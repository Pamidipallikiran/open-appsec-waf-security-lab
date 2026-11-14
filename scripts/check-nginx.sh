#!/usr/bin/env bash
# Run `nginx -t` against the repository's NGINX configurations in a throwaway container.
#
# Needs Docker and permission to pull the NGINX image. The open-appsec attachment is not
# loaded, so this checks configuration syntax only; it says nothing about WAF behaviour.
# A temporary self-signed certificate stands in for the MISP frontend certificate.
#
# Usage:  scripts/check-nginx.sh            (override the image with NGINX_IMAGE=...)

set -euo pipefail

IMAGE="${NGINX_IMAGE:-nginx:stable}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 2; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/conf.d" "$TMP/certs"

cp "$ROOT/configurations/nginx/default.conf" "$TMP/conf.d/default.conf"
cp "$ROOT/configurations/nginx/optional/thehive-cortex.conf.example" "$TMP/conf.d/thehive-cortex.conf"
cp "$ROOT/configurations/nginx/optional/misp.conf.example" "$TMP/conf.d/misp.conf"

openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=lab-test" \
  -keyout "$TMP/certs/misp.key" -out "$TMP/certs/misp.crt" >/dev/null 2>&1

cat > "$TMP/nginx.conf" <<'EOF'
events {}
http {
  include /etc/nginx/conf.d/*.conf;
}
EOF

chmod -R a+rX "$TMP"

docker run --rm \
  -v "$TMP/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$TMP/conf.d:/etc/nginx/conf.d:ro" \
  -v "$TMP/certs:/etc/nginx/certs:ro" \
  "$IMAGE" nginx -t
