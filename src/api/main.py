"""
FastAPI application for forex trading bot.
"""

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
from datetime import datetime
import json
import logging
from pathlib import Path
import socketio

from .models import (
    PredictionRequest, PredictionResponse, PredictionResult,
    RetrainRequest, RetrainResponse, RetrainResult,
    ModelStatus, TradeRequest, TradeResponse, TradeListResponse
)
from .dependencies import (
    get_celery_app, get_predictor_instance, get_db_session
)
from .websocket_handler import (
    handle_predictions_connect, handle_predictions_disconnect,
    handle_trades_connect, handle_trades_disconnect,
    handle_tasks_connect, handle_tasks_disconnect,
    broadcast_prediction, broadcast_trade, broadcast_task_status,
    get_connection_stats
)
from ..tasks.inference_tasks import predict_task
from ..tasks.retraining_tasks import retrain_task
from ..db.logging import log_trade, Prediction, Trade, ModelMetrics
from ..config import MODEL_CURRENT_DIR, MODEL_METADATA_FILENAME, CORS_ORIGINS

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Forex Trading Bot API",
    description="REST API for forex trading bot with ML model inference",
    version="0.1.0"
)

# CORS middleware
cors_origins = CORS_ORIGINS if isinstance(CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO setup
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=cors_origins,
    ping_timeout=60,
    ping_interval=25
)

# Wrap FastAPI with Socket.IO ASGI app
app_with_socket = socketio.ASGIApp(sio, app)


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


# WebSocket Event Handlers - Predictions Namespace
@sio.on('connect', namespace='/predictions')
async def on_connect_predictions(sid, environ):
    """Handle client connection to predictions namespace."""
    await handle_predictions_connect(sid)
    logger.info(f"Predictions client {sid} connected")


@sio.on('disconnect', namespace='/predictions')
async def on_disconnect_predictions(sid):
    """Handle client disconnection from predictions namespace."""
    await handle_predictions_disconnect(sid)
    logger.info(f"Predictions client {sid} disconnected")


# WebSocket Event Handlers - Trades Namespace
@sio.on('connect', namespace='/trades')
async def on_connect_trades(sid, environ):
    """Handle client connection to trades namespace."""
    await handle_trades_connect(sid)
    logger.info(f"Trades client {sid} connected")


@sio.on('disconnect', namespace='/trades')
async def on_disconnect_trades(sid):
    """Handle client disconnection from trades namespace."""
    await handle_trades_disconnect(sid)
    logger.info(f"Trades client {sid} disconnected")


# WebSocket Event Handlers - Tasks Namespace
@sio.on('connect', namespace='/tasks')
async def on_connect_tasks(sid, environ):
    """Handle client connection to tasks namespace."""
    await handle_tasks_connect(sid)
    logger.info(f"Tasks client {sid} connected")


@sio.on('disconnect', namespace='/tasks')
async def on_disconnect_tasks(sid):
    """Handle client disconnection from tasks namespace."""
    await handle_tasks_disconnect(sid)
    logger.info(f"Tasks client {sid} disconnected")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "websocket_connections": get_connection_stats()
    }


# Broadcast endpoints (called by Celery tasks)
@app.post("/api/v1/broadcast/prediction")
async def broadcast_prediction_endpoint(prediction_data: dict):
    """Endpoint for Celery tasks to broadcast prediction results."""
    try:
        await broadcast_prediction(sio, prediction_data)
        return {"status": "ok", "message": "Prediction broadcasted"}
    except Exception as e:
        logger.error(f"Error broadcasting prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/broadcast/trade")
async def broadcast_trade_endpoint(trade_data: dict):
    """Endpoint for Celery tasks to broadcast trade results."""
    try:
        await broadcast_trade(sio, trade_data)
        return {"status": "ok", "message": "Trade broadcasted"}
    except Exception as e:
        logger.error(f"Error broadcasting trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/broadcast/task-status")
async def broadcast_task_status_endpoint(task_id: str, status: str, result: dict = None):
    """Endpoint for Celery tasks to broadcast task status updates."""
    try:
        await broadcast_task_status(sio, task_id, status, result)
        return {"status": "ok", "message": "Task status broadcasted"}
    except Exception as e:
        logger.error(f"Error broadcasting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
frontend_dir = Path(__file__).parent.parent / "frontend"
if (frontend_dir / "static").exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir / "static")), name="static")


# Serve frontend
@app.get("/")
async def frontend_root():
    """Serve main dashboard."""
    frontend_file = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_file.exists():
        return FileResponse(frontend_file, media_type="text/html")
    return {"status": "ok", "message": "API Server Running"}


# Add logging middleware
from src.api.middleware.logging import StructuredLoggingMiddleware
from src.api.routes.health import router as health_router

app.add_middleware(StructuredLoggingMiddleware)
app.include_router(health_router)

# Initialize structured logging
from src.api.config.logging import setup_logging
from ..config import LOG_LEVEL
setup_logging(LOG_LEVEL)
