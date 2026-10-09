#!/usr/bin/env bash
# SABIGOZAR Panel entrypoint  ·  @SAHEBKARAMI
set -uo pipefail
DATA="${SABI_DATA:-/var/lib/sabigozar}"
export PORT="${PORT:-8080}"
log(){ echo "[SABIGOZAR] $*"; }
mkdir -p "$DATA/certs" "$DATA/backups" /var/lib/pg-node/generated

SECRETS="$DATA/secrets.env"
if [ ! -s "$SECRETS" ]; then
  ( umask 077
    { echo "NODE_API_KEY=$(python -c 'import uuid;print(uuid.uuid4())')"
      echo "PATH_SEED=$(python -c 'import secrets;print(secrets.token_hex(6))')"
    } > "$SECRETS" )
  log "new install: secrets generated"
fi
if ! grep -q '^REALITY_PRIVATE_KEY=' "$SECRETS"; then
  RPK="$(/usr/local/bin/xray x25519 2>/dev/null | awk -F': *' 'tolower($1) ~ /private/ {print $2; exit}')"
  if [ -n "$RPK" ]; then
    { echo "REALITY_PRIVATE_KEY=$RPK"; echo "REALITY_SHORT_ID=$(openssl rand -hex 4)"; } >> "$SECRETS"
    log "Reality keys generated"
  fi
fi
set -a; . "$SECRETS"; set +a

if [ ! -f "$DATA/certs/node.pem" ]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 3650 \
    -keyout "$DATA/certs/node.key" -out "$DATA/certs/node.pem" \
    -subj "/CN=localhost" -addext "subjectAltName=IP:127.0.0.1,DNS:localhost" >/dev/null 2>&1
fi

sed -e "s/__PORT__/${PORT}/g" /etc/nginx/sabigozar/nginx.conf.template > /etc/nginx/nginx.conf
sed -e "s/__SEED__/${PATH_SEED}/g" /etc/nginx/sabigozar/routes.conf.template > /etc/nginx/sabigozar/routes.conf
nginx -t -q || { log "nginx config invalid"; exit 1; }

( cd /opt/pg-node && SERVICE_PORT=62050 NODE_HOST=127.0.0.1 SERVICE_PROTOCOL=grpc \
  API_KEY="$NODE_API_KEY" SSL_CERT_FILE="$DATA/certs/node.pem" SSL_KEY_FILE="$DATA/certs/node.key" \
  exec ./main ) &
NODE_PID=$!

( cd /code && python -m alembic upgrade head && exec python main.py ) &
PANEL_PID=$!

if [ -f /opt/sabigozar/scripts/bootstrap.py ]; then
  ( cd /code && exec python /opt/sabigozar/scripts/bootstrap.py ) &
fi

nginx -g 'daemon off;' &
NGINX_PID=$!
log "started on port ${PORT}"

trap 'kill $NODE_PID $PANEL_PID $NGINX_PID 2>/dev/null; exit 0' TERM INT
wait -n $NODE_PID $PANEL_PID $NGINX_PID
log "a core process exited, restarting container"; exit 1
