#!/usr/bin/env bash
# ============================================================================
#  Cavrix Cloud - all-in-one installer / manager
#
#  One-click deploy on ANY Ubuntu/Debian VPS (or Docker container):
#    - Auto-detects the environment and installs with Docker Compose when a
#      Docker daemon is reachable, otherwise runs natively (SQLite + Python
#      venv + static frontend + Caddy TLS). No Postgres/Redis required in
#      native mode (the app degrades gracefully without Redis).
#    - Wires a custom domain through Cloudflare (auto DNS records + DNS-01 TLS).
#    - Prints your admin credentials when done.
#
#  One-liner (run as root):
#      bash <(curl -fsSL https://raw.githubusercontent.com/FaaizJohar/CavrixDash/main/install.sh) \
#          --domain cavrix.example.com --email you@mail.com --cf-token <CF_API_TOKEN>
#
#  Subcommands: install | start | stop | restart | logs | status | backup | uninstall
#  Modes:       --mode auto (default) | docker | native
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------- colors ----
C_RESET=$'\033[0m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_RED=$'\033[31m'; C_BOLD=$'\033[1m'
info()  { printf '%s[*]%s %s\n'      "$C_GREEN" "$C_RESET" "$*"; }
warn()  { printf '%s[!]%s %s\n'      "$C_YELLOW" "$C_RESET" "$*"; }
fail()  { printf '%s[x]%s %s\n'      "$C_RED" "$C_RESET" "$*" >&2; exit 1; }

# ------------------------------------------------------------- defaults ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null || echo "$PWD")"
REPO_DIR="${SCRIPT_DIR}"
INSTALL_DIR="${INSTALL_DIR:-/opt/cavrix}"
GIT_REPO="https://github.com/FaaizJohar/CavrixDash.git"
COMPOSE_FILE="docker-compose.prod.yml"
NATIVE_MARKER=".native"
NODE_VERSION="20.18.0"
RUN_DIR=""
LOG_DIR=""

CAVRIX_DOMAIN=""
ACME_EMAIL=""
CF_TOKEN=""
CF_ZONE_ID=""
ADMIN_EMAIL="admin@cavrix.cloud"
ADMIN_PASSWORD=""
MODE="auto"                      # auto | docker | native
ASSUME_YES=0
NON_INTERACTIVE=0
NO_FIREWALL=0
REGENERATE_SECRETS=0
ADGEM_POSTBACK_KEY=""
CMD="install"

# ----------------------------------------------------------------- utils ----
have() { command -v "$1" >/dev/null 2>&1; }

die() { fail "$*"; }

prompt() { # prompt <var> <question> <default>
  local var="$1" question="$2" default="${3:-}" answer
  if [[ -n "${default}" ]]; then
    read -r -p "${question} [${default}]: " answer
    eval "$var=\"${answer:-$default}\""
  else
    read -r -p "${question}: " answer
    eval "$var=\"$answer\""
  fi
}

confirm() { # confirm <question> -> 0 yes
  [[ "${ASSUME_YES}" -eq 1 ]] && return 0
  [[ "${NON_INTERACTIVE}" -eq 1 ]] && return 1
  local answer
  read -r -p "${1} [y/N]: " answer
  [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

gen_hex()      { openssl rand -hex "${1:-32}"; }
gen_fernet()   { openssl rand -base64 32 | tr '/+' '_-'; }   # 44-char urlsafe key
gen_password() { openssl rand -base64 16 | tr -d '=' | tr '/+' '_-'; }

dc() { docker compose --project-directory "${REPO_DIR}" -f "${REPO_DIR}/${COMPOSE_FILE}" "$@"; }

arch_map() { # arch_map -> x64/amd64|arm64|arm64
  case "$(uname -m)" in
    x86_64) printf '%s' "${1:-x64}" ;;
    aarch64|arm64) printf '%s' "${2:-arm64}" ;;
    *) printf '%s' "unsupported" ;;
  esac
}

in_container() {
  [[ -f /.dockerenv || -f /run/.containerenv ]] && return 0
  grep -qE "/(docker|lxc)/" /proc/1/cgroup 2>/dev/null && return 0
  return 1
}

docker_ok() {
  command -v docker >/dev/null 2>&1 || return 1
  docker info >/dev/null 2>&1
}

is_systemd() { [[ "$(ps -p 1 -o comm= 2>/dev/null)" == "systemd" ]]; }

# -------------------------------------------------------------- CLI args ----
POS_ARGS=()
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      install|start|stop|restart|logs|status|backup|uninstall)
        CMD="$1" ;;
      -d|--domain)        CAVRIX_DOMAIN="${2:-}"; shift ;;
      -e|--email)         ACME_EMAIL="${2:-}"; shift ;;
      -t|--cf-token)      CF_TOKEN="${2:-}"; shift ;;
      -z|--cf-zone-id)    CF_ZONE_ID="${2:-}"; shift ;;
      -a|--admin-email)   ADMIN_EMAIL="${2:-}"; shift ;;
      -p|--admin-password) ADMIN_PASSWORD="${2:-}"; shift ;;
      --adgem-postback-key) ADGEM_POSTBACK_KEY="${2:-}"; shift ;;
      --mode)             MODE="${2:-auto}"; shift ;;
      --repo-dir)         REPO_DIR="${2:-}"; shift ;;
      -y|--yes)           ASSUME_YES=1 ;;
      -n|--non-interactive) NON_INTERACTIVE=1 ;;
      --no-firewall)      NO_FIREWALL=1 ;;
      --regenerate-secrets) REGENERATE_SECRETS=1 ;;
      -h|--help)          usage; exit 0 ;;
      *)
        if [[ "$1" == -* ]]; then
          die "Unknown option: $1 (see --help)"
        fi
        POS_ARGS+=("$1") ;;
    esac
    shift
  done
}

