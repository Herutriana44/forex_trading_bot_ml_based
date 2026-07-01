import pytest
from fastapi import status


@pytest.mark.unit
def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "websocket_connections" in data


@pytest.mark.unit
def test_model_status_not_found(client):
    """Test model status when no model exists."""
    response = client.get("/api/v1/model/status")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.unit
def test_create_prediction_task(client, mocker):
    """Test creating a prediction task."""
    # Mock Celery
    mock_task = mocker.MagicMock()
    mock_task.id = "test-task-123"
    mocker.patch("src.api.main.predict_task.delay", return_value=mock_task)

    response = client.post("/api/v1/predict", json={"symbol": "EURUSD=X"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["task_id"] == "test-task-123"
    assert data["status"] == "queued"


@pytest.mark.unit
def test_get_prediction_pending(client, mocker):
    """Test getting pending prediction result."""
    mock_task = mocker.MagicMock()
    mock_task.state = "PENDING"
    mocker.patch("src.tasks.celery_app.AsyncResult", return_value=mock_task)

    response = client.get("/api/v1/predict/test-task-123")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "pending"


@pytest.mark.unit
def test_get_prediction_success(client, mocker, sample_prediction):
    """Test getting successful prediction result."""
    mock_task = mocker.MagicMock()
    mock_task.state = "SUCCESS"
    mock_task.result = {
        "status": "success",
        "symbol": "EURUSD=X",
        "prediction": 1,
        "prediction_class": "BUY",
        "confidence": 0.85,
        "metadata": sample_prediction["metadata"]
    }
    mocker.patch("src.tasks.celery_app.AsyncResult", return_value=mock_task)

    response = client.get("/api/v1/predict/test-task-123")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert data["prediction_class"] == "BUY"
    assert data["confidence"] == 0.85


@pytest.mark.unit
def test_create_trade(client, db_session, sample_trade):
    """Test creating a trade."""
    response = client.post("/api/v1/trades", json=sample_trade)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["symbol"] == sample_trade["symbol"]
    assert data["action"] == sample_trade["action"]
    assert data["price"] == sample_trade["price"]


@pytest.mark.unit
def test_list_trades(client, db_session, sample_trade):
    """Test listing trades."""
    # Create a trade first
    client.post("/api/v1/trades", json=sample_trade)

    response = client.get("/api/v1/trades")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "trades" in data
    assert "count" in data
    assert data["count"] >= 1


@pytest.mark.unit
def test_broadcast_prediction_endpoint(client, mocker, sample_prediction):
    """Test broadcast prediction endpoint."""
    mocker.patch("src.api.main.broadcast_prediction")

    response = client.post("/api/v1/broadcast/prediction", json=sample_prediction)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.unit
def test_frontend_root(client):
    """Test frontend root route."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
