"""
Retraining pipeline for forex trading model.
"""

import joblib
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
import shutil

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score

from .data_loader import fetch_historical_data, validate_data
from ..inference.feature_engineer import prepare_training_data
from ..config import (
    MODEL_VERSIONED_DIR,
    MODEL_CURRENT_DIR,
    MODEL_FILENAME,
    MODEL_METADATA_FILENAME,
    FEATURE_COLUMNS,
    RETRAIN_TEST_SIZE,
    RETRAIN_ACCURACY_THRESHOLD,
    DEFAULT_SYMBOL,
    DEFAULT_START_DATE
)
from ..db.logging import log_model_metrics


def train_models(X_train, y_train) -> Dict[str, Any]:
    """Train multiple models and return trained instances."""
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=100, max_depth=5, random_state=42
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100, learning_rate=0.05, max_depth=3,
            random_state=42, eval_metric='logloss'
        )
    }

    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)

    return models


def evaluate_model(model, X_test, y_test) -> Dict[str, float]:
    """Evaluate model on test set."""
    y_pred = model.predict(X_test)
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0))
    }


def select_best_model(models, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Select best model based on accuracy."""
    best = max(results, key=lambda x: x["metrics"]["accuracy"])
    return {
        "name": best["model_name"],
        "model": models[best["model_name"]],
        "metrics": best["metrics"]
    }


def save_model_version(model, metrics: Dict[str, float], model_name: str) -> str:
    """Save model to versioned directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_name = f"{model_name.replace(' ', '_').lower()}_{timestamp}"
    version_dir = MODEL_VERSIONED_DIR / version_name
    version_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    model_path = version_dir / "model.pkl"
    joblib.dump(model, str(model_path))

    # Save metadata
    metadata = {
        "model_name": model_name,
        "version": version_name,
        "timestamp": timestamp,
        "metrics": metrics
    }
    metadata_path = version_dir / MODEL_METADATA_FILENAME
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return str(version_dir)


def promote_model(version_dir: Path) -> None:
    """Promote model to current directory by recreating symlink/files."""
    model_src = version_dir / "model.pkl"
    metadata_src = version_dir / MODEL_METADATA_FILENAME

    model_dst = MODEL_CURRENT_DIR / MODEL_FILENAME
    metadata_dst = MODEL_CURRENT_DIR / MODEL_METADATA_FILENAME

    # Copy files (more reliable than symlinks across platforms)
    shutil.copy2(model_src, model_dst)
    if metadata_src.exists():
        shutil.copy2(metadata_src, metadata_dst)


def retrain_models(symbol: str = DEFAULT_SYMBOL,
                   start_date: str = DEFAULT_START_DATE) -> Dict[str, Any]:
    """
    Main orchestration function to retrain all models,
    select the best, and promote it to current.

    Returns:
        Dict with retraining results and metrics
    """
    # Prepare data
    df = prepare_training_data(symbol, start_date)
    validate_data(df)

    X = df[FEATURE_COLUMNS]
    y = df['Target']

    # Split data (time-series, no shuffle)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=RETRAIN_TEST_SIZE, shuffle=False
    )

    # Train models
    models = train_models(X_train, y_train)

    # Evaluate and collect results
    results = []
    for name, model in models.items():
        metrics = evaluate_model(model, X_test, y_test)
        results.append({
            "model_name": name,
            "metrics": metrics
        })

    # Select best
    best = select_best_model(models, results)
    print(f"\nBest model: {best['name']} (acc={best['metrics']['accuracy']:.4f})")

    # Save versioned model
    version_dir = save_model_version(best["model"], best["metrics"], best["name"])

    promoted = False
    if best["metrics"]["accuracy"] >= RETRAIN_ACCURACY_THRESHOLD:
        promote_model(Path(version_dir))
        promoted = True
        print(f"Model promoted to current: {version_dir}")
    else:
        print(f"Accuracy {best['metrics']['accuracy']:.4f} below threshold {RETRAIN_ACCURACY_THRESHOLD}. Not promoted.")

    # Log metrics to DB
    log_model_metrics({
        "model_name": best["name"],
        "model_version": Path(version_dir).name,
        "accuracy": best["metrics"]["accuracy"],
        "precision": best["metrics"]["precision"],
        "recall": best["metrics"]["recall"],
        "metadata": {"promoted": promoted}
    })

    return {
        "all_results": results,
        "best_model": best,
        "version_dir": version_dir,
        "promoted": promoted
    }