#!/bin/bash
# Deploy LabelCheck to a remote server via SSH
# Usage: ./deploy.sh <server-ip> [ssh-key-path]

set -e

SERVER_IP="${1:?Usage: ./deploy.sh <server-ip> [ssh-key-path]}"
SSH_KEY="${2:-$HOME/.ssh/labelcheck_ecs}"
SSH_OPTS="-o StrictHostKeyChecking=no -i $SSH_KEY"
SSH="ssh $SSH_OPTS root@$SERVER_IP"
SCP="scp $SSH_OPTS"

echo "=== LabelCheck Deploy to $SERVER_IP ==="

# 1. Install Docker on server (if not installed)
echo "[1/5] Installing Docker..."
$SSH "command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)"
$SSH "command -v docker-compose >/dev/null 2>&1 || docker compose version >/dev/null 2>&1 || (apt-get update && apt-get install -y docker-compose-plugin)"

# 2. Create project directory
echo "[2/5] Preparing server..."
$SSH "mkdir -p /opt/labelcheck/uploads"

# 3. Copy project files
echo "[3/5] Uploading files..."
# Create tarball excluding unnecessary files
tar czf /tmp/labelcheck-deploy.tar.gz \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='uploads/*' \
  --exclude='.git' \
  --exclude='server.log' \
  -C /Users/alekseiriabokon/Desktop/labelcheck .

$SCP /tmp/labelcheck-deploy.tar.gz root@$SERVER_IP:/tmp/
$SSH "cd /opt/labelcheck && tar xzf /tmp/labelcheck-deploy.tar.gz && rm /tmp/labelcheck-deploy.tar.gz"

# 4. Copy .env file
echo "[4/5] Setting up environment..."
$SCP /Users/alekseiriabokon/Desktop/labelcheck/.env root@$SERVER_IP:/opt/labelcheck/.env

# 5. Build and start
echo "[5/5] Building and starting services..."
$SSH "cd /opt/labelcheck && docker compose up -d --build"

echo ""
echo "=== Deploy complete! ==="
echo "Frontend: http://$SERVER_IP"
echo "Backend API: http://$SERVER_IP/api/v1"
echo "Health check: http://$SERVER_IP/health"
