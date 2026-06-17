"""
Celery tasks for async model inference.
"""

from celery import shared_task
from typing import Dict, Any
import joblib
import pandas as pd
from ..inference.feature_engineer import fetch_latest_data, prepare_features
from ..config import MODEL_CURRENT_DIR, MODEL_FILENAME, PREDICTION_CLASSES
from ..db.logging import log_prediction

@shared_task
def predict_task(symbol: str) -> Dict[str, Any]:
    """
    Task to make a prediction using the current model.

    Args:
        symbol: Forex pair symbol (e.g., "EURUSD=X")

    Returns:
        Dict with prediction results and metadata
    """
    try:
        # Load current model
        model_path = MODEL_CURRENT_DIR / MODEL_FILENAME
        model = joblib.load(model_path)

        # Fetch and prepare data
        raw_data = fetch_latest_data(symbol)
        features, metadata = prepare_features(raw_data)

        # Make prediction
        prediction = model.predict(features)
        prediction_proba = model.predict_proba(features)

        # Prepare result
        result = {
            "symbol": symbol,
            "prediction": int(prediction[0]),
            "prediction_class": PREDICTION_CLASSES[int(prediction[0])],
            "confidence": float(max(prediction_proba[0])),
            "metadata": metadata,
            "status": "success"
        }

        # Log prediction
        log_prediction(result)

        return result

    except Exception as e:
        error_result = {
            "symbol": symbol,
            "status": "error",
            "error": str(e)
        }
        return error_result