usage() {
  cat <<'EOF'
Cavrix Cloud - all-in-one installer / manager

Usage:
  ./install.sh [command] [options]

Commands (default: install):
  install      Full install (or update) of the platform
  start        start all services
  stop         stop all services
  restart      restart all services
  logs         tail logs for a service (default: all)
  status       show service status + backend health
  backup       backup the database into ./backups/
  uninstall    remove services + data (keeps .env)

Options:
  -d, --domain <domain>       Public domain (e.g. cavrix.example.com)
  -e, --email <email>         Let's Encrypt / Cloudflare account email
  -t, --cf-token <token>      Cloudflare API token (Zone.DNS:Edit) for
                              auto DNS records + DNS-01 TLS challenge
  -z, --cf-zone-id <zone>     Cloudflare zone id (auto-detected if omitted)
  -a, --admin-email <email>   Seed admin email   [default: admin@cavrix.cloud]
  -p, --admin-password <pass> Seed admin password [default: auto-generated]
      --adgem-postback-key <key>
                              AdGem postback HMAC secret (v3 POST verification)
      --mode <auto|docker|native>
                              auto: Docker Compose if a daemon exists, else
                              native (SQLite, no Redis)  [default: auto]
      --repo-dir <dir>        Project directory [default: script dir or /opt/cavrix]
      --regenerate-secrets    Create fresh SECRET_KEY/ENCRYPTION_KEY/DB password
  -y, --yes                   Assume yes for all prompts
  -n, --non-interactive       Fail on missing values instead of prompting
      --no-firewall           Skip UFW configuration
  -h, --help                  Show this help
EOF
}

# ------------------------------------------------------ bootstrap/clone ----
ensure_project() {
  if [[ ! -f "${REPO_DIR}/${COMPOSE_FILE}" ]]; then
    if [[ "${REPO_DIR}" == "${SCRIPT_DIR}" ]]; then
      REPO_DIR="${INSTALL_DIR}"
    fi
    if [[ ! -d "${REPO_DIR}" ]]; then
      info "Cloning Cavrix Cloud into ${REPO_DIR} ..."
      mkdir -p "$(dirname "${REPO_DIR}")"
      git clone --depth 1 "${GIT_REPO}" "${REPO_DIR}"
    fi
    if [[ ! -f "${REPO_DIR}/${COMPOSE_FILE}" ]]; then
      die "${REPO_DIR}/${COMPOSE_FILE} not found. Use --repo-dir or clone the repo."
    fi
  elif [[ "${REPO_DIR}" != "${SCRIPT_DIR}" ]] && [[ -d "${REPO_DIR}/.git" ]]; then
    info "Updating existing install in ${REPO_DIR} ..."
    git -C "${REPO_DIR}" pull --ff-only --quiet || warn "git pull failed (continuing with current code)"
  fi
  cd "${REPO_DIR}"
  RUN_DIR="${REPO_DIR}/run"
  LOG_DIR="${REPO_DIR}/logs"
  mkdir -p "${RUN_DIR}" "${LOG_DIR}"
}

