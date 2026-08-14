#!/usr/bin/env bash
# ============================================================================
#  Cavrix Cloud - all-in-one installer / manager
#
#  Installs the Cavrix Cloud dashboard on a fresh Linux VPS (Ubuntu/Debian)
#  with Docker, wires a custom domain through Cloudflare, provisions a
#  Let's Encrypt certificate (DNS-01 via Cloudflare API when a token is
#  supplied), and prints your admin credentials.
#
#  One-liner (run as root):
#      bash <(curl -fsSL https://raw.githubusercontent.com/FaaizJohar/CavrixDash/main/install.sh) \
#          --domain cavrix.example.com --email you@mail.com --cf-token <CF_API_TOKEN>
#
#  Subcommands: install | start | stop | restart | logs | status | backup | uninstall
#
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

CAVRIX_DOMAIN=""
ACME_EMAIL=""
CF_TOKEN=""
CF_ZONE_ID=""
ADMIN_EMAIL="admin@cavrix.cloud"
ADMIN_PASSWORD=""
ASSUME_YES=0
NON_INTERACTIVE=0
NO_FIREWALL=0
REGENERATE_SECRETS=0
CMD="${1:-install}"

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
  start        docker compose up -d
  stop         docker compose down
  restart      restart all services
  logs         tail logs for a service (default: all)
  status       show container status + backend health
  backup       pg_dump the database into ./backups/
  uninstall    stop + remove containers/volumes/images (keeps .env)

Options:
  -d, --domain <domain>       Public domain (e.g. cavrix.example.com)
  -e, --email <email>         Let's Encrypt / Cloudflare account email
  -t, --cf-token <token>      Cloudflare API token (Zone.DNS:Edit) for
                              auto DNS records + DNS-01 TLS challenge
  -z, --cf-zone-id <zone>     Cloudflare zone id (auto-detected if omitted)
  -a, --admin-email <email>   Seed admin email   [default: admin@cavrix.cloud]
  -p, --admin-password <pass> Seed admin password [default: auto-generated]
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
  fi
  cd "${REPO_DIR}"
}

# ----------------------------------------------------------- prereqs -------
install_docker() {
  if ! have docker; then
    info "Installing Docker ..."
    curl -fsSL https://get.docker.com | sh
  fi
  if ! docker compose version >/dev/null 2>&1; then
    die "Docker Compose v2 plugin not available. Install it and re-run."
  fi
  info "Docker $(docker --version | awk '{print $3}' | tr -d ',') ready"
}

install_prereqs() {
  info "Installing prerequisites (curl, ca-certificates, git, jq, openssl, python3) ..."
  if have apt-get; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq curl ca-certificates git jq openssl python3 >/dev/null
  elif have dnf; then
    dnf install -y -q curl ca-certificates git jq openssl python3
  elif have yum; then
    yum install -y -q curl ca-certificates git jq openssl python3
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
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SEED_ADMIN_EMAIL=${ADMIN_EMAIL}
SEED_ADMIN_PASSWORD=${ADMIN_PASSWORD}
CLOUDFLARE_DNS_API_TOKEN=${CF_TOKEN}
ACME_EMAIL=${ACME_EMAIL}
EOF
  chmod 600 "${REPO_DIR}/.env"
}

# --------------------------------------------------- Caddyfile ----------
write_caddyfile() {
  info "Writing ${REPO_DIR}/.Caddyfile (mode 600)"
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
    echo "    reverse_proxy frontend:80"
    echo "}"
  } > "${REPO_DIR}/.Caddyfile"
  chmod 600 "${REPO_DIR}/.Caddyfile"
}

# ------------------------------------------------------ Cloudflare ------
cf_zone() {
  local zone
  zone="$(curl -fsSL --max-time 20 -H "Authorization: Bearer ${CF_TOKEN}" \
    "https://api.cloudflare.com/client/v4/zones?name=${CAVRIX_DOMAIN}" | jq -r '.result[0].id // empty')"
  printf '%s' "$zone"
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
  info "Waiting for backend to become healthy (up to 180s) ..."
  local i
  for i in $(seq 1 36); do
    if curl -fsSL --max-time 5 "http://127.0.0.1:8000/healthz" >/dev/null 2>&1; then
      info "Backend is healthy."
      return 0
    fi
    sleep 5
  done
  warn "Backend did not become healthy in time. Check: ./install.sh logs"
}

# ----------------------------------------------------------- install ------
cmd_install() {
  ensure_project
  install_prereqs
  install_docker
  load_env
  collect_config
  setup_cloudflare
  write_env
  write_caddyfile
  setup_firewall

  info "Building images (first run takes a few minutes) ..."
  dc up -d --build

  wait_healthy

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
cmd_start()    { ensure_project; dc up -d; }
cmd_stop()     { ensure_project; dc down; }
cmd_restart()  { ensure_project; dc down; dc up -d; }
cmd_logs()     { ensure_project; local extra=(); [[ $# -gt 0 ]] && extra=("$@"); dc logs -f --tail=200 "${extra[@]}"; }
cmd_status()   {
  ensure_project
  dc ps
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
  info "Backing up database to ${dir}/cavrix_${stamp}.dump"
  dc exec -T db pg_dump -U cavrix -d cavrix -Fc > "${dir}/cavrix_${stamp}.dump"
  info "Backup complete: ${dir}/cavrix_${stamp}.dump"
}
cmd_uninstall() {
  ensure_project
  if confirm "This removes all containers, images and VOLUMES (database data lost). Continue?"; then
    dc down -v
    docker system prune -af --volumes || true
    info "Cavrix Cloud removed. .env/.Caddyfile kept in ${REPO_DIR}."
  fi
}

# --------------------------------------------------------------- main -----
main() {
  [[ "$(id -u)" -eq 0 ]] || warn "Not running as root. Docker/sudo may be needed."
  case "${CMD}" in
    start|stop|restart|status|backup) "${CMD}" ;;
    logs) cmd_logs "${POS_ARGS[@]}" ;;
    install) cmd_install ;;
    *) die "Unknown command: ${CMD}" ;;
  esac
}

parse_args "$@"
main
