# Implementation Plan: Production-Grade Web Version for Forex Trading Bot

## Context

**Why this matters**: The current web implementation has fundamental architectural issues (Flask proxy layer, SQLAlchemy schema collision, unsafe werkzeug mode, missing tests) and isn't deployment-ready. To make this bot production-grade and deployable on cloud platforms, we need:

1. Fix immediate blockers (metadata column, werkzeug security)
2. Replace Flask proxy with proper WebSocket-enabled backend
3. Keep frontend simple (HTML+JS+Bootstrap) but production-ready
4. Containerize everything for cloud deployment (Docker)
5. Add proper testing, error handling, monitoring
6. Support real-time updates via WebSocket

---

## Current State Analysis

### Critical Issues
| Issue | Impact | Root Cause |
|-------|--------|-----------|
| SQLAlchemy `metadata` column name collision | DB schema breaks | Reserved keyword used as column name (src/db/logging.py:28,53) |
| Werkzeug unsafe mode | Security vulnerability | Line 203 in src/web/app.py |
| No tests | High regression risk | Zero test infrastructure |
| Hardcoded SQLite path | Not portable | src/config.py:9 uses BASE_DIR for local-only setup |
| No WebSocket support | Can't do true real-time | Current SSE polling is inefficient |
| Flask proxy anti-pattern | Unnecessary complexity | Flask front-ends FastAPI redundantly |
| No CI/CD pipeline | Manual deployments | No automated testing/deployment |
| No error handling | Poor observability | Errors silently fail, hard to debug |

### Architecture Issues
- **Current**: Browser → Flask (SSE polling) → FastAPI (HTTP requests) → Celery/Redis → SQLite
- **Problem**: Flask adds unnecessary latency and complexity. Direct WebSocket from browser to FastAPI would be simpler and faster.
- **Solution**: Remove Flask entirely. Build a simple vanilla JS frontend that talks directly to FastAPI via WebSocket + REST.

---

## Implementation Approach

### High-Level Strategy
1. **Phase 1**: Fix immediate blockers (metadata column, security issues, dependencies)
2. **Phase 2**: Add WebSocket support to FastAPI backend
3. **Phase 3**: Build static frontend (HTML+JS+Bootstrap) with WebSocket client
4. **Phase 4**: Add Docker containerization + compose file
5. **Phase 5**: Add testing infrastructure (pytest, unit + integration tests)
6. **Phase 6**: Add monitoring/logging + health checks

