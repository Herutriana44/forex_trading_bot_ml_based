"""
FastAPI application for forex trading bot.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import socketio
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..config import (
    CORS_ORIGINS,
    FOREX_SYMBOLS,
    MODEL_CURRENT_DIR,
    MODEL_METADATA_FILENAME,
    PRICE_STREAM_INTERVAL,
)
from ..inference.feature_engineer import fetch_current_price
from ..tasks.inference_tasks import predict_task
from ..tasks.retraining_tasks import retrain_task
from ..db.logging import log_trade, Prediction, Trade, ModelMetrics
from .dependencies import get_celery_app, get_db_session, get_predictor_instance
from .models import (
    ModelStatus,
    PredictionRequest,
    PredictionResponse,
    PredictionResult,
    RetrainRequest,
    RetrainResponse,
    RetrainResult,
    TradeListResponse,
    TradeRequest,
    TradeResponse,
)
from .websocket_handler import (
    broadcast_prediction,
    broadcast_task_status,
    broadcast_ticker,
    broadcast_trade,
    get_connection_stats,
    handle_predictions_connect,
    handle_predictions_disconnect,
    handle_tasks_connect,
    handle_tasks_disconnect,
    handle_ticker_connect,
    handle_ticker_disconnect,
    handle_trades_connect,
    handle_trades_disconnect,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Forex Trading Bot API",
    description="REST API for forex trading bot with ML model inference",
    version="0.2.0",
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
    async_mode="asgi",
    cors_allowed_origins=cors_origins,
    ping_timeout=60,
    ping_interval=25,
)

# Wrap FastAPI with Socket.IO ASGI app
app_with_socket = socketio.ASGIApp(sio, app)

# ─────────────────────────────────────────────
# Background price-streaming task
# ─────────────────────────────────────────────

_streaming_task: Optional[asyncio.Task] = None


async def _price_stream_loop():
    """
    Background coroutine: fetches current prices for all supported symbols
    and broadcasts them via Socket.IO to the /ticker namespace every
    PRICE_STREAM_INTERVAL seconds.
    """
    symbols = [s["symbol"] for s in FOREX_SYMBOLS]
    while True:
        try:
            for sym in symbols:
                price_data = fetch_current_price(sym)
                if price_data:
                    await broadcast_ticker(sio, price_data)
                    await asyncio.sleep(0.05)  # small delay between symbols
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"Price stream error: {exc}")
        await asyncio.sleep(PRICE_STREAM_INTERVAL)


@app.on_event("startup")
async def _startup():
    global _streaming_task
    _streaming_task = asyncio.create_task(_price_stream_loop())
    logger.info("Price streaming task started")


@app.on_event("shutdown")
async def _shutdown():
    if _streaming_task:
        _streaming_task.cancel()
        try:
            await _streaming_task
        except asyncio.CancelledError:
            pass
    logger.info("Price streaming task stopped")


# ─────────────────────────────────────────────
# REST endpoints
# ─────────────────────────────────────────────


@app.get("/api/v1/symbols")
async def list_symbols():
    """Return the full list of supported forex symbols."""
    return {"symbols": FOREX_SYMBOLS}


@app.post("/api/v1/predict", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    celery_app=Depends(get_celery_app),
):
    """Create async prediction task."""
    task = predict_task.delay(request.symbol)
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/v1/predict/{task_id}", response_model=PredictionResult)
async def get_prediction_result(
    task_id: str,
    celery_app=Depends(get_celery_app),
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
            "timestamp": datetime.utcnow().isoformat(),
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
                "status": "success",
            }
        else:
            return {
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "symbol": result.get("symbol", ""),
                "prediction": 0,
                "prediction_class": "",
                "confidence": 0.0,
                "current_price": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task failed or unknown state: {task.state}",
        )


@app.get("/api/v1/model/status", response_model=ModelStatus)
async def get_model_status():
    """Get current model status and metrics."""
    try:
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
            "current": True,
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current model found. Train a model first.",
        )


@app.post("/api/v1/model/retrain", response_model=RetrainResponse)
async def create_retrain_task(
    request: RetrainRequest,
    celery_app=Depends(get_celery_app),
):
    """Create async retraining task."""
    task = retrain_task.delay(request.symbol, request.start_date)
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/v1/model/retrain/{task_id}", response_model=RetrainResult)
async def get_retrain_result(
    task_id: str,
    celery_app=Depends(get_celery_app),
):
    """Get retraining result by task ID."""
    task = celery_app.AsyncResult(task_id)

    if task.state == "PENDING":
        return {"status": "pending"}
    elif task.state == "SUCCESS":
        result = task.result
        if result["status"] == "success":
            return {"status": "success", "results": result["results"]}
        else:
            return {"status": "error", "error": result["error"]}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task failed or unknown state: {task.state}",
        )


@app.post("/api/v1/trades", response_model=TradeResponse)
async def create_trade(
    request: TradeRequest,
    db=Depends(get_db_session),
):
    """Log a trade execution."""
    log_trade(request.dict())
    db_trade = (
        db.query(Trade)
        .filter(Trade.symbol == request.symbol)
        .order_by(Trade.id.desc())
        .first()
    )
    return {
        "id": db_trade.id,
        "symbol": db_trade.symbol,
        "action": db_trade.action,
        "price": db_trade.price,
        "quantity": db_trade.quantity,
        "timestamp": db_trade.timestamp.isoformat(),
        "notes": db_trade.notes,
    }


@app.get("/api/v1/trades", response_model=TradeListResponse)
async def list_trades(limit: int = 100, db=Depends(get_db_session)):
    """List recent trades."""
    trades = db.query(Trade).order_by(Trade.id.desc()).limit(limit).all()
    return {
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "action": t.action,
                "price": t.price,
                "quantity": t.quantity,
                "timestamp": t.timestamp.isoformat(),
                "notes": t.notes,
            }
            for t in trades
        ],
        "count": len(trades),
    }


# ─────────────────────────────────────────────
# SSE endpoint — live price stream
# ─────────────────────────────────────────────


@app.get("/api/v1/stream/prices")
async def stream_prices(
    symbols: Optional[str] = Query(
        None,
        description="Comma-separated list of symbols to stream. "
        "Omit to stream all supported symbols.",
    )
):
    """
    Server-Sent Events endpoint for live price streaming.
    Connect with EventSource('/api/v1/stream/prices?symbols=EURUSD=X,GBPUSD=X').
    Each event is a JSON-encoded price tick.
    """
    requested = (
        [s.strip() for s in symbols.split(",") if s.strip()]
        if symbols
        else [s["symbol"] for s in FOREX_SYMBOLS]
    )

    async def event_generator():
        # Send an initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'symbols': requested, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        while True:
            try:
                for sym in requested:
                    price_data = fetch_current_price(sym)
                    if price_data:
                        payload = json.dumps({"type": "tick", **price_data})
                        yield f"data: {payload}\n\n"
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                err = json.dumps({"type": "error", "message": str(exc)})
                yield f"data: {err}\n\n"

            await asyncio.sleep(PRICE_STREAM_INTERVAL)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────
# Socket.IO event handlers
# ─────────────────────────────────────────────


@sio.on("connect", namespace="/predictions")
async def on_connect_predictions(sid, environ):
    await handle_predictions_connect(sid)
    logger.info(f"Predictions client {sid} connected")


@sio.on("disconnect", namespace="/predictions")
async def on_disconnect_predictions(sid):
    await handle_predictions_disconnect(sid)
    logger.info(f"Predictions client {sid} disconnected")


@sio.on("connect", namespace="/trades")
async def on_connect_trades(sid, environ):
    await handle_trades_connect(sid)
    logger.info(f"Trades client {sid} connected")


@sio.on("disconnect", namespace="/trades")
async def on_disconnect_trades(sid):
    await handle_trades_disconnect(sid)
    logger.info(f"Trades client {sid} disconnected")


@sio.on("connect", namespace="/tasks")
async def on_connect_tasks(sid, environ):
    await handle_tasks_connect(sid)
    logger.info(f"Tasks client {sid} connected")


@sio.on("disconnect", namespace="/tasks")
async def on_disconnect_tasks(sid):
    await handle_tasks_disconnect(sid)
    logger.info(f"Tasks client {sid} disconnected")


@sio.on("connect", namespace="/ticker")
async def on_connect_ticker(sid, environ):
    await handle_ticker_connect(sid)
    logger.info(f"Ticker client {sid} connected")


@sio.on("disconnect", namespace="/ticker")
async def on_disconnect_ticker(sid):
    await handle_ticker_disconnect(sid)
    logger.info(f"Ticker client {sid} disconnected")


# ─────────────────────────────────────────────
# Internal broadcast helpers (called by tasks)
# ─────────────────────────────────────────────


@app.post("/api/v1/broadcast/prediction")
async def broadcast_prediction_endpoint(prediction_data: dict):
    """Called by Celery tasks to push prediction results to clients."""
    try:
        await broadcast_prediction(sio, prediction_data)
        return {"status": "ok"}
    except Exception as exc:
        logger.error(f"Error broadcasting prediction: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/broadcast/trade")
async def broadcast_trade_endpoint(trade_data: dict):
    try:
        await broadcast_trade(sio, trade_data)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/v1/broadcast/task-status")
async def broadcast_task_status_endpoint(
    task_id: str,
    task_status: str,
    result: dict = None,
):
    try:
        await broadcast_task_status(sio, task_id, task_status, result)
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─────────────────────────────────────────────
# Health + frontend
# ─────────────────────────────────────────────


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "websocket_connections": get_connection_stats(),
    }


# Mount static files
_frontend_dir = Path(__file__).parent.parent / "frontend"
if (_frontend_dir / "static").exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(_frontend_dir / "static")),
        name="static",
    )


@app.get("/")
async def frontend_root():
    """Serve main dashboard."""
    frontend_file = _frontend_dir / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file), media_type="text/html")
    return {"status": "ok", "message": "API Server Running — no frontend found"}


# ─────────────────────────────────────────────
# Middleware + routers
# ─────────────────────────────────────────────

from src.api.middleware.logging import StructuredLoggingMiddleware  # noqa: E402
from src.api.routes.health import router as health_router  # noqa: E402

app.add_middleware(StructuredLoggingMiddleware)
app.include_router(health_router)

from src.api.config.logging import setup_logging  # noqa: E402
from ..config import LOG_LEVEL  # noqa: E402

setup_logging(LOG_LEVEL)