# ----------------------------------------------------------- prereqs -------
install_docker() {
  if ! have docker; then
    info "Installing Docker ..."
    curl -fsSL https://get.docker.com | sh || die "Docker install failed."
  fi
  if ! docker compose version >/dev/null 2>&1; then
    die "Docker Compose v2 plugin not available. Install it or use --mode native."
  fi
  info "Docker $(docker --version | awk '{print $3}' | tr -d ',') ready"
}

install_prereqs() {
  info "Installing prerequisites (curl, ca-certificates, git, jq, openssl, python3, node build tools) ..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    # Self-heal broken/incomplete dpkg state (common on fresh VPS images).
    dpkg --configure -a 2>/dev/null || true
    apt-get --fix-broken install -y -qq >/dev/null 2>&1 || true
    apt-get update -qq
    # --no-upgrade: only install missing packages. Never upgrade existing ones
    # (btrfs/overlay root filesystems fail dpkg's backup-hardlink with EXDEV).
    apt-get install -y -qq --no-upgrade \
      curl ca-certificates git jq openssl python3 python3-venv xz-utils >/dev/null
  elif have dnf; then
    dnf install -y -q curl ca-certificates git jq openssl python3 python3-virtualenv xz >/dev/null 2>&1 || \
    dnf install -y -q curl ca-certificates git jq openssl python3 xz >/dev/null
  elif have yum; then
    yum install -y -q curl ca-certificates git jq openssl python3 xz >/dev/null
  fi
}

# ------------------------------------------------------ public ip -------
public_ip() {
  local ip=""
  for u in "https://api.ipify.org" "https://ifconfig.me" "https://ipv4.icanhazip.com"; do
    ip="$(curl -fsSL --max-time 8 "$u" 2>/dev/null | tr -d '[:space:]')" && [[ -n "$ip" ]] && break
  done
  [[ -z "$ip" ]] && ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  printf '%s' "$ip"
}

# -------------------------------------------------------------- .env ------
load_env() {
  # Preserve CLI-provided values across a re-run; .env is the stored truth
  # for anything the user did not pass again on the command line.
  local cli_domain="${CAVRIX_DOMAIN}" cli_email="${ACME_EMAIL}" cli_cf="${CF_TOKEN}" cli_admin_pw="${ADMIN_PASSWORD}"
  if [[ -f "${REPO_DIR}/.env" ]]; then
    set +u
    # shellcheck disable=SC1091
    source "${REPO_DIR}/.env"
    set -u
  fi
  CAVRIX_DOMAIN="${cli_domain:-$CAVRIX_DOMAIN}"
  ACME_EMAIL="${cli_email:-$ACME_EMAIL}"
  CF_TOKEN="${cli_cf:-$CF_TOKEN}"
  ADMIN_PASSWORD="${cli_admin_pw:-${SEED_ADMIN_PASSWORD:-$ADMIN_PASSWORD}}"
}

load_env_file() {
  # Export .env into the environment for child processes (alembic, uvicorn).
  set -a
  # shellcheck disable=SC1090
  source "${REPO_DIR}/.env"
  set +a
}

