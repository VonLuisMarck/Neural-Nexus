#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  FASE 2 — Arranque del victim-stack
#
#  Arquitectura:
#    Docker  → nn-victim-llm  (Ollama LLM — localhost:11434)
#    Local   → victim-lab     (Flask + frontend — localhost:8080)  ← venv
#    Local   → C2 server      (localhost:5001)                     ← manual
#
#  Este script gestiona SOLO el LLM Docker (Ollama).
#  El victim-lab se lanza por separado con:  ./start-victim-lab.sh
#  El C2 se lanza manualmente con:           cd server && ./start-c2-server.sh
#
#  Uso:
#    ./start-demo.sh              # arranca Ollama en Docker
#    ./start-demo.sh --no-model   # omite el pull de llama3
#    ./start-demo.sh --down       # detiene contenedores Docker
#    ./start-demo.sh --logs       # tail logs de Ollama
#    ./start-demo.sh --status     # muestra estado de todos los servicios
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'
CYN='\033[0;36m'; PRP='\033[0;35m'; BLD='\033[1m'; RST='\033[0m'

ok()   { echo -e "${GRN}  ✓${RST}  $*"; }
info() { echo -e "${CYN}  ●${RST}  $*"; }
warn() { echo -e "${YEL}  ⚠${RST}  $*"; }
fail() { echo -e "${RED}  ✗  $*${RST}"; exit 1; }
step() { echo -e "\n${BLD}${PRP}▶ $*${RST}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"

PULL_MODEL=true
TEAR_DOWN=false
SHOW_LOGS=false
SHOW_STATUS=false

for arg in "$@"; do
  case "$arg" in
    --no-model) PULL_MODEL=false ;;
    --down)     TEAR_DOWN=true ;;
    --logs)     SHOW_LOGS=true ;;
    --status)   SHOW_STATUS=true ;;
    --help|-h)
      echo ""; echo "  Uso: ./start-demo.sh [opción]"
      echo "  (sin flags)   Arranca victim-stack"
      echo "  --no-model    Omite el pull del modelo llama3"
      echo "  --down        Detiene y elimina contenedores"
      echo "  --logs        Muestra logs en tiempo real"
      echo "  --status      Muestra estado actual del stack"
      echo ""; exit 0 ;;
    *) warn "Argumento desconocido: $arg (ignorado)" ;;
  esac
done

cd "$SCRIPT_DIR"

# ── Helper: compose command ───────────────────────────────────────────────────
_compose() {
  if docker compose version &>/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    fail "docker compose / docker-compose no encontrado — ejecuta setup.sh primero"
  fi
}

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo -e "${PRP}"
cat << 'BANNER'
  ███╗   ██╗███████╗██╗   ██╗██████╗  █████╗ ██╗         ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝██║   ██║██╔══██╗██╔══██╗██║         ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗  ██║   ██║██████╔╝███████║██║         ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝  ██║   ██║██╔══██╗██╔══██║██║         ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗╚██████╔╝██║  ██║██║  ██║███████╗    ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝    ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
BANNER
echo -e "${RST}"
echo -e "  ${BLD}FASE 2 — LLM Docker + Victim Lab local${RST}"
echo -e "  ${YEL}──────────────────────────────────────────────────────────────────${RST}"
echo -e "  ${PRP}DOCKER${RST}  nn-victim-llm  → ${BLD}http://localhost:11434${RST} (Ollama)"
echo -e "  ${GRN}LOCAL ${RST}  victim-lab     → ${BLD}http://localhost:8080${RST}  (./start-victim-lab.sh)"
echo -e "  ${CYN}LOCAL ${RST}  C2 server      → ${BLD}http://localhost:5001${RST}  (cd server && ./start-c2-server.sh)"
echo -e "  ${YEL}──────────────────────────────────────────────────────────────────${RST}\n"

