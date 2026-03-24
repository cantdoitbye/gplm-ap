#!/bin/bash

set -e

PROJECT_DIR="/home/ai-govt/gplm-ap"
SERVER_IP="135.222.42.174"
REPO_URL="https://github.com/cantdoitbye/gplm-ap.git"

echo "========================================"
echo "  GPLM-AP Deployment Script"
echo "========================================"

if [ ! -d "$PROJECT_DIR" ]; then
    echo ""
    echo "First-time deployment: Cloning repository..."
    cd /home/ai-govt
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
    echo ""
    echo "IMPORTANT: Edit .env file before continuing!"
    echo "Run: nano $PROJECT_DIR/.env"
    echo "Then run this script again."
    exit 0
fi

cd "$PROJECT_DIR"

echo ""
echo "Pulling latest changes..."
git stash 2>/dev/null || true
git pull

echo ""
echo "Stopping existing containers..."
docker compose -f docker-compose.prod.yml down

echo ""
echo "Building and starting containers..."
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "Waiting for services to be healthy..."
sleep 10

echo ""
echo "Checking service status..."
docker compose -f docker-compose.prod.yml ps

echo ""
FRONTEND_PORT=$(docker port gplm-ap-frontend 80 2>/dev/null | cut -d: -f2)
BACKEND_PORT=$(docker port gplm-ap-backend 8000 2>/dev/null | cut -d: -f2)

echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
if [ -n "$FRONTEND_PORT" ]; then
    echo "Frontend:    http://$SERVER_IP:$FRONTEND_PORT"
fi
if [ -n "$BACKEND_PORT" ]; then
    echo "Backend API: http://$SERVER_IP:$BACKEND_PORT"
    echo "API Docs:    http://$SERVER_IP:$BACKEND_PORT/docs"
fi
echo "========================================"