write_env() {
  local need_regenerate=0
  if [[ "${REGENERATE_SECRETS}" -eq 1 ]] || [[ -z "${SECRET_KEY:-}" ]] || \
     [[ -z "${ENCRYPTION_KEY:-}" ]] || [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    need_regenerate=1
  fi
  if [[ "${need_regenerate}" -eq 1 ]]; then
    SECRET_KEY="$(gen_hex 32)"
    ENCRYPTION_KEY="$(gen_fernet)"
    POSTGRES_PASSWORD="$(gen_hex 16)"
  fi
  if [[ -z "${ADMIN_PASSWORD}" ]]; then
    ADMIN_PASSWORD="$(gen_password)"
  fi

  if [[ "${MODE}" == "native" ]]; then
    DATABASE_URL="sqlite+pysqlite:///${REPO_DIR}/data/cavrix.db"
    REDIS_URL="redis://127.0.0.1:6379/0"
  else
    DATABASE_URL="postgresql+psycopg://cavrix:${POSTGRES_PASSWORD}@127.0.0.1:5432/cavrix"
    REDIS_URL="redis://127.0.0.1:6379/0"
  fi

  info "Writing ${REPO_DIR}/.env (mode 600)"
  cat > "${REPO_DIR}/.env" <<EOF
# Generated by install.sh on $(date -u +%F\ %TZ)
APP_ENV=production
DB_AUTO_CREATE=false
MOCK_PROVIDER_ENABLED=false
SECURE_COOKIES=true
CAVRIX_DOMAIN=${CAVRIX_DOMAIN}
CORS_ORIGINS=https://${CAVRIX_DOMAIN}
FRONTEND_URL=https://${CAVRIX_DOMAIN}
PUBLIC_BASE_URL=https://${CAVRIX_DOMAIN}
DATABASE_URL=${DATABASE_URL}
REDIS_URL=${REDIS_URL}
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SEED_ADMIN_EMAIL=${ADMIN_EMAIL}
SEED_ADMIN_PASSWORD=${ADMIN_PASSWORD}
CLOUDFLARE_DNS_API_TOKEN=${CF_TOKEN}
ACME_EMAIL=${ACME_EMAIL}
ADGEM_POSTBACK_KEY=${ADGEM_POSTBACK_KEY:-}
EOF
  chmod 600 "${REPO_DIR}/.env"
  mkdir -p "${REPO_DIR}/data"
}

# --------------------------------------------------- Caddyfile ----------
write_caddyfile() {
  info "Writing ${REPO_DIR}/.Caddyfile (mode 600)"
  local API_DOMAIN="api.${CAVRIX_DOMAIN#*.}"
  {
    if [[ -n "${ACME_EMAIL}" ]]; then
      echo "{"
      echo "    email ${ACME_EMAIL}"
      echo "}"
    fi
    echo "${CAVRIX_DOMAIN}, www.${CAVRIX_DOMAIN} {"
    if [[ -n "${CF_TOKEN}" ]]; then
      echo "    tls {"
      echo "        dns cloudflare {env.CLOUDFLARE_DNS_API_TOKEN}"
      echo "    }"
    fi
    echo "    encode gzip zstd"
    if [[ "${MODE}" == "native" ]]; then
      echo "    root * ${REPO_DIR}/frontend/dist"
      echo "    handle /api/* {"
      echo "        reverse_proxy 127.0.0.1:8000"
      echo "    }"
      echo "    handle /ws {"
      echo "        reverse_proxy 127.0.0.1:8000"
      echo "    }"
      echo "    file_server"
    else
      echo "    reverse_proxy frontend:80"
    fi
    echo "}"
    echo ""
    echo "${API_DOMAIN} {"
    if [[ -n "${CF_TOKEN}" ]]; then
      echo "    tls {"
      echo "        dns cloudflare {env.CLOUDFLARE_DNS_API_TOKEN}"
      echo "    }"
    fi
    echo "    encode gzip zstd"
    if [[ "${MODE}" == "native" ]]; then
      echo "    reverse_proxy 127.0.0.1:8000"
    else
      echo "    reverse_proxy backend:8000"
    fi
    echo "}"
  } > "${REPO_DIR}/.Caddyfile"
  chmod 600 "${REPO_DIR}/.Caddyfile"
}

# ------------------------------------------------------ Cloudflare ------
cf_zone() {
  # Find the registered zone for CAVRIX_DOMAIN by walking up the label chain
  # (dash.cavrix.cloud -> cavrix.cloud), in case a subdomain is used.
  local d="${CAVRIX_DOMAIN}" zone
  while [[ -n "$d" ]]; do
    zone="$(curl -fsSL --max-time 20 -H "Authorization: Bearer ${CF_TOKEN}" \
      "https://api.cloudflare.com/client/v4/zones?name=${d}" | jq -r '.result[0].id // empty')"
    [[ -n "$zone" ]] && { printf '%s' "$zone"; return 0; }
    d="${d#*.}"
  done
  return 1
}

cf_dns_record() { # cf_dns_record <zone> <type> <name> <content> <proxied>
  local zone="$1" type="$2" name="$3" content="$4" proxied="$5"
  local payload search_name
  payload="$(jq -n --arg t "$type" --arg n "$name" --arg c "$content" --argjson p "$proxied" \
    '{type:$t,name:$n,content:$c,proxied:$p,ttl:1}')"
  curl -fsSL --max-time 20 -X POST \
    -H "Authorization: Bearer ${CF_TOKEN}" -H "Content-Type: application/json" \
    --data "$payload" \
    "https://api.cloudflare.com/client/v4/zones/${zone}/dns_records" \
    >/dev/null 2>&1 && return 0
  # Update instead if record already exists.
  if [[ "$name" == "@" ]]; then
    search_name="${CAVRIX_DOMAIN}"
  else
    search_name="${name}.${CAVRIX_DOMAIN}"
  fi
  local id
  id="$(curl -fsSL --max-time 20 -H "Authorization: Bearer ${CF_TOKEN}" \
    "https://api.cloudflare.com/client/v4/zones/${zone}/dns_records?type=${type}&name=${search_name}" \
    | jq -r '.result[0].id // empty')"
  [[ -z "$id" ]] && return 1
  curl -fsSL --max-time 20 -X PUT \
    -H "Authorization: Bearer ${CF_TOKEN}" -H "Content-Type: application/json" \
    --data "$payload" \
    "https://api.cloudflare.com/client/v4/zones/${zone}/dns_records/${id}" \
    >/dev/null 2>&1
}

