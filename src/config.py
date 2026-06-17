import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/db/trading.db")

MODELS_DIR = BASE_DIR / "models"
MODEL_VERSIONED_DIR = MODELS_DIR / "versioned"
MODEL_CURRENT_DIR = MODELS_DIR / "current"
MODEL_FILENAME = "model.pkl"
MODEL_METADATA_FILENAME = "metadata.json"

DEFAULT_SYMBOL = "EURUSD=X"
DEFAULT_START_DATE = "2019-01-01"
DEFAULT_LOOKBACK_DAYS = 100

RETRAIN_ACCURACY_THRESHOLD = float(os.getenv("RETRAIN_ACCURACY_THRESHOLD", "0.55"))
RETRAIN_TEST_SIZE = 0.2

FEATURE_COLUMNS = [
    "Open", "High", "Low", "Close",
    "SMA_10", "SMA_50",
    "Daily_Return", "Body_Size", "High_Low_Chg"
]

PREDICTION_CLASSES = {0: "SELL/SHORT", 1: "BUY"}

MODEL_VERSIONED_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
