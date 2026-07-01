import pytest
import json
from datetime import datetime
from src.db.logging import Prediction, Trade, ModelMetrics


@pytest.mark.unit
def test_prediction_table_schema(db_session):
    """Test prediction table has correct schema."""
    prediction = Prediction(
        symbol="EURUSD=X",
        prediction=1,
        prediction_class="BUY",
        confidence=0.85,
        current_price=1.0950,
        extra_data=json.dumps({"test": "data"})
    )
    db_session.add(prediction)
    db_session.commit()

    assert prediction.id is not None
    assert prediction.symbol == "EURUSD=X"
    assert prediction.prediction == 1
    assert prediction.confidence == 0.85


@pytest.mark.unit
def test_trade_table_schema(db_session):
    """Test trade table has correct schema."""
    trade = Trade(
        symbol="EURUSD=X",
        action="BUY",
        price=1.0950,
        quantity=1.0,
        notes="Test trade"
    )
    db_session.add(trade)
    db_session.commit()

    assert trade.id is not None
    assert trade.symbol == "EURUSD=X"
    assert trade.action == "BUY"
    assert trade.notes == "Test trade"


@pytest.mark.unit
def test_model_metrics_table_schema(db_session):
    """Test model metrics table has correct schema."""
    metrics = ModelMetrics(
        model_name="RandomForest",
        model_version="1.0.0",
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        extra_data=json.dumps({"feature_importance": {}})
    )
    db_session.add(metrics)
    db_session.commit()

    assert metrics.id is not None
    assert metrics.model_name == "RandomForest"
    assert metrics.accuracy == 0.85


@pytest.mark.unit
def test_prediction_timestamp_auto_set(db_session):
    """Test that prediction timestamp is auto-set."""
    before = datetime.utcnow()
    prediction = Prediction(
        symbol="EURUSD=X",
        prediction=1,
        prediction_class="BUY",
        confidence=0.85,
        current_price=1.0950,
        extra_data="{}"
    )
    db_session.add(prediction)
    db_session.commit()
    after = datetime.utcnow()

    assert prediction.timestamp is not None
    assert before <= prediction.timestamp <= after


@pytest.mark.unit
def test_trade_query_by_symbol(db_session):
    """Test querying trades by symbol."""
    trades = [
        Trade(symbol="EURUSD=X", action="BUY", price=1.0950, quantity=1.0),
        Trade(symbol="GBPUSD=X", action="SELL", price=1.2750, quantity=0.5),
        Trade(symbol="EURUSD=X", action="SELL", price=1.0960, quantity=1.0),
    ]
    for trade in trades:
        db_session.add(trade)
    db_session.commit()

    eur_trades = db_session.query(Trade).filter(Trade.symbol == "EURUSD=X").all()
    assert len(eur_trades) == 2


@pytest.mark.unit
def test_trade_nullable_notes(db_session):
    """Test that trade notes field is nullable."""
    trade = Trade(
        symbol="EURUSD=X",
        action="BUY",
        price=1.0950,
        quantity=1.0
    )
    db_session.add(trade)
    db_session.commit()

    fetched = db_session.query(Trade).first()
    assert fetched.notes is None


@pytest.mark.unit
def test_extra_data_json_storage(db_session):
    """Test that extra_data stores JSON correctly."""
    metadata = {"key1": "value1", "key2": 123}
    prediction = Prediction(
        symbol="EURUSD=X",
        prediction=1,
        prediction_class="BUY",
        confidence=0.85,
        current_price=1.0950,
        extra_data=json.dumps(metadata)
    )
    db_session.add(prediction)
    db_session.commit()

    fetched = db_session.query(Prediction).first()
    stored_metadata = json.loads(fetched.extra_data)
    assert stored_metadata["key1"] == "value1"
    assert stored_metadata["key2"] == 123


@pytest.mark.integration
def test_prediction_filtering_by_class(db_session):
    """Test filtering predictions by class."""
    predictions = [
        Prediction(symbol="EURUSD=X", prediction=1, prediction_class="BUY",
                  confidence=0.9, current_price=1.0950, extra_data="{}"),
        Prediction(symbol="EURUSD=X", prediction=0, prediction_class="SELL",
                  confidence=0.8, current_price=1.0950, extra_data="{}"),
        Prediction(symbol="EURUSD=X", prediction=1, prediction_class="BUY",
                  confidence=0.85, current_price=1.0960, extra_data="{}"),
    ]
    for pred in predictions:
        db_session.add(pred)
    db_session.commit()

    buy_preds = db_session.query(Prediction).filter(
        Prediction.prediction_class == "BUY"
    ).all()
    sell_preds = db_session.query(Prediction).filter(
        Prediction.prediction_class == "SELL"
    ).all()

    assert len(buy_preds) == 2
    assert len(sell_preds) == 1
