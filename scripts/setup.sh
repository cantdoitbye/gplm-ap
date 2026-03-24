#!/bin/bash

# AIKOSH-5 Setup Script
# This script sets up the development environment for AIKOSH-5

set -e

echo "======================================"
echo "AIKOSH-5 Development Environment Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check for required tools
echo -e "\n${YELLOW}Checking required tools...${NC}"

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is not installed"
        return 1
    fi
}

# Check required commands
MISSING=0
check_command python3 || MISSING=1
check_command pip3 || MISSING=1
check_command node || MISSING=1
check_command npm || MISSING=1
check_command docker || MISSING=1
check_command docker-compose || MISSING=1
check_command git || MISSING=1

if [ $MISSING -eq 1 ]; then
    echo -e "\n${RED}Please install missing tools before continuing.${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Setup backend
echo -e "\n${YELLOW}Setting up backend...${NC}"

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

cd "$PROJECT_ROOT"

# Setup frontend
echo -e "\n${YELLOW}Setting up frontend...${NC}"

cd frontend

# Install Node dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install
else
    echo "Node modules already installed. Run 'npm install' manually to update."
fi

cd "$PROJECT_ROOT"

# Create environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "\n${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your API credentials${NC}"
fi

# Create data directories
echo -e "\n${YELLOW}Creating data directories...${NC}"
mkdir -p data/satellite/raw
mkdir -p data/satellite/processed
mkdir -p data/osm
mkdir -p data/buildings
mkdir -p data/mock
mkdir -p backend/models

# Start Docker services
echo -e "\n${YELLOW}Starting Docker services...${NC}"
cd infrastructure
docker-compose up -d postgres redis minio
cd "$PROJECT_ROOT"

# Wait for services to be ready
echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Check if services are running
echo -e "\n${YELLOW}Checking service health...${NC}"

# Check PostgreSQL
if docker exec aikosh5-postgres pg_isready -U aikosh5 &> /dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running"
else
    echo -e "${RED}✗${NC} PostgreSQL is not ready"
fi

# Check Redis
if docker exec aikosh5-redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis is not ready"
fi

# Check MinIO
if curl -s http://localhost:9000/minio/health/live &> /dev/null; then
    echo -e "${GREEN}✓${NC} MinIO is running"
else
    echo -e "${RED}✗${NC} MinIO is not ready"
fi

echo -e "\n${GREEN}======================================"
echo "Setup Complete!"
echo "======================================${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Edit .env with your API credentials:"
echo "   - COPERNICUS_USERNAME and COPERNICUS_PASSWORD (from https://dataspace.copernicus.eu/)"
echo "   - MAPBOX_ACCESS_TOKEN (from https://www.mapbox.com/)"
echo ""
echo "2. Generate mock data:"
echo "   cd backend && source venv/bin/activate"
echo "   python -m app.data.mock.generator"
echo ""
echo "3. Start the backend:"
echo "   cd backend && source venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "4. Start the frontend:"
echo "   cd frontend && npm run dev"
echo ""
echo "5. Access the application:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
