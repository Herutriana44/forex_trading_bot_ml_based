"""
WebSocket handlers for real-time updates using Socket.IO.
Broadcasts predictions, trades, task status, and live price ticks
to connected clients across four namespaces:
  /predictions  — ML prediction results
  /trades       — logged trade executions
  /tasks        — Celery task status updates
  /ticker       — live price ticks for all symbols
"""

import logging
from datetime import datetime
from typing import Dict, Set

logger = logging.getLogger(__name__)

# Active connection sets per namespace
active_connections: Dict[str, Set[str]] = {
    "predictions": set(),
    "trades": set(),
    "tasks": set(),
    "ticker": set(),
}


# ─── Connection lifecycle ────────────────────────────────────────────────────


async def handle_predictions_connect(sid: str):
    active_connections["predictions"].add(sid)
    logger.debug(f"Prediction client connected: {sid}")


async def handle_predictions_disconnect(sid: str):
    active_connections["predictions"].discard(sid)
    logger.debug(f"Prediction client disconnected: {sid}")


async def handle_trades_connect(sid: str):
    active_connections["trades"].add(sid)
    logger.debug(f"Trade client connected: {sid}")


async def handle_trades_disconnect(sid: str):
    active_connections["trades"].discard(sid)
    logger.debug(f"Trade client disconnected: {sid}")


async def handle_tasks_connect(sid: str):
    active_connections["tasks"].add(sid)
    logger.debug(f"Task client connected: {sid}")


async def handle_tasks_disconnect(sid: str):
    active_connections["tasks"].discard(sid)
    logger.debug(f"Task client disconnected: {sid}")


async def handle_ticker_connect(sid: str):
    active_connections["ticker"].add(sid)
    logger.debug(f"Ticker client connected: {sid}")


async def handle_ticker_disconnect(sid: str):
    active_connections["ticker"].discard(sid)
    logger.debug(f"Ticker client disconnected: {sid}")


# ─── Broadcast helpers ───────────────────────────────────────────────────────


async def broadcast_prediction(sio, prediction_data: dict):
    """
    Broadcast a completed prediction result to all /predictions clients.
    Called after predict_task completes.
    """
    if not active_connections["predictions"]:
        return

    message = {
        "type": "prediction",
        "data": prediction_data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        await sio.emit(
            "new_prediction",
            message,
            to=list(active_connections["predictions"]),
            namespace="/predictions",
        )
        logger.debug(
            f"Broadcast prediction to {len(active_connections['predictions'])} clients"
        )
    except Exception as exc:
        logger.error(f"Error broadcasting prediction: {exc}")


async def broadcast_trade(sio, trade_data: dict):
    """
    Broadcast a new trade execution to all /trades clients.
    Called when a trade is logged.
    """
    if not active_connections["trades"]:
        return

    message = {
        "type": "trade",
        "data": trade_data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        await sio.emit(
            "new_trade",
            message,
            to=list(active_connections["trades"]),
            namespace="/trades",
        )
    except Exception as exc:
        logger.error(f"Error broadcasting trade: {exc}")


async def broadcast_task_status(sio, task_id: str, status: str, result: dict = None):
    """
    Broadcast a Celery task status change to all /tasks clients.
    """
    if not active_connections["tasks"]:
        return

    message = {
        "type": "task_status",
        "task_id": task_id,
        "status": status,
        "result": result,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        await sio.emit(
            "task_update",
            message,
            to=list(active_connections["tasks"]),
            namespace="/tasks",
        )
    except Exception as exc:
        logger.error(f"Error broadcasting task status: {exc}")


async def broadcast_ticker(sio, price_data: dict):
    """
    Broadcast a live price tick to all /ticker clients.
    Called by the background price-streaming loop in main.py.
    price_data shape: {symbol, price, open, high, low, prev_close, change, change_pct, timestamp}
    """
    if not active_connections["ticker"]:
        return

    message = {
        "type": "tick",
        "data": price_data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        await sio.emit(
            "price_tick",
            message,
            namespace="/ticker",
        )
    except Exception as exc:
        logger.error(f"Error broadcasting ticker: {exc}")


# ─── Stats ───────────────────────────────────────────────────────────────────


def get_connection_stats() -> dict:
    """Return current connection counts for all namespaces."""
    return {
        ns: len(clients) for ns, clients in active_connections.items()
    } | {"total": sum(len(v) for v in active_connections.values())}