setup_cloudflare() {
  local ip
  ip="$(public_ip)"
  [[ -z "$ip" ]] && { warn "Could not detect public IP - skipping automatic DNS records."; return 0; }
  info "Server public IP: ${ip}"

  if [[ -z "${CF_ZONE_ID}" ]]; then
    info "Detecting Cloudflare zone id for ${CAVRIX_DOMAIN} ..."
    CF_ZONE_ID="$(cf_zone || true)"
  fi
  if [[ -z "${CF_ZONE_ID}" ]]; then
    warn "Could not resolve zone id. Add A record manually in Cloudflare:"
    warn "  type=A name=@ content=${ip} proxied=YES"
    warn "  type=A name=www content=${ip} proxied=YES"
    return 0
  fi

  info "Creating DNS records for ${CAVRIX_DOMAIN} -> ${ip} (proxied)"
  cf_dns_record "$CF_ZONE_ID" "A" "@" "$ip" true || warn "Could not set A record for @ (may need manual DNS)."
  cf_dns_record "$CF_ZONE_ID" "A" "www" "$ip" true || warn "Could not set A record for www (may need manual DNS)."

  local api_sub="${CAVRIX_DOMAIN%%.*}"
  local api_name="${api_sub}"
  if [[ "${api_name}" == "dash" ]] || [[ "${api_name}" == "www" ]]; then
    api_name="api"
  fi
  info "Creating DNS record for ${api_name}.${CAVRIX_DOMAIN#*.} -> ${ip} (proxied)"
  cf_dns_record "$CF_ZONE_ID" "A" "${api_name}" "$ip" true || warn "Could not set A record for api subdomain (may need manual DNS)."
}

