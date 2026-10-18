#!/usr/bin/env bash
# Activ-Ate – install the frontend on a fresh Google Cloud VM (Debian 12 / Ubuntu 22.04+).
#
# Usage (on the VM, inside the unpacked project folder):
#   sudo bash deploy/setup-vm.sh                 # install / update the site
#   sudo bash deploy/setup-vm.sh activ-ate.example.com you@example.com   # + HTTPS via Let's Encrypt
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
SRC="$(cd "$(dirname "$0")/.." && pwd)"
WEBROOT=/var/www/activ-ate

if [[ $EUID -ne 0 ]]; then echo "Please run with sudo." >&2; exit 1; fi

echo "==> Installing nginx"
apt-get update -y
apt-get install -y nginx rsync

echo "==> Copying site to $WEBROOT"
mkdir -p "$WEBROOT"
rsync -a --delete --exclude 'docs/' --exclude 'deploy/' --exclude '.git/' --exclude '*.md' "$SRC/" "$WEBROOT/"
chown -R www-data:www-data "$WEBROOT"

echo "==> Configuring nginx"
cp "$SRC/deploy/nginx.conf" /etc/nginx/sites-available/activ-ate
if [[ -n "$DOMAIN" ]]; then
  sed -i "s/server_name _;/server_name $DOMAIN;/" /etc/nginx/sites-available/activ-ate
fi
ln -sf /etc/nginx/sites-available/activ-ate /etc/nginx/sites-enabled/activ-ate
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

if [[ -n "$DOMAIN" && -n "$EMAIL" ]]; then
  echo "==> Requesting HTTPS certificate for $DOMAIN"
  apt-get install -y certbot python3-certbot-nginx
  certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --non-interactive --redirect
fi

IP=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip || true)
echo
echo "Done. Open: http://${DOMAIN:-$IP}/"
