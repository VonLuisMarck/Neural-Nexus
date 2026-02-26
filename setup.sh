#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  FASE 1 — Setup del entorno
#
#  Ejecuta esto UNA SOLA VEZ antes del demo para preparar todo:
#    • Verifica prerequisitos (Python 3, Docker, Docker Compose)
#    • Crea venv Python para el servidor C2
#    • Instala dependencias Python del C2
#    • Construye las imágenes Docker del victim-stack
#    • (Opcional) Pre-descarga el modelo llama3 en Ollama
#
#  Una vez completado, usa start-demo.sh para arrancar el victim-stack.
#  El C2 lo lanzas tú manualmente: cd server && ./start-c2-server.sh
#
#  Uso:
#    chmod +x setup.sh
#    ./setup.sh                  # setup completo (incluye pull del modelo)
#    ./setup.sh --no-model       # salta el pull de llama3
#    ./setup.sh --no-docker      # solo venv + deps Python, sin Docker
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
VENV="$SCRIPT_DIR/.venv"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3}"

PULL_MODEL=true
SKIP_DOCKER=false

for arg in "$@"; do
  case "$arg" in
    --no-model)  PULL_MODEL=false ;;
    --no-docker) SKIP_DOCKER=true ;;
    --help|-h)
      echo ""; echo "  Uso: ./setup.sh [--no-model] [--no-docker]"
      echo "  --no-model   Omite la descarga del modelo llama3 (~4 GB)"
      echo "  --no-docker  Solo instala dependencias Python, sin Docker"
      echo ""; exit 0 ;;
    *) warn "Argumento desconocido: $arg (ignorado)" ;;
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
echo -e "  ${BLD}FASE 1 — Setup del entorno  (ejecución única)${RST}"
echo -e "  ${YEL}──────────────────────────────────────────────${RST}\n"

cd "$SCRIPT_DIR"

# ── Helper: detect compose command ───────────────────────────────────────────
_compose() {
  if docker compose version &>/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose &>/dev/null; then
    docker-compose "$@"
  else
    fail "docker compose / docker-compose no encontrado"
  fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. PREREQUISITOS
# ─────────────────────────────────────────────────────────────────────────────
step "Comprobando prerequisitos"

# Python 3
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version)
  PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
  (( PY_MINOR < 8 )) && fail "Se requiere Python 3.8+  (encontrado: $PY_VER)"
  ok "$PY_VER"
else
  fail "python3 no encontrado  →  apt install python3"
fi

# pip / venv
if ! python3 -m venv --help &>/dev/null; then
  PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
  fail "python3-venv no está instalado  →  apt install python3.${PY_MINOR}-venv"
fi
ok "python3-venv disponible"

if ! $SKIP_DOCKER; then
  # Docker
  if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "?")
    ok "Docker $DOCKER_VER"
  else
    fail "Docker no encontrado  →  https://docs.docker.com/engine/install/"
  fi

  # Docker Compose
  if docker compose version &>/dev/null 2>&1; then
    ok "docker compose v2"
  elif command -v docker-compose &>/dev/null; then
    warn "docker-compose legacy detectado — se recomienda actualizar a compose v2"
  else
    fail "docker compose no encontrado  →  apt install docker-compose-plugin"
  fi

  # RAM
  if command -v free &>/dev/null; then
    TOTAL_MB=$(free -m | awk '/Mem:/{print $2}')
    (( TOTAL_MB < 4096 )) && warn "Solo ${TOTAL_MB} MB RAM detectados (Ollama requiere 8 GB para llama3)"
    ok "RAM disponible: ${TOTAL_MB} MB"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# 2. ENTORNO PYTHON PARA EL C2
# ─────────────────────────────────────────────────────────────────────────────
step "Configurando entorno Python para el C2 server"

if [[ ! -f "$VENV/bin/activate" ]]; then
  info "Creando venv en $VENV ..."
  python3 -m venv "$VENV"
  ok "venv creado"
else
  ok "venv ya existe en $VENV"
fi

info "Actualizando pip..."
"$VENV/bin/pip" install -q --upgrade pip

if [[ -f "$C2_DIR/requirements.txt" ]]; then
  info "Instalando dependencias del C2 (server/requirements.txt)..."
  "$VENV/bin/pip" install -q -r "$C2_DIR/requirements.txt"
  ok "Dependencias Python instaladas"
else
  warn "server/requirements.txt no encontrado — saltando"
fi

