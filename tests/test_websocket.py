import pytest
import asyncio
from unittest.mock import MagicMock, patch


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_predictions_connect():
    """Test WebSocket connection to predictions namespace."""
    from src.api.websocket_handler import handle_predictions_connect

    sid = "test-client-123"
    await handle_predictions_connect(sid)

    # Verify connection was tracked
    from src.api.websocket_handler import active_connections
    assert sid in active_connections["predictions"]


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_predictions_disconnect():
    """Test WebSocket disconnection from predictions namespace."""
    from src.api.websocket_handler import (
        handle_predictions_connect, handle_predictions_disconnect,
        active_connections
    )

    sid = "test-client-123"
    await handle_predictions_connect(sid)
    assert sid in active_connections["predictions"]

    await handle_predictions_disconnect(sid)
    assert sid not in active_connections["predictions"]


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_broadcast_prediction():
    """Test broadcasting prediction to connected clients."""
    from src.api.websocket_handler import (
        broadcast_prediction, handle_predictions_connect,
        active_connections
    )

    sid = "test-client-123"
    await handle_predictions_connect(sid)

    # Mock Socket.IO instance
    mock_sio = MagicMock()
    mock_sio.emit = MagicMock(return_value=asyncio.sleep(0))

    prediction_data = {
        "symbol": "EURUSD=X",
        "prediction": 1,
        "prediction_class": "BUY",
        "confidence": 0.85
    }

    await broadcast_prediction(mock_sio, prediction_data)

    # Verify emit was called
    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "new_prediction"


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_broadcast_trade():
    """Test broadcasting trade to connected clients."""
    from src.api.websocket_handler import (
        broadcast_trade, handle_trades_connect,
        active_connections
    )

    sid = "test-client-456"
    await handle_trades_connect(sid)

    mock_sio = MagicMock()
    mock_sio.emit = MagicMock(return_value=asyncio.sleep(0))

    trade_data = {
        "symbol": "EURUSD=X",
        "action": "BUY",
        "price": 1.0950,
        "quantity": 1.0
    }

    await broadcast_trade(mock_sio, trade_data)

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "new_trade"


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_broadcast_task_status():
    """Test broadcasting task status update."""
    from src.api.websocket_handler import (
        broadcast_task_status, handle_tasks_connect,
        active_connections
    )

    sid = "test-client-789"
    await handle_tasks_connect(sid)

    mock_sio = MagicMock()
    mock_sio.emit = MagicMock(return_value=asyncio.sleep(0))

    await broadcast_task_status(mock_sio, "task-123", "success", {"result": "ok"})

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "task_update"


@pytest.mark.websocket
def test_connection_stats():
    """Test getting connection statistics."""
    from src.api.websocket_handler import (
        get_connection_stats, active_connections
    )

    # Clear and reset
    active_connections["predictions"].clear()
    active_connections["trades"].clear()
    active_connections["tasks"].clear()

    # Add some connections
    active_connections["predictions"].add("client-1")
    active_connections["predictions"].add("client-2")
    active_connections["trades"].add("client-3")

    stats = get_connection_stats()
    assert stats["predictions"] == 2
    assert stats["trades"] == 1
    assert stats["tasks"] == 0
    assert stats["total"] == 3