# ─────────────────────────────────────────────────────────────────────────────
# STATUS MODE
# ─────────────────────────────────────────────────────────────────────────────
if $SHOW_STATUS; then
  step "Estado del victim-stack"
  _compose ps 2>/dev/null || warn "Ningún contenedor activo"
  echo ""
  for svc in "nn-victim-llm:localhost:11434/api/tags" "victim-lab(local):localhost:8080/health"; do
    NAME="${svc%%:*}"; URL="${svc#*:}"
    if curl -sf --max-time 2 "http://$URL" >/dev/null 2>&1; then
      ok "$NAME  → UP  (http://$URL)"
    else
      echo -e "${RED}  ✗${RST}  $NAME  → DOWN  (http://$URL)"
    fi
  done
  # C2
  C2_PORT="${C2_PORT:-5001}"
  if curl -sf --max-time 2 "http://localhost:${C2_PORT}" >/dev/null 2>&1; then
    ok "C2 server → UP  (http://localhost:${C2_PORT})"
  else
    warn "C2 server → no responde en :${C2_PORT}  (¿lo has lanzado manualmente?)"
  fi
  echo ""
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# TEAR-DOWN MODE
# ─────────────────────────────────────────────────────────────────────────────
if $TEAR_DOWN; then
  step "Deteniendo victim-stack"
  _compose down --remove-orphans 2>/dev/null && ok "Contenedores eliminados" || warn "Nada que eliminar"
  docker network rm nn-demo-net 2>/dev/null && ok "Red nn-demo-net eliminada" || true
  echo ""
  warn "El C2 server (si está activo) lo debes detener manualmente con Ctrl-C en su terminal."
  echo ""
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# LOGS MODE
# ─────────────────────────────────────────────────────────────────────────────
if $SHOW_LOGS; then
  echo -e "  ${BLD}Logs en tiempo real (Ctrl-C para salir)${RST}\n"
  trap "exit 0" INT
  _compose logs -f --no-log-prefix 2>/dev/null
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# PREFLIGHT
# ─────────────────────────────────────────────────────────────────────────────
step "Comprobaciones previas"

ok "Verificaciones OK (victim-lab corre local — no necesita imagen Docker)"

if command -v docker &>/dev/null; then
  ok "Docker disponible"
else
  fail "Docker no encontrado"
fi

# C2 — aviso (no bloquea)
C2_PORT="${C2_PORT:-5001}"
if curl -sf --max-time 1 "http://localhost:${C2_PORT}" >/dev/null 2>&1; then
  ok "C2 detectado en :${C2_PORT}  ✓"
else
  warn "C2 no responde en :${C2_PORT} — recuerda lanzarlo:"
  echo -e "       ${YEL}cd server && ./start-c2-server.sh${RST}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# RED DOCKER
# ─────────────────────────────────────────────────────────────────────────────
step "Red Docker — nn-demo-net (172.30.0.0/24)"

if docker network inspect nn-demo-net &>/dev/null 2>&1; then
  ok "Red nn-demo-net ya existe"
else
  docker network create \
    --driver bridge \
    --subnet 172.30.0.0/24 \
    --gateway 172.30.0.1 \
    nn-demo-net &>/dev/null
  ok "Red nn-demo-net creada"
fi

# ─────────────────────────────────────────────────────────────────────────────
# ARRANCAR CONTENEDORES
# ─────────────────────────────────────────────────────────────────────────────
step "Arrancando contenedores"

info "victim-llm (Ollama)..."
_compose up -d victim-llm
ok "victim-llm arrancado"

# victim-lab corre local — recordatorio
warn "victim-lab corre LOCAL (no en Docker) → lanza en otra terminal:"
echo -e "       ${YEL}./start-victim-lab.sh${RST}"

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────
step "Esperando a que los servicios estén listos"

_wait_http() {
  local label="$1" url="$2" max="${3:-90}" elapsed=0
  printf "  %-36s " "$label"
  while (( elapsed < max )); do
    if curl -sf --max-time 2 "$url" >/dev/null 2>&1; then
      echo -e "${GRN}UP${RST}"
      return 0
    fi
    printf "."
    sleep 2
    (( elapsed += 2 ))
  done
  echo -e " ${RED}TIMEOUT${RST}"
  return 1
}

LLM_OK=false

_wait_http "victim-llm  (localhost:11434)"   "http://localhost:11434/api/tags"   120 && LLM_OK=true   || warn "Ollama no respondió — revisa: docker compose logs nn-victim-llm"

