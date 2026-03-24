#!/bin/bash

SERVER_IP="135.222.42.174"

echo "========================================"
echo "  GPLM-AP Container Ports"
echo "========================================"
docker ps --filter "name=gplm-ap" --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" 2>/dev/null || echo "No containers found. Is Docker running?"

echo ""
FRONTEND_PORT=$(docker port gplm-ap-frontend 80 2>/dev/null | cut -d: -f2)
BACKEND_PORT=$(docker port gplm-ap-backend 8000 2>/dev/null | cut -d: -f2)

if [ -n "$FRONTEND_PORT" ] || [ -n "$BACKEND_PORT" ]; then
    echo "Access URLs:"
    echo "========================================"
    [ -n "$FRONTEND_PORT" ] && echo "Frontend:    http://$SERVER_IP:$FRONTEND_PORT"
    [ -n "$BACKEND_PORT" ] && echo "Backend API: http://$SERVER_IP:$BACKEND_PORT"
    [ -n "$BACKEND_PORT" ] && echo "API Docs:    http://$SERVER_IP:$BACKEND_PORT/docs"
else
    echo "Containers not running."
    echo "Start with: docker compose -f docker-compose.prod.yml up -d"
fi
