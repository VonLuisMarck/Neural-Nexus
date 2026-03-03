#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  Victim Lab — arranque local (venv)
#
#  Levanta el victim-lab (Flask backend + frontend) directamente en el host
#  con un virtualenv Python. El LLM (Ollama) sigue en Docker.
#
#  Prerequisito: Ollama corriendo en Docker:
#    docker compose up -d
#
#  Uso:
#    ./start-victim-lab.sh               # arranca en :8080
#    ./start-victim-lab.sh --port 9090   # puerto personalizado
#    ./start-victim-lab.sh --stop        # mata el proceso
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'
CYN='\033[0;36m'; PRP='\033[0;35m'; BLD='\033[1m'; RST='\033[0m'

ok()   { echo -e "${GRN}  ✓${RST}  $*"; }
info() { echo -e "${CYN}  ●${RST}  $*"; }
warn() { echo -e "${YEL}  ⚠${RST}  $*"; }
fail() { echo -e "${RED}  ✗  $*${RST}"; exit 1; }
step() { echo -e "\n${BLD}${PRP}▶ $*${RST}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv-victim-lab"
BACKEND_DIR="$SCRIPT_DIR/victim-lab/backend"
PID_FILE="$SCRIPT_DIR/.victim-lab.pid"

PORT=8080
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"
JWT_SECRET="${JWT_SECRET_KEY:-change-this-in-production}"
LAB_ID="${LAB_ID:-victim-corp-01}"

STOP=false
for arg in "$@"; do
  case "$arg" in
    --stop)        STOP=true ;;
    --port)        shift; PORT="$1" ;;
    --port=*)      PORT="${arg#*=}" ;;
    --help|-h)
      echo ""; echo "  Uso: ./start-victim-lab.sh [--port N] [--stop]"
      echo "  Env vars: OLLAMA_HOST, OLLAMA_MODEL, JWT_SECRET_KEY, LAB_ID"
      echo ""; exit 0 ;;
  esac
done

# ── Stop ─────────────────────────────────────────────────────────────────────
if $STOP; then
  if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" && ok "victim-lab (PID $PID) detenido" || warn "No se pudo matar PID $PID"
    else
      warn "PID $PID no está activo"
    fi
    rm -f "$PID_FILE"
  else
    warn "No se encontró $PID_FILE"
  fi
  exit 0
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${PRP}"
cat << 'BANNER'
  ╔══════════════════════════════════════════════════════════╗
  ║        NEURAL NEXUS  ·  Victim Lab  (venv local)        ║
  ╚══════════════════════════════════════════════════════════╝
BANNER
echo -e "${RST}"

# ── Python check ─────────────────────────────────────────────────────────────
step "Python"
PYTHON=$(command -v python3 || command -v python || fail "Python 3 no encontrado")
PY_VER=$("$PYTHON" --version 2>&1 | awk '{print $2}')
ok "Python $PY_VER → $PYTHON"

# ── Venv ─────────────────────────────────────────────────────────────────────
step "Virtualenv — $VENV"
if [[ ! -d "$VENV" ]]; then
  info "Creando venv…"
  "$PYTHON" -m venv "$VENV"
  ok "Venv creado"
else
  ok "Venv ya existe"
fi

PY="$VENV/bin/python"
PIP="$VENV/bin/pip"

info "Instalando dependencias…"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r "$BACKEND_DIR/requirements.txt"
ok "Dependencias OK"

# ── Ollama check (no bloqueante) ─────────────────────────────────────────────
step "Comprobando Ollama"
if curl -sf --max-time 3 "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
  ok "Ollama responde en $OLLAMA_HOST"
else
  warn "Ollama no responde en $OLLAMA_HOST"
  warn "Asegúrate de que Docker está corriendo: docker compose up -d"
fi

# ── Matar proceso anterior si existe ─────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    info "Matando proceso anterior (PID $OLD_PID)…"
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
fi
# Fallback: kill any process still holding the port (handles orphans from failed starts)
STALE=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
if [[ -n "$STALE" ]]; then
  info "Puerto $PORT ocupado (PID $STALE) — liberando…"
  kill "$STALE" 2>/dev/null || true
  sleep 1
fi

# ── Arrancar Flask ────────────────────────────────────────────────────────────
step "Arrancando victim-lab en :$PORT"

HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' \
          || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

export OLLAMA_HOST OLLAMA_MODEL JWT_SECRET_KEY="$JWT_SECRET" LAB_ID PORT

nohup "$PY" "$BACKEND_DIR/app.py" \
  >> "$SCRIPT_DIR/victim-lab.log" 2>&1 &
echo $! > "$PID_FILE"
FLASK_PID=$(cat "$PID_FILE")

# Esperar a que Flask arranque
sleep 2
for i in {1..15}; do
  if curl -sf --max-time 2 "http://localhost:$PORT/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if curl -sf --max-time 2 "http://localhost:$PORT/health" >/dev/null 2>&1; then
  ok "victim-lab arrancado (PID $FLASK_PID)"
else
  fail "victim-lab no responde — revisa victim-lab.log"
fi

# ── Resumen ──────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${BLD}${PRP}Victim Lab activo:${RST}"
echo -e "  ${YEL}┌──────────────────────────────────────────────────────────┐${RST}"
printf  "  ${YEL}│${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "CorpAI Lab"    "http://localhost:$PORT"
printf  "  ${YEL}│${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "Marketplace"   "http://localhost:$PORT/marketplace"
printf  "  ${YEL}│${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "Ollama"        "$OLLAMA_HOST"
echo -e "  ${YEL}└──────────────────────────────────────────────────────────┘${RST}"

if [[ -n "$HOST_IP" && "$HOST_IP" != "127.0.0.1" ]]; then
  echo ""
  echo -e "  ${BLD}Acceso remoto (víctima en misma red):${RST}"
  echo -e "  ${CYN}http://${HOST_IP}:${PORT}${RST}"
fi

echo ""
echo -e "  ${BLD}Dos vectores de demo disponibles:${RST}"
echo -e "  ${PRP}① Extensión Chrome${RST}  → Marketplace → 'Instalar gratis' → descarga .zip"
echo -e "  ${PRP}② Agente Python${RST}     → Marketplace → 'Agente Python'   → descarga .py"
echo ""
echo -e "  Logs: ${YEL}tail -f victim-lab.log${RST}"
echo -e "  Stop: ${YEL}./start-victim-lab.sh --stop${RST}"
echo ""