# ─────────────────────────────────────────────────────────────────────────────
# PULL MODELO (si Ollama está arriba)
# ─────────────────────────────────────────────────────────────────────────────
if $PULL_MODEL && $LLM_OK; then
  step "Modelo LLM — $OLLAMA_MODEL"
  if docker exec nn-victim-llm ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    ok "Modelo $OLLAMA_MODEL ya en caché"
  else
    info "Descargando $OLLAMA_MODEL (primera vez, ~4 GB)..."
    docker exec nn-victim-llm ollama pull "$OLLAMA_MODEL" \
      && ok "Modelo listo" \
      || warn "Pull falló — reintenta: docker exec nn-victim-llm ollama pull $OLLAMA_MODEL"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
step "Victim-stack listo"
echo ""

# Detectar IP del host para acceso en red
HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' \
          || hostname -I 2>/dev/null | awk '{print $1}' || echo "")

echo -e "  ${BLD}${PRP}Servicios activos:${RST}"
echo -e "  ${YEL}┌──────────────────────────────────────────────────────────────────┐${RST}"
printf  "  ${YEL}│${RST}  %-8s  %-12s  %-40s  ${YEL}│${RST}\n" "SERVICIO"  "MODO"  "URL"
echo -e "  ${YEL}├──────────────────────────────────────────────────────────────────┤${RST}"
printf  "  ${YEL}│${RST}  ${GRN}%-8s${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "victim-llm"  "Docker"  "http://localhost:11434"
printf  "  ${YEL}│${RST}  ${GRN}%-8s${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "victim-lab"  "venv local"  "http://localhost:8080  (start-victim-lab.sh)"
printf  "  ${YEL}│${RST}  ${RED}%-8s${RST}  %-12s  %-40s  ${YEL}│${RST}\n" "C2 server"  "local"  "http://localhost:${C2_PORT}  (manual)"
echo -e "  ${YEL}└──────────────────────────────────────────────────────────────────┘${RST}"
echo ""

echo -e "  ${BLD}Flujo del demo:${RST}"
echo -e "  ${CYN}①${RST}  ${BLD}[tú]${RST}      Lanza el C2:        ${YEL}cd server && ./start-c2-server.sh${RST}"
echo -e "  ${CYN}②${RST}  ${BLD}[tú]${RST}      Lanza victim-lab:   ${YEL}./start-victim-lab.sh${RST}"
echo -e "  ${CYN}③${RST}  ${BLD}[victim]${RST}  Visita ${BLD}http://localhost:8080${RST} → login ${YEL}alice / alice123${RST}"
echo -e "  ${CYN}④${RST}  ${BLD}[victim]${RST}  Marketplace → elige vector:"
echo -e "           ${PRP}A) Extensión Chrome${RST} → descarga .zip → instala → beacon automático"
echo -e "           ${PRP}B) Agente Python${RST}    → descarga .py  → ejecuta → beacon al C2"
echo -e "  ${CYN}⑤${RST}  ${BLD}[tú]${RST}      Panel C2 ${BLD}http://localhost:5001${RST} → agente registrado"
echo -e "  ${CYN}⑥${RST}  ${BLD}[tú]${RST}      Lanza ${BLD}AI Hunter${RST} → inyección de prompt / exfil de credenciales"
echo ""

if [[ -n "$HOST_IP" && "$HOST_IP" != "127.0.0.1" ]]; then
  echo -e "  ${BLD}Acceso remoto (misma red local):${RST}"
  echo -e "  CorpAI Lab → ${CYN}http://${HOST_IP}:8080${RST}  (victim-lab local)"
  echo -e "  C2 Panel   → ${CYN}http://${HOST_IP}:${C2_PORT}${RST}"
  echo ""
fi

echo -e "  ${BLD}Comandos útiles:${RST}"
echo -e "  ${YEL}./start-demo.sh --logs${RST}     # logs en tiempo real"
echo -e "  ${YEL}./start-demo.sh --status${RST}   # estado del stack"
echo -e "  ${YEL}./start-demo.sh --down${RST}          # detener Docker (Ollama)"
echo -e "  ${YEL}./start-victim-lab.sh --stop${RST}    # detener victim-lab local"
echo -e "  ${YEL}docker compose logs -f nn-victim-llm${RST}"
echo ""
