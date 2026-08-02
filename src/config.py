import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENVIRONMENT == "production" else "DEBUG")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR}/db/trading.db"
)

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
if CORS_ORIGINS == ["*"]:
    CORS_ORIGINS = ["*"]

# Models
MODELS_DIR = BASE_DIR / "models"
MODEL_VERSIONED_DIR = MODELS_DIR / "versioned"
MODEL_CURRENT_DIR = MODELS_DIR / "current"
MODEL_FILENAME = "model.pkl"
MODEL_METADATA_FILENAME = "metadata.json"

# Trading
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

# Supported Forex Symbols — grouped by major/minor/cross/commodity/crypto
FOREX_SYMBOLS = [
    # Major Pairs
    {"symbol": "EURUSD=X", "label": "EUR/USD", "group": "Major"},
    {"symbol": "GBPUSD=X", "label": "GBP/USD", "group": "Major"},
    {"symbol": "USDJPY=X", "label": "USD/JPY", "group": "Major"},
    {"symbol": "USDCHF=X", "label": "USD/CHF", "group": "Major"},
    {"symbol": "AUDUSD=X", "label": "AUD/USD", "group": "Major"},
    {"symbol": "USDCAD=X", "label": "USD/CAD", "group": "Major"},
    {"symbol": "NZDUSD=X", "label": "NZD/USD", "group": "Major"},
    # Minor / Cross Pairs
    {"symbol": "EURGBP=X", "label": "EUR/GBP", "group": "Minor"},
    {"symbol": "EURJPY=X", "label": "EUR/JPY", "group": "Minor"},
    {"symbol": "GBPJPY=X", "label": "GBP/JPY", "group": "Minor"},
    {"symbol": "AUDJPY=X", "label": "AUD/JPY", "group": "Minor"},
    {"symbol": "CHFJPY=X", "label": "CHF/JPY", "group": "Minor"},
    {"symbol": "EURCHF=X", "label": "EUR/CHF", "group": "Minor"},
    {"symbol": "GBPAUD=X", "label": "GBP/AUD", "group": "Minor"},
    {"symbol": "GBPCAD=X", "label": "GBP/CAD", "group": "Minor"},
    {"symbol": "AUDNZD=X", "label": "AUD/NZD", "group": "Minor"},
    {"symbol": "AUDCAD=X", "label": "AUD/CAD", "group": "Minor"},
    {"symbol": "CADJPY=X", "label": "CAD/JPY", "group": "Minor"},
    {"symbol": "NZDJPY=X", "label": "NZD/JPY", "group": "Minor"},
    # Exotic Pairs
    {"symbol": "USDTRY=X", "label": "USD/TRY", "group": "Exotic"},
    {"symbol": "USDZAR=X", "label": "USD/ZAR", "group": "Exotic"},
    {"symbol": "USDMXN=X", "label": "USD/MXN", "group": "Exotic"},
    {"symbol": "USDSEK=X", "label": "USD/SEK", "group": "Exotic"},
    {"symbol": "USDNOK=X", "label": "USD/NOK", "group": "Exotic"},
    {"symbol": "USDDKK=X", "label": "USD/DKK", "group": "Exotic"},
    {"symbol": "USDSGD=X", "label": "USD/SGD", "group": "Exotic"},
    {"symbol": "USDHKD=X", "label": "USD/HKD", "group": "Exotic"},
    # Commodity / Metals
    {"symbol": "XAUUSD=X", "label": "XAU/USD (Gold)", "group": "Commodity"},
    {"symbol": "XAGUSD=X", "label": "XAG/USD (Silver)", "group": "Commodity"},
    {"symbol": "XPTUSD=X", "label": "XPT/USD (Platinum)", "group": "Commodity"},
]

# Symbol lookup dict for fast access
FOREX_SYMBOL_MAP = {s["symbol"]: s for s in FOREX_SYMBOLS}

# Price streaming interval (seconds)
PRICE_STREAM_INTERVAL = int(os.getenv("PRICE_STREAM_INTERVAL", "10"))

MODEL_VERSIONED_DIR.mkdir(parents=True, exist_ok=True)
MODEL_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
