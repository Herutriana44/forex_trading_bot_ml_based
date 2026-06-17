"""
Celery tasks for model retraining.
"""

from celery import shared_task
from typing import Dict, Any
import joblib
from datetime import datetime
from ..retraining.pipeline import retrain_models
from ..config import MODEL_VERSIONED_DIR, MODEL_CURRENT_DIR, MODEL_FILENAME

@shared_task
def retrain_task(symbol: str = "EURUSD=X", start_date: str = "2019-01-01") -> Dict[str, Any]:
    """
    Task to retrain the trading model.

    Args:
        symbol: Forex pair symbol
        start_date: Start date for historical data

    Returns:
        Dict with retraining results
    """
    try:
        # Run retraining pipeline
        results = retrain_models(symbol=symbol, start_date=start_date)

        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
