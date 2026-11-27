#!/usr/bin/env bash
# Pulso Energético: despliegue idempotente en UNA EC2 Ubuntu (AWS Academy Learner Lab).
# Uso (en la EC2, como usuario ubuntu):
#   ./deploy-ec2.sh            # todo: swap, Docker, repo, imágenes, .env, up y verify
#   ./deploy-ec2.sh refresh-ip # tras End Lab o un reinicio: actualiza ALLOWED_HOSTS y recrea web
#   ./deploy-ec2.sh verify     # login de observador + curl a /api/localities y al state de cuenca-sede
#   ./deploy-ec2.sh status     # contenedores, memoria y últimas líneas del log
# Uso en el portátil o en la EC2 para reiniciar el ensayo (menos de 10 s):
#   BASE_URL=http://localhost:8080 ENV_FILE=.env ./scripts/deploy-ec2.sh reset-demo
# Variables opcionales: APP_DIR, REPO_URL, IMAGES_TAR, WEB_BIND, PUBLIC_PORT, SWAP_GB, BUDGET_KWH, BASE_URL, ENV_FILE.
# No llama a ninguna API de AWS: solo usa el servicio de metadatos de la propia instancia.
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/PulsoEnergetico}"
REPO_URL="${REPO_URL:-https://github.com/datmetalpls/PulsoEnergetico.git}"
IMAGES_TAR="${IMAGES_TAR:-$HOME/pulso-images.tar.gz}"
WEB_BIND="${WEB_BIND:-0.0.0.0}"
PUBLIC_PORT="${PUBLIC_PORT:-8080}"
SWAP_GB="${SWAP_GB:-2}"
BUDGET_KWH="${BUDGET_KWH:-0.15}"
SITE_SLUG="cuenca-sede"
WEB_IMAGE="pulso-web:demo"

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

compose() {
  (cd "$APP_DIR" && sudo docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml "$@")
}

env_get() { # env_get ARCHIVO CLAVE → valor (o vacío)
  [ -f "$1" ] && grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2- || true
}

secret() { # secret CLAVE: como compose, .env tiene prioridad sobre .env.example
  local f v
  for f in ${ENV_FILE:+"$ENV_FILE"} ./.env "$APP_DIR/.env" ./.env.example "$APP_DIR/.env.example"; do
    v="$(env_get "$f" "$1")"; [ -n "$v" ] && { printf '%s' "$v"; return; }
  done
  die "No encuentro $1 en .env ni en .env.example (definir ENV_FILE)"
}

setup_swap() {
  if swapon --show=NAME --noheadings | grep -q .; then
    log "Swap ya activa: $(swapon --show=NAME,SIZE --noheadings | tr '\n' ' ')"; return
  fi
  log "Creando swap de ${SWAP_GB} GB en /swapfile"
  [ -f /swapfile ] || sudo fallocate -l "${SWAP_GB}G" /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile >/dev/null
  sudo swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
}

install_docker() {
  if command -v docker >/dev/null && sudo docker compose version >/dev/null 2>&1; then
    log "Docker ya instalado: $(sudo docker --version); $(sudo docker compose version)"
  else
    log "Instalando Docker Engine y el plugin compose (repositorio oficial de Docker)"
    sudo apt-get update -y
    sudo apt-get install -y ca-certificates curl git
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    # shellcheck disable=SC1091
    codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")"
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${codename} stable" \
      | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  fi
  sudo systemctl enable --now docker >/dev/null
  sudo usermod -aG docker "$USER" || true
  # !override y !reset en compose.ec2.yml, y env_file con required:false, exigen Compose >= 2.24.
  local v; v="$(sudo docker compose version --short | sed 's/^v//')"
  [ "$(printf '%s\n2.24.0\n' "$v" | sort -V | head -n1)" = "2.24.0" ] || die "Compose $v < 2.24: actualizar docker-compose-plugin"
}

sync_repo() {
  command -v git >/dev/null || { sudo apt-get update -y && sudo apt-get install -y git; }
  if [ -d "$APP_DIR/.git" ]; then
    log "Actualizando repo en $APP_DIR"
    git -C "$APP_DIR" pull --ff-only || echo "AVISO: git pull falló; se usa la copia actual" >&2
  elif [ -f "$APP_DIR/docker-compose.yml" ]; then
    log "$APP_DIR sin .git pero con docker-compose.yml (copiado por scp); se usa tal cual"
  elif [ -d "$APP_DIR" ]; then
    log "$APP_DIR existe (p. ej. solo .env): se clona aparte y se copia sin pisar archivos"
    local tmp; tmp="$(mktemp -d)"
    git clone --depth 1 "$REPO_URL" "$tmp/r" && cp -rn "$tmp/r/." "$APP_DIR/" || echo "AVISO: clone falló" >&2
    rm -rf "$tmp"
  else
    log "Clonando $REPO_URL"
    git clone --depth 1 "$REPO_URL" "$APP_DIR"
  fi
  [ -f "$APP_DIR/docker-compose.yml" ] && [ -f "$APP_DIR/.env.example" ] || die \
    "Faltan docker-compose.yml o .env.example en $APP_DIR (¿aún sin push?). Copiarlos con scp; ver scripts/deploy-ec2.md §3"
}

