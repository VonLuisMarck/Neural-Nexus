#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  FASE 2 — Arranque del victim-stack
#
#  Prerequisito: haber ejecutado ./setup.sh al menos una vez.
#  El C2 server lo lanzas tú MANUALMENTE (cd server && ./start-c2-server.sh)
#
#  Este script SOLO gestiona los contenedores Docker del victim-stack:
#    • nn-victim-llm   (Ollama — 172.30.0.11:11434)
#    • nn-victim-lab   (CorpAI Assistant — 172.30.0.10:8080)
#
#  Uso:
#    ./start-demo.sh              # arranca victim-stack
#    ./start-demo.sh --no-model   # omite el pull de llama3
#    ./start-demo.sh --down       # detiene y elimina contenedores
#    ./start-demo.sh --logs       # tail logs de los contenedores
#    ./start-demo.sh --status     # muestra estado actual
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
echo -e "  ${BLD}FASE 2 — Victim Stack${RST}  (C2 se lanza manualmente)"
echo -e "  ${YEL}──────────────────────────────────────────────────────────────────${RST}"
echo -e "  ${PRP}DOCKER${RST}  nn-victim-lab  → ${BLD}http://localhost:8080${RST}  (172.30.0.10)"
echo -e "  ${PRP}DOCKER${RST}  nn-victim-llm  → ${BLD}http://localhost:11434${RST} (172.30.0.11)"
echo -e "  ${CYN}HOST  ${RST}  C2 server      → ${BLD}http://localhost:5001${RST}  (lanzar manualmente)"
echo -e "  ${YEL}──────────────────────────────────────────────────────────────────${RST}\n"

# ─────────────────────────────────────────────────────────────────────────────
# STATUS MODE
# ─────────────────────────────────────────────────────────────────────────────
if $SHOW_STATUS; then
  step "Estado del victim-stack"
  _compose ps 2>/dev/null || warn "Ningún contenedor activo"
  echo ""
  for svc in "nn-victim-lab:localhost:8080/health" "nn-victim-llm:localhost:11434/api/tags"; do
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

# Verificar que setup.sh fue ejecutado (imagen construida)
if ! docker image inspect nn-victim-lab:latest &>/dev/null 2>&1; then
  fail "Imagen nn-victim-lab:latest no encontrada.\n     Ejecuta primero: ${YEL}./setup.sh${RST}"
fi
ok "Imagen nn-victim-lab:latest presente"

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

info "victim-lab (CorpAI)..."
_compose up -d victim-lab
ok "victim-lab arrancado"

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

VICTIM_OK=false; LLM_OK=false

_wait_http "victim-lab  (localhost:8080)"    "http://localhost:8080/health"      90  && VICTIM_OK=true || warn "victim-lab no respondió — revisa: docker compose logs nn-victim-lab"
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
printf  "  ${YEL}│${RST}  %-10s  %-26s  %-22s  ${YEL}│${RST}\n" "SERVICIO"  "IP INTERNA"                          "URL LOCAL"
echo -e "  ${YEL}├──────────────────────────────────────────────────────────────────┤${RST}"
printf  "  ${YEL}│${RST}  %-10s  %-26s  %-22s  ${YEL}│${RST}\n" "victim-lab"  "172.30.0.10:8080"    "http://localhost:8080"
printf  "  ${YEL}│${RST}  %-10s  %-26s  %-22s  ${YEL}│${RST}\n" "victim-llm"  "172.30.0.11:11434"   "http://localhost:11434"
printf  "  ${YEL}│${RST}  ${RED}%-10s${RST}  %-26s  %-22s  ${YEL}│${RST}\n" "C2 server"   "host :${C2_PORT} (manual)"    "http://localhost:${C2_PORT}"
echo -e "  ${YEL}└──────────────────────────────────────────────────────────────────┘${RST}"
echo ""

echo -e "  ${BLD}Flujo del demo:${RST}"
echo -e "  ${CYN}①${RST}  ${BLD}[tú]${RST}      Lanza el C2 si aún no está activo:"
echo -e "           ${YEL}cd server && ./start-c2-server.sh${RST}"
echo -e "  ${CYN}②${RST}  ${BLD}[victim]${RST}  Visita ${BLD}http://localhost:8080${RST} → login como ${YEL}alice / alice123${RST}"
echo -e "  ${CYN}③${RST}  ${BLD}[victim]${RST}  Va al Marketplace → instala cualquier skill → agente arranca"
echo -e "  ${CYN}④${RST}  ${BLD}[tú]${RST}      Panel C2 ${BLD}http://localhost:5001${RST} → agente registrado"
echo -e "  ${CYN}⑤${RST}  ${BLD}[tú]${RST}      Lanza ${BLD}AutoRecon${RST} → descubre victim-lab en 172.30.0.10:8080"
echo -e "  ${CYN}⑥${RST}  ${BLD}[tú]${RST}      Lanza ${BLD}AI Hunter${RST} → inyección de prompt / exfil de credenciales"
echo ""

if [[ -n "$HOST_IP" && "$HOST_IP" != "127.0.0.1" ]]; then
  echo -e "  ${BLD}Acceso remoto (misma red local):${RST}"
  echo -e "  CorpAI Lab → ${CYN}http://${HOST_IP}:8080${RST}"
  echo -e "  C2 Panel   → ${CYN}http://${HOST_IP}:${C2_PORT}${RST}"
  echo ""
fi

echo -e "  ${BLD}Comandos útiles:${RST}"
echo -e "  ${YEL}./start-demo.sh --logs${RST}     # logs en tiempo real"
echo -e "  ${YEL}./start-demo.sh --status${RST}   # estado del stack"
echo -e "  ${YEL}./start-demo.sh --down${RST}     # detener todo"
echo -e "  ${YEL}docker compose logs -f nn-victim-lab${RST}"
echo ""
