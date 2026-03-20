#!/usr/bin/env bash

set -euo pipefail

EC2_HOST="${EC2_HOST:-}"
EC2_USER="${EC2_USER:-ec2-user}"
APP_NAME="${APP_NAME:-myself_ec2}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-/home/${EC2_USER}/${APP_NAME}}"
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
  "SERVER_NAME='${SERVER_NAME}' REMOTE_APP_DIR='${REMOTE_APP_DIR}' bash -s" <<'EOF'
set -euo pipefail

sudo dnf install -y nginx rsync python3 python3-pip
cd "${REMOTE_APP_DIR}"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
fi

sudo cp "${REMOTE_APP_DIR}/deploy/nginx-personal-site.conf" /etc/nginx/conf.d/personal-site.conf
sudo cp "${REMOTE_APP_DIR}/deploy/personal-site.service" /etc/systemd/system/personal-site.service

if [[ "${SERVER_NAME}" != "_" ]]; then
  sudo sed -i.bak "s/server_name _;/server_name ${SERVER_NAME};/" /etc/nginx/conf.d/personal-site.conf
fi

sudo systemctl daemon-reload
sudo systemctl enable --now personal-site.service
sudo systemctl restart personal-site.service
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
EOF

echo "Deployment complete."
echo "Public URL: http://${EC2_HOST}"