write_override() {
  local needs_port_override=1
  if [ "$PUBLIC_PORT" = "8080" ] && grep -q 'WEB_BIND' "$APP_DIR/docker-compose.yml" 2>/dev/null; then
    needs_port_override=0
  fi
  if [ "$needs_port_override" -eq 0 ]; then
    log "Escribiendo compose.ec2.yml (imagen precompilada; bind ${WEB_BIND}:8080 y restart heredados de docker-compose.yml)"
    cat > "$APP_DIR/compose.ec2.yml" <<EOF
# Solo para la EC2. No se sube al repo. Generado por scripts/deploy-ec2.sh.
# El bind ${WEB_BIND}:8080 (vía WEB_BIND en .env) y restart: unless-stopped vienen de docker-compose.yml.
services:
  web:
    build: !reset null
    image: ${WEB_IMAGE}
    pull_policy: never
EOF
  else
    log "Escribiendo compose.ec2.yml (bind ${WEB_BIND}:${PUBLIC_PORT} con !override, imagen precompilada, restart)"
    cat > "$APP_DIR/compose.ec2.yml" <<EOF
# Solo para la EC2. No se sube al repo. Generado por scripts/deploy-ec2.sh.
services:
  db:
    restart: unless-stopped
  web:
    build: !reset null
    image: ${WEB_IMAGE}
    pull_policy: never
    restart: unless-stopped
    ports: !override
      - "${WEB_BIND}:${PUBLIC_PORT}:8000"
EOF
  fi
}

load_images() {
  if [ -f "$IMAGES_TAR" ]; then
    local sum marker="$HOME/.pulso-images.sha256"
    sum="$(sha256sum "$IMAGES_TAR" | cut -d' ' -f1)"
    if [ "$(cat "$marker" 2>/dev/null)" = "$sum" ] && sudo docker image inspect "$WEB_IMAGE" >/dev/null 2>&1; then
      log "Imágenes ya cargadas ($IMAGES_TAR sin cambios)"
    else
      log "Cargando imágenes desde $IMAGES_TAR"
      gunzip -c "$IMAGES_TAR" | sudo docker load
      echo "$sum" > "$marker"
    fi
  fi
  sudo docker image inspect "$WEB_IMAGE" >/dev/null 2>&1 || die \
    "No existe la imagen $WEB_IMAGE. Construirla en el portátil y copiar $IMAGES_TAR (scripts/deploy-ec2.md §2)"
  local arch; arch="$(sudo docker image inspect -f '{{.Architecture}}' "$WEB_IMAGE")"
  [ "$arch" = "amd64" ] || die "La imagen es $arch; t3 necesita amd64 (build con --platform linux/amd64)"
}

public_host() { # IP pública y DNS desde IMDSv2; vacío si no responde
  local t
  t="$(curl -fsS -m 2 -X PUT http://169.254.169.254/latest/api/token \
        -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' 2>/dev/null)" || return 0
  for k in public-ipv4 public-hostname; do
    curl -fsS -m 2 -H "X-aws-ec2-metadata-token: $t" "http://169.254.169.254/latest/meta-data/$k" 2>/dev/null && echo || true
  done
  return 0
}

set_env_var() { # set_env_var ARCHIVO CLAVE VALOR
  if grep -q "^$2=" "$1"; then
    sed -i "s|^$2=.*|$2=$3|" "$1"
  else
    printf '\n%s=%s\n' "$2" "$3" >> "$1"
  fi
}

configure_env() {
  local envf="$APP_DIR/.env"
  [ -f "$envf" ] || die "Falta $envf. Copiarlo desde el portátil con scp (nunca subirlo al repo); ver deploy-ec2.md §1"
  chmod 600 "$envf"
  grep -q 'replace-before-deployment' "$envf" && die "DJANGO_SECRET_KEY de .env sigue con el valor de ejemplo"
  local hosts
  hosts="$(public_host | grep -v '^$' | paste -sd, -)"
  [ -n "$hosts" ] || echo "AVISO: IMDS no respondió; ALLOWED_HOSTS queda solo local" >&2
  hosts="${hosts:+$hosts,}localhost,127.0.0.1,web"
  log "ALLOWED_HOSTS=$hosts · WEB_BIND=$WEB_BIND"
  set_env_var "$envf" ALLOWED_HOSTS "$hosts"
  set_env_var "$envf" WEB_BIND "$WEB_BIND"
}

