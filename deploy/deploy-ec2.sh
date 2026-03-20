#!/usr/bin/env bash

set -euo pipefail

EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_NAME="${APP_NAME:-personal-site}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/home/${EC2_USER}/${APP_NAME}}"
WEB_ROOT="${WEB_ROOT:-/var/www/personal-site}"
SERVER_NAME="${SERVER_NAME:-_}"

if [[ -z "${EC2_HOST}" ]]; then
  echo "Missing EC2_HOST. Example:"
  echo "  EC2_HOST=1.2.3.4 ./deploy/deploy-ec2.sh"
  exit 1
fi

echo "Uploading project to ${EC2_USER}@${EC2_HOST}:${REMOTE_APP_DIR}"
rsync -avz --delete \
  --exclude ".git" \
  --exclude ".DS_Store" \
  ./ "${EC2_USER}@${EC2_HOST}:${REMOTE_APP_DIR}/"

echo "Configuring nginx and publishing static files on the server"
ssh "${EC2_USER}@${EC2_HOST}" \
  "SERVER_NAME='${SERVER_NAME}' REMOTE_APP_DIR='${REMOTE_APP_DIR}' WEB_ROOT='${WEB_ROOT}' bash -s" <<'EOF'
set -euo pipefail

sudo dnf install -y nginx rsync
sudo mkdir -p "${WEB_ROOT}"
sudo rsync -av --delete \
  --exclude ".git" \
  --exclude ".DS_Store" \
  "${REMOTE_APP_DIR}/" "${WEB_ROOT}/"
sudo cp "${REMOTE_APP_DIR}/deploy/nginx-personal-site.conf" /etc/nginx/conf.d/personal-site.conf

if [[ "${SERVER_NAME}" != "_" ]]; then
  sudo sed -i.bak "s/server_name _;/server_name ${SERVER_NAME};/" /etc/nginx/conf.d/personal-site.conf
fi

sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
EOF

echo "Deployment complete."
echo "Public URL: http://${EC2_HOST}"
