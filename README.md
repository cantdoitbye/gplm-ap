# AIKOSH-5: AI-Enabled Geospatial Property & Land-Use Monitoring

An MVP implementation of the Ooumph Agentic AI Solution for AIKOSH-5 - a sovereign geospatial intelligence ecosystem for monitoring property and land-use changes.

## Overview

This system provides:
- **Property Detection Agent (PDA)**: Detect buildings, roads, and water bodies from satellite imagery
- **Change Detection Agent (CDA)**: Compare temporal imagery to identify new construction and encroachments
- **GIS Auto-Update Agent (GUA)**: Automatically update property records with audit trails
- **Urban Planning Dashboard (UPDA)**: Interactive dashboard with 100+ GIS layers

## Tech Stack

| Layer | Technology |
|-------|------------|
| Satellite Imagery | Sentinel-2 (Copernicus Data Space), Google Earth Engine |
| Backend | Python 3.11, FastAPI, PostgreSQL + PostGIS |
| AI/ML | PyTorch, YOLOv8, Flower (Federated Learning) |
| Frontend | React + TypeScript, Leaflet.js, Recharts |
| Infrastructure | Docker, Redis, MinIO |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Copernicus Data Space account (https://dataspace.copernicus.eu/)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd aikosh5-mvp

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Create Python virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Infrastructure Services

```bash
# From project root
docker-compose up -d

# Wait for services to be ready
docker-compose ps
```

### 3. Initialize Database

```bash
cd backend
alembic upgrade head
```

### 4. Start Backend API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 6. Access the Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

## Project Structure

```
aikosh5-mvp/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── database/            # Database models and connections
│   │   ├── agents/              # AI agents (PDA, CDA, GUA, UPDA)
│   │   ├── orchestration/       # Agent workflow orchestration
│   │   ├── federated/           # Federated learning (Flower)
│   │   ├── trust/               # Trust score and audit system
│   │   ├── data/                # Data pipelines (satellite, OSM, mock)
│   │   └── api/                 # API routes
│   ├── models/                  # Trained ML models
│   ├── tests/                   # Test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API services
│   │   └── App.tsx
│   └── package.json
├── infrastructure/
│   ├── docker-compose.yml       # Development compose
│   └── nginx.conf               # Nginx configuration
├── scripts/
│   ├── setup.sh                 # Setup script
│   └── download_sentinel.py     # Satellite imagery download
└── docs/
    └── api.md                   # API documentation
```

## API Endpoints

### Property Detection Agent (PDA)
- `POST /pda/detect` - Run detection on imagery
- `GET /pda/properties` - Get detected properties
- `POST /pda/match` - Match detections with records

### Change Detection Agent (CDA)
- `POST /cda/compare` - Compare two imagery dates
- `GET /cda/changes` - Get detected changes
- `GET /cda/alerts` - Get generated alerts

### GIS Auto-Update Agent (GUA)
- `GET/POST /gua/records` - CRUD for GIS records
- `GET /gua/audit` - Audit trail queries
- `POST /gua/rollback` - Rollback functionality

## Development

### Run Tests
```bash
cd backend
pytest
```

### Code Formatting
```bash
# Backend
cd backend
black app/
isort app/

# Frontend
cd frontend
npm run lint
```

## Free API Keys Required

| Service | URL | Purpose |
|---------|-----|---------|
| Copernicus Data Space | dataspace.copernicus.eu | Sentinel-2 imagery |
| Google Earth Engine | earthengine.google.com | Imagery processing |
| Mapbox | mapbox.com | Map tiles |

## License

MIT License

## References

- [AIKOSH-5 Implementation Plan](.trae/documents/aikosh5-geospatial-ai-implementation-plan.md)
- [Copernicus Data Space](https://dataspace.copernicus.eu/)
- [Google Open Buildings](https://sites.research.google/gr/open-buildings)