up() {
  log "docker compose up -d (sin --build: la imagen viene compilada del portátil)"
  compose up -d --remove-orphans
  log "Esperando a que web responda en 127.0.0.1:${PUBLIC_PORT}"
  for _ in $(seq 1 60); do
    if curl -fsS -m 2 "http://127.0.0.1:${PUBLIC_PORT}/api/auth/me" >/dev/null 2>&1; then
      local logs; logs="$(compose logs web 2>&1)"
      grep -m1 'Demo ready' <<<"$logs" || echo "AVISO: no se ve 'Demo ready' en el log" >&2
      return
    fi
    sleep 2
  done
  compose logs --tail 50 web
  die "web no respondió en 120 s"
}

# --- Cliente HTTP mínimo con sesión Django (CSRF + cookie) ---
JAR=""
http_login() { # http_login BASE USUARIO CONTRASEÑA
  JAR="$(mktemp)"; trap 'rm -f "$JAR"' EXIT
  curl -fsS -c "$JAR" -b "$JAR" "$1/api/auth/csrf" >/dev/null
  local body
  body="$(python3 -c 'import json,sys; print(json.dumps({"username":sys.argv[1],"password":sys.argv[2]}))' "$2" "$3")"
  local out
  out="$(curl -fsS -c "$JAR" -b "$JAR" -H "X-CSRFToken: $(csrf)" -H 'Content-Type: application/json' \
    -d "$body" "$1/api/auth/login")" || die "login de $2 falló (¿contraseña distinta a la sembrada?)"
  grep -q '"authenticated": *true' <<<"$out" || die "login de $2 falló"
}
csrf() { awk '$6=="csrftoken"{v=$7} END{print v}' "$JAR"; }
http() { # http MÉTODO URL [JSON]
  curl -fsS -c "$JAR" -b "$JAR" -X "$1" -H "X-CSRFToken: $(csrf)" -H 'Content-Type: application/json' \
    ${3:+-d "$3"} "$2"
}

verify() {
  local base="${BASE_URL:-http://127.0.0.1:${PUBLIC_PORT}}"
  local pw; pw="$(secret DEMO_OBSERVER_PASSWORD)"
  log "Verificando $base como observador"
  http_login "$base" observador "$pw"
  local out
  out="$(http GET "$base/api/localities")"
  grep -q '"cuenca"' <<<"$out" || die "/api/localities no incluye cuenca"
  echo "OK  /api/localities"
  out="$(http GET "$base/api/sites/$SITE_SLUG/state")"
  grep -q '"salon-principal"' <<<"$out" || die "state de $SITE_SLUG incompleto"
  echo "OK  /api/sites/$SITE_SLUG/state"
  local ip; ip="$(public_host | head -n1)"
  [ -n "$ip" ] && echo "Abrir en el navegador: http://${ip}:${PUBLIC_PORT}  (requiere regla ${PUBLIC_PORT}/tcp en el SG)"
  true
}

reset_demo() { # nuevo ensayo de Cuenca con presupuesto corto para el guion de 90 s
  local base="${BASE_URL:-http://localhost:8080}"
  local pw; pw="$(secret DEMO_CUENCA_PASSWORD)"
  log "Reiniciando ensayo de $SITE_SLUG en $base (presupuesto ${BUDGET_KWH} kWh)"
  http_login "$base" operador_cuenca "$pw"
  http POST "$base/api/sites/$SITE_SLUG/sessions" '{}' >/dev/null
  http PATCH "$base/api/sites/$SITE_SLUG" "{\"budget_kwh_day\": ${BUDGET_KWH}}" >/dev/null
  echo "OK  ensayo nuevo, en pausa, umbral $(python3 -c "print(round(${BUDGET_KWH}*1000))") Wh. En la UI: ▶ Reproducir"
}

status() {
  compose ps
  free -h
  compose logs --tail 20 web
}

cmd="${1:-all}"
case "$cmd" in
  all)        setup_swap; install_docker; sync_repo; write_override; load_images; configure_env; up; verify ;;
  refresh-ip) write_override; configure_env; up; verify ;;
  verify)     verify ;;
  reset-demo) reset_demo ;;
  status)     status ;;
  *) die "Subcomando desconocido: $cmd (all|refresh-ip|verify|reset-demo|status)" ;;
esac
