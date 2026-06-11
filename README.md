# 🚢 Ship Tracker (Sea Tracker)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=000)](https://react.dev/)
[![PostgreSQL + PostGIS](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Git LFS](https://img.shields.io/badge/Git%20LFS-enabled-0A7?logo=git-lfs&logoColor=white)](https://git-lfs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

Enterprise-style, real-time maritime intelligence platform for tracking vessels, incidents, alerts, and ocean conditions.

It combines multiple AIS feeds, geospatial analytics, operational alerting, and a modern map-centric UI into one monorepo.

## Highlights

- **Real-time vessel intelligence** via AIS feed aggregation (AISStream, Kystverket, NOAA, GFW).
- **Operational dashboard** for incidents, alerts, and analytics.
- **WebSocket live streams** for vessels, alerts, and incident updates.
- **Geospatial services** for EEZ boundaries, shipping lanes, submarine cables, and ports.
- **Detection engines** for collision risk, anomalies, and zone-based rules.
- **Production-ready backend design** with async FastAPI, Redis pub/sub, Celery workers, and PostGIS.

## Architecture at a Glance

Canonical diagram source: `docs/architecture.mmd`  
Exported image artifact: `docs/architecture.svg`

![Ship Tracker architecture](docs/architecture.svg)

```mermaid
flowchart LR
    subgraph external_sources["External Sources"]
        A[AISStream]
        B[Kystverket]
        C[NOAA AIS]
        D[Global Fishing Watch]
        E[Open-Meteo / NOAA Tides]
    end

    subgraph backend["Backend (FastAPI)"]
        AGG[AIS Aggregator]
        VT[Vessel Tracker]
        AD[Alert / Incident / Collision / Zone Services]
        API[REST + WebSocket APIs]
        CEL[Celery Worker + Beat]
    end

    subgraph data_layer["Data Layer"]
        PG[(PostgreSQL + PostGIS)]
        R[(Redis)]
        GEO[GeoJSON Layers]
    end

    subgraph frontend["Frontend (React + Vite)"]
        UI[Map + Ops + Analytics]
    end

    A --> AGG
    B --> AGG
    C --> AGG
    D --> AGG
    E --> AD
    AGG --> VT
    VT --> R
    VT --> PG
    AD --> R
    AD --> PG
    CEL --> AD
    GEO --> API
    PG --> API
    R --> API
    API --> UI
```

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 18, Vite, Leaflet, Recharts, Zustand, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic Settings |
| Async/Data | SQLAlchemy Async, asyncpg, GeoAlchemy2, Shapely, PyProj |
| Database | PostgreSQL + PostGIS |
| Realtime/Queue | Redis, Celery |
| Testing | Pytest + Coverage |

## Repository Layout

```text
Ship Tracker/
├── backend/
│   ├── main.py                  # FastAPI app + startup lifecycle
│   ├── config.py                # Environment-backed settings
│   ├── database.py              # DB init/session management
│   ├── routers/                 # REST APIs
│   ├── websocket/               # WS endpoints + broadcasters
│   ├── services/                # Core domain services and detectors
│   ├── tasks/                   # Celery worker/beat tasks
│   ├── models/                  # SQLAlchemy models
│   ├── schemas/                 # API schemas
│   ├── utils/                   # Utility modules
│   ├── tests/                   # Backend test suite
│   └── static/                  # GeoJSON/static maritime datasets
├── frontend/
│   ├── src/components/
│   ├── src/hooks/
│   ├── src/pages/
│   ├── src/store/
│   └── src/utils/
├── setup.bat                    # First-time setup (Windows)
├── start.bat                    # Multi-window startup (Windows)
├── start_inline.bat             # Single-terminal startup
└── stop.bat                     # Graceful stop helper
```

## Prerequisites

- **Python** 3.11+
- **Node.js** 18+
- **PostgreSQL** 15+ with **PostGIS**
- **Redis** (Memurai works on Windows)
- Optional API keys for premium/extended data feeds

## Quick Start (Windows)

1. **Install dependencies and bootstrap the workspace**

    - Run `setup.bat`

2. **Create and prepare the database**

    In `psql`:

    - `CREATE DATABASE seatracker;`
    - `\c seatracker`
    - `CREATE EXTENSION postgis;`

3. **Configure environment**

    - Copy `backend/.env.example` to `backend/.env`
    - Fill in required values (at minimum database + redis + AIS key if used)

4. **Start services**

    - `start.bat` (spawns backend, frontend, celery worker, celery beat)
    - or `start_inline.bat` for single-terminal mode

5. **Open the app**

    - Frontend: `http://localhost:5173`
    - API: `http://localhost:8000`
    - OpenAPI Docs: `http://localhost:8000/docs`

## Configuration

Primary runtime configuration is loaded from `backend/.env`.

### Core Variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async SQLAlchemy connection string |
| `DATABASE_SYNC_URL` | Sync DB URL for tools/scripts |
| `REDIS_URL` | Redis broker/pubsub endpoint |
| `AISSTREAM_API_KEY` | AISStream authentication key |
| `GFW_API_KEY` | Global Fishing Watch API key (optional) |
| `CMEMS_USERNAME` / `CMEMS_PASSWORD` | Ocean model credentials (optional) |
| `SMTP_*` | Email alert notifications (optional) |

> Note: Additional tuning settings exist in `backend/config.py` for polling intervals, stale timeouts, and alert thresholds.

## API Surface

### REST (examples)

- `GET /api/health`
- `GET /api/vessels`
- `GET /api/vessels/{mmsi}`
- `GET /api/history/{mmsi}`
- `GET /api/alerts`
- `GET /api/incidents`
- `GET /api/ports`
- `GET /api/zones`
- `GET /api/analytics/dashboard`

### WebSocket

- `/ws/vessels`
- `/ws/alerts`
- `/ws/incidents`

## Testing & Quality

Backend tests and coverage are configured via `pytest.ini`.

- Test path: `backend/tests`
- Python path: `backend`
- Coverage output: terminal + `coverage.xml`

Run tests from repository root:

- `pytest`

## Large GeoJSON Assets (Git LFS)

Large geospatial files are managed with **Git LFS** to stay within GitHub file size limits while preserving versioning.

Tracked via LFS:

- `backend/static/eez_boundaries.geojson`

If you clone this repository for development, ensure Git LFS is installed before pulling large assets.

## Operations Notes

- `start.bat` launches four processes: FastAPI, Celery worker, Celery beat, and Vite.
- `stop.bat` terminates tracked service windows/processes.
- Celery uses `--pool=solo` for Windows compatibility.

## Contributing

See `CONTRIBUTING.md` for branch workflow, coding expectations, and PR checklist.

## Release Checklist

See `docs/release-checklist.md` for pre-release quality and operations gates.

## License

MIT
