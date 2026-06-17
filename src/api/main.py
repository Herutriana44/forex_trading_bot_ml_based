"""
FastAPI application for forex trading bot.
"""

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime
import json

from .models import (
    PredictionRequest, PredictionResponse, PredictionResult,
    RetrainRequest, RetrainResponse, RetrainResult,
    ModelStatus, TradeRequest, TradeResponse, TradeListResponse
)
from .dependencies import (
    get_celery_app, get_predictor_instance, get_db_session
)
from ..tasks.inference_tasks import predict_task
from ..tasks.retraining_tasks import retrain_task
from ..db.logging import log_trade, Prediction, Trade, ModelMetrics
from ..config import MODEL_CURRENT_DIR, MODEL_METADATA_FILENAME

app = FastAPI(
    title="Forex Trading Bot API",
    description="REST API for forex trading bot with ML model inference",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/predict", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    celery_app = Depends(get_celery_app)
):
    """Create async prediction task."""
    task = predict_task.delay(request.symbol)
    return {
        "task_id": task.id,
        "status": "queued"
    }


@app.get("/api/v1/predict/{task_id}", response_model=PredictionResult)
async def get_prediction_result(
    task_id: str,
    celery_app = Depends(get_celery_app)
):
    """Get prediction result by task ID."""
    task = celery_app.AsyncResult(task_id)

    if task.state == "PENDING":
        return {
            "status": "pending",
            "symbol": "",
            "prediction": 0,
            "prediction_class": "",
            "confidence": 0.0,
            "current_price": 0.0,
            "timestamp": datetime.now().isoformat()
        }
    elif task.state == "SUCCESS":
        result = task.result
        if result["status"] == "success":
            return {
                "symbol": result["symbol"],
                "prediction": result["prediction"],
                "prediction_class": result["prediction_class"],
                "confidence": result["confidence"],
                "current_price": result["metadata"]["current_price"],
                "timestamp": result["metadata"]["timestamp"],
                "status": "success"
            }
        else:
            return {
                "status": "error",
                "error": result["error"],
                "symbol": result["symbol"],
                "prediction": 0,
                "prediction_class": "",
                "confidence": 0.0,
                "current_price": 0.0,
                "timestamp": datetime.now().isoformat()
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task failed or unknown state: {task.state}"
        )


@app.get("/api/v1/model/status", response_model=ModelStatus)
async def get_model_status():
    """Get current model status and metrics."""
    try:
        # Read metadata file
        metadata_path = MODEL_CURRENT_DIR / MODEL_METADATA_FILENAME
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        return {
            "model_name": metadata["model_name"],
            "model_version": metadata["version"],
            "accuracy": metadata["metrics"]["accuracy"],
            "precision": metadata["metrics"]["precision"],
            "recall": metadata["metrics"]["recall"],
            "timestamp": metadata["timestamp"],
            "current": True
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current model found. Train a model first."
        )


@app.post("/api/v1/model/retrain", response_model=RetrainResponse)
async def create_retrain_task(
    request: RetrainRequest,
    celery_app = Depends(get_celery_app)
):
    """Create async retraining task."""
    task = retrain_task.delay(request.symbol, request.start_date)
    return {
        "task_id": task.id,
        "status": "queued"
    }


@app.get("/api/v1/model/retrain/{task_id}", response_model=RetrainResult)
async def get_retrain_result(
    task_id: str,
    celery_app = Depends(get_celery_app)
):
    """Get retraining result by task ID."""
    task = celery_app.AsyncResult(task_id)

    if task.state == "PENDING":
        return {
            "status": "pending"
        }
    elif task.state == "SUCCESS":
        result = task.result
        if result["status"] == "success":
            return {
                "status": "success",
                "results": result["results"]
            }
        else:
            return {
                "status": "error",
                "error": result["error"]
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task failed or unknown state: {task.state}"
        )


@app.post("/api/v1/trades", response_model=TradeResponse)
async def create_trade(
    request: TradeRequest,
    db = Depends(get_db_session)
):
    """Log a trade execution."""
    trade_data = request.dict()
    log_trade(trade_data)

    # Get the created trade from DB
    db_trade = db.query(Trade).filter(Trade.symbol == request.symbol).order_by(Trade.id.desc()).first()

    return {
        "id": db_trade.id,
        "symbol": db_trade.symbol,
        "action": db_trade.action,
        "price": db_trade.price,
        "quantity": db_trade.quantity,
        "timestamp": db_trade.timestamp.isoformat(),
        "notes": db_trade.notes
    }


@app.get("/api/v1/trades", response_model=TradeListResponse)
async def list_trades(
    limit: int = 100,
    db = Depends(get_db_session)
):
    """List recent trades."""
    trades = db.query(Trade).order_by(Trade.id.desc()).limit(limit).all()

    return {
        "trades": [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "action": trade.action,
                "price": trade.price,
                "quantity": trade.quantity,
                "timestamp": trade.timestamp.isoformat(),
                "notes": trade.notes
            }
            for trade in trades
        ],
        "count": len(trades)
    }