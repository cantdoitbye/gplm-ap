#!/bin/bash

set -e

PROJECT_DIR="/home/ai-govt/gplm-ap"
SERVER_IP="135.222.42.174"
REPO_URL="https://github.com/cantdoitbye/gplm-ap.git"

echo "========================================"
echo "  GPLM-AP First-Time Setup"
echo "========================================"

if [ -d "$PROJECT_DIR" ]; then
    echo "Error: $PROJECT_DIR already exists!"
    echo "Use deploy.sh for updates instead."
    exit 1
fi

echo ""
echo "Cloning repository to $PROJECT_DIR..."
cd /home/ai-govt
git clone "$REPO_URL"
cd "$PROJECT_DIR"

echo ""
echo "Making scripts executable..."
chmod +x deploy.sh check-ports.sh

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit .env file:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "   Update these values:"
echo "   - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
echo "   - MAPBOX_ACCESS_TOKEN"
echo "   - COPERNICUS_USERNAME / COPERNICUS_PASSWORD"
echo ""
echo "2. Run deployment:"
echo "   cd $PROJECT_DIR && ./deploy.sh"
echo ""
echo "3. Seed admin user:"
echo "   docker compose -f docker-compose.prod.yml exec backend python seed_users.py"
echo "========================================"