# ------------------------------------------------------------- config -----
collect_config() {
  [[ -z "${CAVRIX_DOMAIN}" ]] && [[ "${NON_INTERACTIVE}" -eq 1 ]] && die "--domain is required in non-interactive mode"
  if [[ -z "${CAVRIX_DOMAIN}" ]]; then
    prompt CAVRIX_DOMAIN "Public domain (via Cloudflare)" ""
  fi
  [[ "$CAVRIX_DOMAIN" =~ ^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]] || die "Invalid domain: ${CAVRIX_DOMAIN}"

  if [[ -z "${ACME_EMAIL}" ]] && [[ "${NON_INTERACTIVE}" -ne 1 ]] && [[ "${ASSUME_YES}" -ne 1 ]]; then
    prompt ACME_EMAIL "Email for Let's Encrypt / Cloudflare" ""
  fi
  if [[ -z "${CF_TOKEN}" ]] && [[ "${NON_INTERACTIVE}" -ne 1 ]] && [[ "${ASSUME_YES}" -ne 1 ]]; then
    prompt CF_TOKEN "Cloudflare API token (optional, DNS:Edit on zone)" ""
  fi
  if [[ -z "${ADMIN_PASSWORD}" ]] && [[ "${NON_INTERACTIVE}" -ne 1 ]] && [[ "${ASSUME_YES}" -ne 1 ]]; then
    read -r -p "Seed admin password (blank = auto-generate): " -s ADMIN_PASSWORD
    echo
  fi
}

# ----------------------------------------------------------- firewall -----
setup_firewall() {
  [[ "${NO_FIREWALL}" -eq 1 ]] && return 0
  if have ufw; then
    if confirm "Configure UFW to allow SSH(22), HTTP(80), HTTPS(443) and enable it?"; then
      ufw allow 22/tcp >/dev/null
      ufw allow 80/tcp >/dev/null
      ufw allow 443/tcp >/dev/null
      ufw --force enable >/dev/null
      info "UFW enabled (22/80/443 allowed)."
    fi
  fi
}

# ----------------------------------------------------------- health --------
wait_healthy() {
  info "Waiting for backend to become healthy (up to 240s) ..."
  local i
  for i in $(seq 1 48); do
    if curl -fsSL --max-time 5 "http://127.0.0.1:8000/healthz" >/dev/null 2>&1; then
      info "Backend is healthy."
      return 0
    fi
    sleep 5
  done
  warn "Backend did not become healthy in time. Check: ./install.sh logs"
}

# ============================================================ NATIVE MODE ==
install_node() {
  if have node && [[ "$(node -v 2>/dev/null)" == v1[89]* || "$(node -v 2>/dev/null)" == v2* ]]; then
    info "Node $(node -v) present"
    return 0
  fi
  local a
  a="$(arch_map x64 arm64)"
  [[ "$a" == "unsupported" ]] && die "Unsupported architecture for Node: $(uname -m)"
  info "Installing Node ${NODE_VERSION} (${a}) to /opt ..."
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${a}.tar.xz" -o /tmp/node.tar.xz
  tar -xJf /tmp/node.tar.xz -C /opt
  ln -sfn "/opt/node-v${NODE_VERSION}-linux-${a}" /opt/node
  export PATH="/opt/node/bin:${PATH}"
  info "Node $(/opt/node/bin/node -v) installed"
}

install_caddy() {
  if have caddy; then
    info "Caddy $(caddy version 2>/dev/null | head -c 40) present"
    return 0
  fi
  local a
  a="$(arch_map amd64 arm64)"
  [[ "$a" == "unsupported" ]] && die "Unsupported architecture for Caddy: $(uname -m)"
  info "Installing Caddy (with Cloudflare DNS module) ..."
  curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=${a}&p=github.com/caddy-dns/cloudflare" \
    -o /tmp/caddy.tar.gz
  tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy
  chmod +x /usr/local/bin/caddy
  info "Caddy installed: /usr/local/bin/caddy"
}

native_py() {
  if [[ ! -d "${REPO_DIR}/venv" ]]; then
    info "Creating Python virtualenv ..."
    python3 -m venv "${REPO_DIR}/venv"
  fi
  "${REPO_DIR}/venv/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1 || true
  info "Installing Python dependencies ..."
  "${REPO_DIR}/venv/bin/pip" install --quiet -r "${REPO_DIR}/backend/requirements.txt"
}

native_migrate() {
  info "Creating database schema (alembic upgrade head) ..."
  cd "${REPO_DIR}/backend"
  load_env_file
  "${REPO_DIR}/venv/bin/alembic" upgrade head
  cd "${REPO_DIR}"
}

