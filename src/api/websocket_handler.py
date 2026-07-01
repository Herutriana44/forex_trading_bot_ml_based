"""
WebSocket handlers for real-time updates using Socket.IO.
Broadcasts predictions, trades, and task status to connected clients.
"""

from typing import Dict, Set
import logging
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Store active connections per namespace
active_connections: Dict[str, Set[str]] = {
    "predictions": set(),
    "trades": set(),
    "tasks": set()
}


async def handle_predictions_connect(sid: str):
    """Handle new prediction stream connection."""
    active_connections["predictions"].add(sid)
    logger.info(f"Prediction client connected: {sid}")


async def handle_predictions_disconnect(sid: str):
    """Handle prediction stream disconnection."""
    active_connections["predictions"].discard(sid)
    logger.info(f"Prediction client disconnected: {sid}")


async def handle_trades_connect(sid: str):
    """Handle new trade stream connection."""
    active_connections["trades"].add(sid)
    logger.info(f"Trade client connected: {sid}")


async def handle_trades_disconnect(sid: str):
    """Handle trade stream disconnection."""
    active_connections["trades"].discard(sid)
    logger.info(f"Trade client disconnected: {sid}")


async def handle_tasks_connect(sid: str):
    """Handle new task status stream connection."""
    active_connections["tasks"].add(sid)
    logger.info(f"Task client connected: {sid}")


async def handle_tasks_disconnect(sid: str):
    """Handle task status stream disconnection."""
    active_connections["tasks"].discard(sid)
    logger.info(f"Task client disconnected: {sid}")


async def broadcast_prediction(sio, prediction_data: dict):
    """
    Broadcast new prediction to all connected prediction clients.
    Called when predict_task completes.
    """
    if not active_connections["predictions"]:
        return

    message = {
        "type": "prediction",
        "data": prediction_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        await sio.emit(
            "new_prediction",
            message,
            to=list(active_connections["predictions"]),
            namespace="/predictions"
        )
        logger.debug(f"Broadcast prediction to {len(active_connections['predictions'])} clients")
    except Exception as e:
        logger.error(f"Error broadcasting prediction: {e}")


async def broadcast_trade(sio, trade_data: dict):
    """
    Broadcast new trade execution to all connected trade clients.
    Called when trade is logged.
    """
    if not active_connections["trades"]:
        return

    message = {
        "type": "trade",
        "data": trade_data,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        await sio.emit(
            "new_trade",
            message,
            to=list(active_connections["trades"]),
            namespace="/trades"
        )
        logger.debug(f"Broadcast trade to {len(active_connections['trades'])} clients")
    except Exception as e:
        logger.error(f"Error broadcasting trade: {e}")


async def broadcast_task_status(sio, task_id: str, status: str, result: dict = None):
    """
    Broadcast task status update to all connected task clients.
    Called when Celery task status changes.
    """
    if not active_connections["tasks"]:
        return

    message = {
        "type": "task_status",
        "task_id": task_id,
        "status": status,
        "result": result,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        await sio.emit(
            "task_update",
            message,
            to=list(active_connections["tasks"]),
            namespace="/tasks"
        )
        logger.debug(f"Broadcast task status to {len(active_connections['tasks'])} clients")
    except Exception as e:
        logger.error(f"Error broadcasting task status: {e}")


def get_connection_stats() -> dict:
    """Get current connection statistics."""
    return {
        "predictions": len(active_connections["predictions"]),
        "trades": len(active_connections["trades"]),
        "tasks": len(active_connections["tasks"]),
        "total": sum(len(v) for v in active_connections.values())
    }