# Crear script de lanzamiento del C2 si no existe
C2_LAUNCHER="$C2_DIR/start-c2-server.sh"
if [[ ! -f "$C2_LAUNCHER" ]]; then
  info "Generando $C2_LAUNCHER ..."
  cat > "$C2_LAUNCHER" << 'LAUNCHER'
#!/usr/bin/env bash
# C2 Server launcher — generado por setup.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV="$ROOT_DIR/.venv"
C2_PORT="${C2_PORT:-5001}"

[[ ! -f "$VENV/bin/activate" ]] && echo "ERROR: venv no encontrado. Ejecuta primero: ./setup.sh" && exit 1

echo -e "\n  \033[0;35m▶ Iniciando C2 server en puerto ${C2_PORT}\033[0m"
echo -e "  \033[0;36m●\033[0m Panel: http://localhost:${C2_PORT}\n"

cd "$SCRIPT_DIR"
PORT="$C2_PORT" "$VENV/bin/python" app.py
LAUNCHER
  chmod +x "$C2_LAUNCHER"
  ok "Launcher creado: server/start-c2-server.sh"
else
  ok "server/start-c2-server.sh ya existe"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. IMÁGENES DOCKER
# ─────────────────────────────────────────────────────────────────────────────
if ! $SKIP_DOCKER; then
  step "Construyendo imágenes Docker del victim-stack"
  info "Construyendo nn-victim-lab (puede tardar 2–5 min la primera vez)..."
  _compose build victim-lab
  ok "Imagen nn-victim-lab lista"

  info "Descargando imagen ollama/ollama:latest..."
  docker pull ollama/ollama:latest &>/dev/null && ok "Imagen Ollama descargada" || warn "Pull de Ollama falló — se reintentará al arrancar"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. PRE-PULL DEL MODELO (OPCIONAL)
# ─────────────────────────────────────────────────────────────────────────────
if ! $SKIP_DOCKER && $PULL_MODEL; then
  step "Pre-descargando modelo LLM: $OLLAMA_MODEL (~4 GB, requiere Ollama activo)"

  # Levanta Ollama temporalmente para el pull
  _compose up -d victim-llm
  info "Esperando a que Ollama arranque..."
  for i in $(seq 1 30); do
    curl -sf --max-time 2 "http://localhost:11434/api/tags" >/dev/null 2>&1 && break
    sleep 2
  done

  if curl -sf "http://localhost:11434/api/tags" >/dev/null 2>&1; then
    if docker exec nn-victim-llm ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
      ok "Modelo $OLLAMA_MODEL ya está en caché"
    else
      info "Descargando $OLLAMA_MODEL (solo esta vez)..."
      docker exec nn-victim-llm ollama pull "$OLLAMA_MODEL" && ok "Modelo $OLLAMA_MODEL listo" || warn "Pull falló — reintenta: docker exec nn-victim-llm ollama pull $OLLAMA_MODEL"
    fi
  else
    warn "Ollama no respondió — descarga el modelo manualmente después de arrancar"
  fi

  # Detén Ollama para que start-demo.sh lo arranque limpio
  _compose stop victim-llm &>/dev/null || true
fi

# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
echo -e "\n${BLD}${GRN}  ══════════════════════════════════════════════════${RST}"
echo -e "${BLD}${GRN}  ✓  Setup completado correctamente${RST}"
echo -e "${BLD}${GRN}  ══════════════════════════════════════════════════${RST}\n"

echo -e "  ${BLD}Siguientes pasos para el demo:${RST}\n"
echo -e "  ${PRP}① Arranca el C2 manualmente (en una terminal separada):${RST}"
echo -e "     ${YEL}cd server && ./start-c2-server.sh${RST}"
echo -e "     ${CYN}→ Panel C2: http://localhost:5001${RST}\n"
echo -e "  ${PRP}② Arranca el victim-stack:${RST}"
echo -e "     ${YEL}./start-demo.sh${RST}"
echo -e "     ${CYN}→ CorpAI Victim Lab: http://localhost:8080${RST}\n"
echo -e "  ${PRP}③ Flujo del ataque:${RST}"
echo -e "     ${CYN}a)${RST} Victim visita http://localhost:8080 → instala Neural Nexus skill"
echo -e "     ${CYN}b)${RST} Agente conecta al C2 → aparece en el panel"
echo -e "     ${CYN}c)${RST} Ejecuta AutoRecon → descubre victim-lab en 172.30.0.10:8080"
echo -e "     ${CYN}d)${RST} Lanza AI Hunter → inyección de prompt / exfil de credenciales\n"
