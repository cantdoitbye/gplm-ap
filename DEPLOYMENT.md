# AIKOSH-5 MVP Server Deployment Guide

This guide explains how to deploy the AIKOSH-5 MVP on your server alongside the existing nerdcap-2.0 deployment.

## Prerequisites

- Docker and Docker Compose are already installed on your server
- Git is installed
- You have SSH/root access to the server

## Quick Deployment Steps

### 1. Clone the Repository

```bash
cd /home/ai-govt
git clone https://github.com/YOUR-USERNAME/aikosh5-mvp.git
cd aikosh5-mvp
```

Replace `YOUR-USERNAME` with the actual GitHub username/organization where you host the public repo.

### 2. Configure Environment Variables

The `.env` file is already configured for production. You should update these sensitive values:

```bash
nano .env
```

Update these critical values:
- `JWT_SECRET_KEY` - Generate a secure random string (e.g., `openssl rand -hex 32`)
- `COPERNICUS_USERNAME` and `COPERNICUS_PASSWORD` - Your Copernicus Data Space credentials
- `MAPBOX_ACCESS_TOKEN` - Your Mapbox token
- `GOOGLE_EARTH_ENGINE_KEY` - Your GEE key (if using)

### 3. Deploy with Docker Compose

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Seed Initial Users

```bash
docker compose -f docker-compose.prod.yml exec backend python seed_users.py
```

This creates the admin user:
- Email: `abhishek.awasthi@ooumph.com`
- Password: `admin123`

**Important:** Change this password after first login!

### 5. Check Assigned Ports

Since we use random ports to avoid conflicts with nerdcap-2.0, check which ports were assigned:

```bash
docker compose -f docker-compose.prod.yml ps
```

Or for more detail:

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

You'll see output like:
```
NAMES               PORTS
aikosh5-frontend    0.0.0.0:32768->80/tcp
aikosh5-backend     0.0.0.0:32769->8000/tcp
aikosh5-postgres    0.0.0.0:32770->5432/tcp
aikosh5-redis       0.0.0.0:32771->6379/tcp
```

### 6. Access the Application

Access the frontend at: `http://YOUR-SERVER-IP:FRONTEND-PORT`

For example, if frontend port is 32768:
```
http://your-server-ip:32768
```

## Manual Update Process

When you want to update the application:

```bash
cd /home/ai-govt/aikosh5-mvp
git pull
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
```

If only code changed (no Dockerfile changes), you can skip the build:
```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

## Useful Commands

### View Logs
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f frontend
```

### Restart Services
```bash
docker compose -f docker-compose.prod.yml restart
```

### Stop Services
```bash
docker compose -f docker-compose.prod.yml down
```

### Stop and Remove Volumes (Clean Slate)
```bash
docker compose -f docker-compose.prod.yml down -v
```

## Port Management

The `docker-compose.prod.yml` uses `0:port` syntax which tells Docker to assign random available ports. This avoids conflicts with your existing nerdcap-2.0 deployment.

If you prefer specific ports, you can modify the ports section in `docker-compose.prod.yml`:
```yaml
ports:
  - "8081:80"    # Frontend on port 8081
  - "8001:8000"  # Backend on port 8001
```

## Troubleshooting

### Check Container Status
```bash
docker compose -f docker-compose.prod.yml ps
```

### Check Container Health
```bash
docker inspect aikosh5-postgres | grep -A 10 Health
docker inspect aikosh5-redis | grep -A 10 Health
```

### Database Connection Issues
```bash
docker compose -f docker-compose.prod.yml exec backend python -c "from app.database.connection import async_session_maker; import asyncio; asyncio.run(async_session_maker())"
```

### Reset Everything
```bash
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec backend python seed_users.py
```

## Production Security Checklist

- [ ] Change `JWT_SECRET_KEY` to a secure random value
- [ ] Update default admin password after first login
- [ ] Configure firewall to only expose necessary ports
- [ ] Set up SSL/TLS with a reverse proxy (nginx/traefik) if needed
- [ ] Review and update CORS settings if needed
- [ ] Set up regular database backups
