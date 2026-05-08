#!/usr/bin/env bash
# Runs ON the EC2 server during CD. Fast-forwards main, rebuilds the frontend,
# refreshes Python deps, and restarts the systemd unit.
#
# Triggered by .github/workflows/ci.yml (deploy job) over SSH.

set -euo pipefail

APP_DIR="${APP_DIR:-/home/ec2-user/myself_ec2}"
BRANCH="${BRANCH:-main}"

echo "==> Updating $APP_DIR to origin/$BRANCH"
cd "$APP_DIR"

git fetch --prune origin "$BRANCH"
git reset --hard "origin/$BRANCH"

echo "==> Installing backend dependencies"
.venv/bin/pip install --upgrade pip --quiet
.venv/bin/pip install -r backend/requirements.txt --quiet

echo "==> Building frontend"
cd frontend
if [[ -f package-lock.json ]]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build
cd ..

echo "==> Restarting services"
sudo systemctl restart personal-site.service
sudo systemctl reload-or-restart personal-site-healthcheck.timer || true

echo "==> Verifying health endpoint"
sleep 3
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/api/health > /dev/null
echo "==> Deploy complete."