### Technology Choices (Justification)
- **Backend**: FastAPI (async, WebSocket-native, auto-docs)
- **Real-time**: WebSocket via `python-socketio` (more reliable than SSE, bidirectional)
- **Frontend**: Vanilla HTML+JS+Bootstrap (minimal deps, fast iteration, doesn't need npm build)
- **Database**: PostgreSQL (production-grade, replaces SQLite), with Alembic migrations
- **Containerization**: Docker + docker-compose (local dev and cloud deployment)
- **Testing**: pytest + pytest-asyncio (FastAPI standard)
- **Monitoring**: Structured logging (Python logging + JSON format)

---

## Proposed Architecture

### System Diagram
```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Single Page)                │
│  - HTML + Vanilla JS + Bootstrap 5 + Socket.IO Client  │
│  - Dashboard, charts, trade history, model status      │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │ REST (GET/POST)           │ WebSocket (bi-directional)
         │ - Model status            │ - Real-time predictions
         │ - Trade history           │ - Trade execution events
         │ - Trigger actions         │ - Task status updates
         │                           │
         ▼─────────────┬─────────────▼
    ┌──────────────────────────────────────────┐
    │  FastAPI Backend (src/api/main.py)       │
    │  - REST endpoints for state queries      │
    │  - WebSocket namespace for real-time     │
    │  - CORS properly configured              │
    │  - Error handling + structured logging   │
    └──────────┬───────────────────────────────┘
               │
    ┌──────────┴──────────────────┬─────────────────┐
    │                             │                 │
    ▼                             ▼                 ▼
┌─────────────┐         ┌──────────────────┐  ┌──────────────┐
│   Celery    │         │  PostgreSQL      │  │  Redis       │
│  Task Queue │         │   Database       │  │  Cache/Broker│
│ (inference  │         │  (predictions,   │  │              │
│ retraining) │         │   trades, metrics)  │              │
└─────────────┘         └──────────────────┘  └──────────────┘

Docker Compose:
├─ fastapi-backend (port 8000)
├─ celery-worker
├─ postgres (port 5432)
├─ redis (port 6379)
└─ (optional) nginx-reverse-proxy (port 80/443)
```

### Backend Structure (FastAPI)
```
src/api/
├─ main.py               # FastAPI app + routes + middleware
├─ models.py             # Pydantic schemas
├─ websocket_handler.py  # NEW: WebSocket namespace handlers
├─ dependencies.py       # Dependency injection (db, celery)
├─ routes/
│  ├─ predictions.py     # REST: GET model/predictions
│  ├─ trades.py          # REST: GET/POST trades
│  ├─ model.py           # REST: GET model/status, POST model/retrain
│  └─ health.py          # NEW: Health checks for monitoring
└─ middleware/
   ├─ logging.py         # Structured logging
   ├─ error_handlers.py  # Global exception handling
   └─ cors.py            # CORS configuration

src/db/
├─ models.py             # SQLAlchemy models (fixed schema)
├─ schemas.py            # Alembic migrations folder
├─ session.py            # Database session management

src/frontend/
├─ index.html            # Single HTML file (or simple templates)
├─ static/
│  ├─ css/dashboard.css
│  ├─ js/socket-client.js    # WebSocket + Socket.IO client
│  ├─ js/api-client.js       # REST API calls
│  └─ js/ui-manager.js       # DOM updates
```

### Frontend (Simple, Production-Grade)
- **Single HTML file** (`src/frontend/index.html`)
- **Dependencies**: Bootstrap 5 CDN, Socket.IO client CDN, Chart.js CDN
- **Sections**:
  - Dashboard (live metrics, latest predictions)
  - Model status (accuracy, precision, recall, last training)
  - Recent predictions (table with timestamps)
  - Trade history (executed trades)
  - Control panel (trigger prediction, trigger retraining)
  - Real-time event log (WebSocket events flowing in)

---

## Phase-by-Phase Implementation

### Phase 1: Fix Critical Issues (Files: src/db/, src/api/, src/config.py)

**Database Schema Fix**:
- Rename `extra_data = Column("metadata", Text)` → `extra_data = Column("extra_data", Text)` (or `metadata_json`)
- Affects: `src/db/logging.py` lines 28, 53

**Security Fix**:
- Remove `allow_unsafe_werkzeug=True` from src/web/app.py
- Actually: Remove Flask entirely (will be done in Phase 3)

**Configuration**:
- Update `src/config.py` to support:
  - PostgreSQL URL (DATABASE_URL env var with fallback to SQLite for local dev)
  - CORS_ORIGINS (whitelist specific domains, not "*")
  - Environment-aware logging level

**Dependencies**:
- Update `requirements.txt` with current versions
- Add: `python-socketio`, `alembic`, `psycopg2-binary` (for PostgreSQL)

---

### Phase 2: Add WebSocket Support to FastAPI

**New File**: `src/api/websocket_handler.py`
- Socket.IO namespace for `/predictions` (broadcasts new predictions)
- Socket.IO namespace for `/trades` (broadcasts trade executions)
- Socket.IO namespace for `/tasks` (broadcasts Celery task status updates)
- Connection/disconnection lifecycle management
- Error handling for WebSocket failures

**Update**: `src/api/main.py`
- Instantiate Socket.IO instance
- Attach WebSocket handlers
- Update CORS to allow Socket.IO handshake
- Attach Socket.IO to FastAPI app

**Integration with Celery**:
- When `predict_task` completes: broadcast result via WebSocket
- When `retrain_task` completes: broadcast result via WebSocket
- Socket.IO connection tracking: only send events to connected clients

---

### Phase 3: Build Frontend + Remove Flask

**New Static Frontend**: `src/frontend/index.html`
- Bootstrap 5 grid layout (responsive)
- Real-time sections (bound to WebSocket events)
- Control buttons (predict, retrain, manual trade logging)
- Charts: Recent accuracy trends, trade P&L, prediction confidence over time

**Frontend JavaScript**:
- `socket-client.js`: Connect to WebSocket, emit/listen events
- `api-client.js`: REST calls (model status, trade history, etc.)
- `ui-manager.js`: Update DOM when data arrives

**Remove Flask**:
- Delete `src/web/app.py` and `src/web/` directory
- Static files served by FastAPI (via `StaticFiles` middleware)

**Serve Static Files**:
- In FastAPI `main.py`: mount static directory
- Serve `index.html` at `/` route

---

### Phase 4: Docker Containerization

**New Files**:
- `Dockerfile` (FastAPI app)
- `Dockerfile.celery` (Celery worker)
- `docker-compose.yml` (postgres, redis, fastapi, celery, nginx optional)
- `.dockerignore`
- `docker/entrypoint.sh` (health checks, migrations)

**Docker Compose Services**:
1. `postgres`: PostgreSQL 15, volume for persistence
2. `redis`: Redis 7, volume for persistence
3. `fastapi-backend`: Port 8000, depends on postgres+redis
4. `celery-worker`: Port unmapped, depends on fastapi+redis
5. `celery-beat`: (optional) Task scheduling

**Local Development**:
- Run `docker-compose up` → entire stack ready
- Hot reload for FastAPI (mount src/ volume)
- Environment variables: `.env` file

---

### Phase 5: Testing Infrastructure

**New Files**:
- `tests/conftest.py` (pytest fixtures: test DB, Celery, FastAPI client)
- `tests/test_api_routes.py` (unit tests for all endpoints)
- `tests/test_websocket.py` (WebSocket connection/broadcast tests)
- `tests/test_ml.py` (predictor, feature engineering tests)
- `tests/test_db.py` (database operations)
- `pytest.ini` (configuration)

**Test Strategy**:
- Use in-memory SQLite for tests (or TestContainer PostgreSQL for integration tests)
- Mock Celery (Celery eager mode for synchronous testing)
- Test coverage target: 70%+ for API routes and critical logic

**CI/CD**:
- GitHub Actions: Run pytest on every push
- Lint check: ruff, mypy
- Docker build test

---

### Phase 6: Monitoring + Logging

**New Files**:
- `src/api/middleware/logging.py` (structured JSON logging)
- `src/api/routes/health.py` (health checks, metrics)
- `src/api/config/logging.py` (logging configuration)

**Health Checks**:
- `/health` (FastAPI ready?)
- `/health/db` (Database reachable?)
- `/health/redis` (Redis reachable?)
- `/health/celery` (Celery worker alive?)

**Structured Logging**:
- All logs as JSON (timestamp, level, message, context)
- Logs to stdout (Docker-friendly, can be ingested by ELK, CloudWatch, etc.)
- Correlation IDs for request tracing

---

## Critical Files to Modify / Create

### Must Fix (Phase 1)
1. `src/db/logging.py` → Rename `metadata` column
2. `src/config.py` → Add PostgreSQL support, environment-aware config
3. `requirements.txt` → Update/add dependencies

### Must Create (Phase 2-3)
4. `src/api/websocket_handler.py` → NEW
5. `src/frontend/index.html` → NEW
6. `src/frontend/static/js/*.js` → NEW (3-4 files)
7. `src/api/routes/health.py` → NEW

### Must Create (Phase 4)
8. `Dockerfile` → NEW
9. `docker-compose.yml` → NEW
10. `docker/entrypoint.sh` → NEW

### Should Create (Phase 5-6)
11. `tests/` directory with test files → NEW
12. `pytest.ini` → NEW
13. `src/api/middleware/` directory → NEW

### Can Delete (Phase 3)
- `src/web/` (entire Flask directory)

---

## Verification Plan

### Post-Implementation Testing

**1. Local Development (docker-compose)**
```bash
docker-compose up
# Check: All services healthy
# Check: http://localhost:8000 loads frontend
# Check: WebSocket connects in browser dev tools
# Check: Trigger prediction → see live update in dashboard
```

**2. Manual Integration Test**
- Open dashboard in browser
- Click "Predict" button
- Verify:
  - REST call to FastAPI succeeds
  - Celery task queued
  - WebSocket message arrives with result
  - Dashboard updates in real-time

**3. Run Test Suite**
```bash
pytest tests/ -v --cov=src
# Target: >70% coverage
```

**4. Load Test (optional)**
- Multiple browser tabs → multiple WebSocket connections
- Trigger rapid predictions
- Monitor: Celery queue, Redis, database connections

**5. Deployment Check**
- Deploy docker-compose to staging
- Verify health checks pass
- Verify logs are structured JSON
- Verify monitoring endpoints work

---

## Rollout Plan

### If starting from scratch (recommended):
1. Run Phase 1 fixes
2. Run Phase 2 (WebSocket)
3. Run Phase 3 (Frontend)
4. Test locally with docker-compose
5. Run Phase 4 (Containerization) as part of Phase 3
6. Add Phase 5 (Tests)
7. Add Phase 6 (Monitoring)

### If iterating on existing web app:
1. Run Phase 1 fixes first (unblocks everything)
2. Create new FastAPI structure in parallel
3. Migrate endpoints one-by-one
4. Once WebSocket working, swap frontend
5. Delete Flask app
6. Containerize + test

---

## Known Trade-offs

| Trade-off | Choice | Why |
|-----------|--------|-----|
| Frontend Framework | Vanilla JS (not React) | User preference + simple dashboard doesn't need SPA complexity |
| Database | PostgreSQL (not SQLite) | Production-grade, scales better, required for cloud deployment |
| Real-time | WebSocket (not polling) | User requirement, more efficient, better UX |
| Architecture | Monolith (not microservices) | Simpler to start, can split later if needed |
| Testing | Unit + integration (not E2E) | E2E with Selenium/Playwright adds overhead; browser testing is manual for now |

