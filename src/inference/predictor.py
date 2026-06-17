"""
Predictor module for loading model and making predictions.
"""

import joblib
from typing import Dict, Any, Optional
from pathlib import Path
from ..config import MODEL_CURRENT_DIR, MODEL_FILENAME


class ModelPredictor:
    """Singleton class for model loading and inference."""

    _instance = None
    _model = None
    _model_path = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelPredictor, cls).__new__(cls)
        return cls._instance

    def load_model(self, model_path: Optional[Path] = None) -> Any:
        """Load model from disk."""
        if model_path is None:
            model_path = MODEL_CURRENT_DIR / MODEL_FILENAME

        try:
            self._model = joblib.load(str(model_path))
            self._model_path = str(model_path)
            return self._model
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No model found at {model_path}. Train a model first."
            )

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    def predict(self, features) -> Any:
        """Make prediction using loaded model."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return self._model.predict(features)

    def predict_proba(self, features) -> Any:
        """Get prediction probabilities."""
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        return self._model.predict_proba(features)

    def get_model_path(self) -> Optional[str]:
        """Get currently loaded model path."""
        return self._model_path


def get_predictor() -> ModelPredictor:
    """Get singleton predictor instance."""
    return ModelPredictor()