native_frontend() {
  export PATH="/opt/node/bin:${PATH}"
  if ! have npm; then
    die "npm not found - Node install failed."
  fi
  cd "${REPO_DIR}/frontend"
  info "Installing frontend dependencies (this can take a few minutes) ..."
  npm install --no-audit --no-fund
  info "Building frontend ..."
  npm run build
  cd "${REPO_DIR}"
}

# ---- service management (pid files) ----
_native_cmd() {
  # _native_cmd <service> <run-command...>  (launches detached, writes pid)
  local name="$1"; shift
  local pidfile="${RUN_DIR}/${name}.pid"
  nohup "$@" >"${LOG_DIR}/${name}.log" 2>&1 &
  echo $! > "${pidfile}"
  info "started ${name} (pid $(cat "${pidfile}"))"
}

native_stop_one() {
  local name="$1"
  local pidfile="${RUN_DIR}/${name}.pid"
  if [[ -f "${pidfile}" ]] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
    kill "$(cat "${pidfile}")" 2>/dev/null || true
    sleep 2
    kill -9 "$(cat "${pidfile}")" 2>/dev/null || true
    rm -f "${pidfile}"
    info "stopped ${name}"
  fi
}

native_start() {
  [[ -d "${REPO_DIR}/venv" ]] || die "Not installed in native mode yet. Run: ./install.sh install"
  load_env_file
  export PATH="/opt/node/bin:${PATH}"

  if [[ -f "${RUN_DIR}/caddy.pid" ]] && kill -0 "$(cat "${RUN_DIR}/caddy.pid")" 2>/dev/null; then
    : # already running
  else
    _native_cmd caddy /usr/local/bin/caddy run --config "${REPO_DIR}/.Caddyfile" --adapter caddyfile
  fi

  if [[ -f "${RUN_DIR}/backend.pid" ]] && kill -0 "$(cat "${RUN_DIR}/backend.pid")" 2>/dev/null; then
    : # already running
  else
    (
      cd "${REPO_DIR}/backend"
      _native_cmd backend "${REPO_DIR}/venv/bin/uvicorn" \
        app.main:app --host 127.0.0.1 --port 8000
    )
  fi

  if [[ -f "${RUN_DIR}/worker.pid" ]] && kill -0 "$(cat "${RUN_DIR}/worker.pid")" 2>/dev/null; then
    : # already running
  else
    (
      cd "${REPO_DIR}/backend"
      _native_cmd worker "${REPO_DIR}/venv/bin/python" -m app.workers.worker
    )
  fi
}

native_stop() {
  native_stop_one worker
  native_stop_one backend
  native_stop_one caddy
}

native_status() {
  local name
  for name in caddy backend worker; do
    local pidfile="${RUN_DIR}/${name}.pid"
    if [[ -f "${pidfile}" ]] && kill -0 "$(cat "${pidfile}")" 2>/dev/null; then
      printf '  %-9s running (pid %s)\n' "${name}" "$(cat "${pidfile}")"
    else
      printf '  %-9s stopped\n' "${name}"
    fi
  done
}

native_logs() {
  local svc="${1:-all}"
  local files=()
  case "${svc}" in
    backend|worker|caddy) files=("${LOG_DIR}/${svc}.log") ;;
    *) files=("${LOG_DIR}/caddy.log" "${LOG_DIR}/backend.log" "${LOG_DIR}/worker.log") ;;
  esac
  tail -f --lines=100 "${files[@]}"
}

native_install() {
  info "Mode: native (no Docker daemon required - SQLite + venv + Caddy)"
  touch "${REPO_DIR}/${NATIVE_MARKER}"
  install_node
  install_caddy
  native_py
  native_migrate
  native_frontend
  write_caddyfile
  native_start
  wait_healthy
}

# ============================================================ DOCKER MODE ==
docker_install() {
  info "Mode: docker (Compose stack: postgres + redis + backend + worker + frontend + caddy)"
  rm -f "${REPO_DIR}/${NATIVE_MARKER}"
  install_docker
  write_caddyfile
  info "Building images (first run takes a few minutes) ..."
  dc up -d --build
  wait_healthy
}

