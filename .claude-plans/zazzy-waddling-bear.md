# Forex Trading Bot - REST API + Task Queue + Retraining Pipeline

## Context
Projek ini sudah memiliki:
- ML experiments (Classification & Timeseries) dengan 3 model (RF, GB, XGBoost)
- Simple bot.py untuk inference lokal
- Feature engineering: SMA_10, SMA_50, Daily_Return, Body_Size, High_Low_Chg

Dibutuhkan:
- REST API untuk menerima trade signals, model predictions, status
- Task queue untuk inference async (hindari blocking)
- Retraining pipeline untuk update model berkala (triggered/scheduled)

## Architecture Design

### 1. Tech Stack
- **Framework**: FastAPI (async native, built-in task queues via Celery/RQ)
- **Task Queue**: Celery + Redis (production-grade, reliable)
- **Database**: SQLite/PostgreSQL untuk logging trades, model metrics
- **Model Storage**: Joblib (pkl) in versioned directory structure
- **Data Pipeline**: Same feature engineering as experiments

### 2. File Structure
```
src/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + routes
│   ├── models.py               # Pydantic schemas
│   └── dependencies.py         # Shared dependencies
├── inference/
│   ├── __init__.py
│   ├── predictor.py            # Model loading + prediction logic
│   └── feature_engineer.py     # Feature preparation (extracted)
├── retraining/
│   ├── __init__.py
│   ├── pipeline.py             # Retraining orchestration
│   └── data_loader.py          # yfinance data fetching
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py           # Celery config
│   ├── inference_tasks.py      # Async inference task
│   └── retraining_tasks.py     # Async retraining task
├── models/
│   ├── versioned/              # Store model versions with timestamps
│   └── current/                # Symlink to active model
├── db/
│   ├── __init__.py
│   └── logging.py              # Trade/prediction logging
└── config.py                   # Environment config
```

### 3. API Endpoints (REST)

**Inference:**
- `POST /api/v1/predict` → Submit prediction request (returns task_id)
- `GET /api/v1/predict/{task_id}` → Poll prediction result

**Model Management:**
- `GET /api/v1/model/status` → Current model version, accuracy
- `POST /api/v1/model/retrain` → Trigger retraining (returns task_id)
- `GET /api/v1/model/retrain/{task_id}` → Check retraining progress

**Trading:**
- `GET /api/v1/trades` → List trades/signals
- `POST /api/v1/trades` → Log trade execution

### 4. Task Queue Flow

**Inference Task:**
```
Client → POST /predict → FastAPI validates → Celery task enqueued
         → Returns task_id immediately
         → Worker processes: fetch data → engineer features → predict
         → Result stored in Redis/DB
         → Client polls /predict/{task_id} to retrieve
```

**Retraining Task:**
```
POST /model/retrain (or cron trigger)
→ Celery task enqueued
→ Worker: fetch historical data → train models → evaluate → save versioned
→ If accuracy > threshold: promote to current model
→ Log metrics to DB
```

### 5. Implementation Details

**Feature Engineering** (extract to src/inference/feature_engineer.py):
- Move `prepare_features()` from simple_bot.py
- Handle data alignment for time-series

**Model Versioning**:
- Store models: `models/versioned/model_xgboost_20260617_143022.pkl`
- Current pointer: `models/current/model.pkl` → symlink
- Retrain creates new version, rollback by changing symlink

**Async Inference**:
- FastAPI receives request (symbol, params)
- Spawns Celery task with request ID
- Worker fetches data, prepares features, predicts
- Returns result with confidence/metadata

**Retraining Pipeline**:
- Scheduled: cron job or manual trigger
- Downloads full historical data via yfinance
- Reuses experiment logic from classification_experiments.py
- Trains 3 models in parallel (map/reduce)
- Compares against baseline, promotes best to current

### 6. New Dependencies
```
fastapi
uvicorn
celery
redis
sqlalchemy
psycopg2  # if using PostgreSQL
pydantic
```

### 7. Verification Strategy

1. **Unit Tests**: Feature engineering, model loading
2. **Integration**: 
   - POST /predict → returns task_id
   - GET /predict/{task_id} → returns prediction
   - Inference latency < 5s (worker time)
3. **E2E**: 
   - Full retraining cycle
   - Model promotion on accuracy improvement
   - Trade logging

## Implementation Approach
1. Extract feature_engineer.py from experiments
2. Create FastAPI app with basic routes
3. Setup Celery + Redis locally
4. Implement async inference task
5. Implement retraining pipeline task
6. Add DB logging for trades/predictions
7. Test full cycle: predict → retrain → new model serve

## Next Steps
- Confirm tech choices (Redis? PostgreSQL or SQLite?)
- Confirm retraining trigger (cron schedule or manual only?)
- Decide model serving strategy (always latest, canary, A/B test?)