# ----------------------------------------------------------- install ------
cmd_install() {
  install_prereqs
  ensure_project
  load_env
  collect_config
  setup_cloudflare

  case "${MODE}" in
    docker)  MODE="docker" ;;
    native)  MODE="native" ;;
    auto)
      if docker_ok; then MODE="docker"; else MODE="native"; fi ;;
    *) die "Unknown mode: ${MODE} (auto|docker|native)" ;;
  esac
  info "Install mode: ${MODE}"

  write_env
  setup_firewall

  if [[ "${MODE}" == "native" ]]; then
    native_install
  else
    docker_install
  fi

  echo
  printf '%s%s============================================================%s\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
  printf '%s  Cavrix Cloud is live!%s\n' "$C_BOLD" "$C_RESET"
  printf '%s  URL:            %shttps://%s%s\n' "$C_BOLD" "$C_RESET" "$CAVRIX_DOMAIN" "$C_RESET"
  printf '%s  Admin email:    %s%s\n' "$C_BOLD" "$C_RESET" "$ADMIN_EMAIL"
  printf '%s  Admin password: %s%s\n' "$C_BOLD" "$C_RESET" "$ADMIN_PASSWORD"
  printf '%s============================================================%s\n' "$C_BOLD" "$C_GREEN" "$C_RESET"
  echo
  warn "Save the admin password somewhere safe. A super-admin MUST enable 2FA on first login."
  warn "Credentials are stored in ${REPO_DIR}/.env (mode 600)."
}

# ------------------------------------------------------------ control -----
is_native() { [[ -f "${REPO_DIR}/${NATIVE_MARKER}" ]]; }

cmd_start() {
  ensure_project
  if is_native; then native_start; else dc up -d; fi
}

cmd_stop() {
  ensure_project
  if is_native; then native_stop; else dc down; fi
}

cmd_restart() {
  ensure_project
  if is_native; then native_stop; native_start; else dc restart; fi
}

cmd_logs() {
  ensure_project
  if is_native; then
    native_logs "${1:-all}"
  else
    local extra=()
    [[ $# -gt 0 ]] && extra=("$@")
    dc logs -f --tail=200 "${extra[@]}"
  fi
}

cmd_status() {
  ensure_project
  if is_native; then
    native_status
  else
    dc ps
  fi
  echo
  if curl -fsSL --max-time 5 "http://127.0.0.1:8000/healthz" >/dev/null 2>&1; then
    info "Backend health: OK $(curl -fsSL http://127.0.0.1:8000/healthz 2>/dev/null)"
  else
    warn "Backend health: not reachable (is it running?)"
  fi
}

cmd_backup() {
  ensure_project
  local dir="${REPO_DIR}/backups" stamp
  stamp="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$dir"
  if is_native; then
    info "Backing up database to ${dir}/cavrix_${stamp}.db"
    cp "${REPO_DIR}/data/cavrix.db" "${dir}/cavrix_${stamp}.db"
    info "Backup complete: ${dir}/cavrix_${stamp}.db"
  else
    info "Backing up database to ${dir}/cavrix_${stamp}.dump"
    dc exec -T db pg_dump -U cavrix -d cavrix -Fc > "${dir}/cavrix_${stamp}.dump"
    info "Backup complete: ${dir}/cavrix_${stamp}.dump"
  fi
}

cmd_uninstall() {
  ensure_project
  if confirm "This removes all services and DATA (database lost). .env/.Caddyfile kept. Continue?"; then
    if is_native; then
      native_stop
      rm -rf "${REPO_DIR}/venv" "${REPO_DIR}/data" "${REPO_DIR}/frontend/node_modules" "${REPO_DIR}/frontend/dist"
    else
      dc down -v
      docker system prune -af --volumes || true
    fi
    info "Cavrix Cloud removed. .env/.Caddyfile kept in ${REPO_DIR}."
  fi
}

# --------------------------------------------------------------- main -----
main() {
  [[ "$(id -u)" -eq 0 ]] || warn "Not running as root. Docker/sudo may be needed."
  case "${CMD}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    logs) cmd_logs "${POS_ARGS[@]}" ;;
    status) cmd_status ;;
    backup) cmd_backup ;;
    uninstall) cmd_uninstall ;;
    install) cmd_install ;;
    *) die "Unknown command: ${CMD}" ;;
  esac
}

parse_args "$@"
main
