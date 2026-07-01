import pytest
from pathlib import Path
from src.inference.feature_engineer import FeatureEngineer
from src.db.logging import Prediction, Trade, ModelMetrics


@pytest.mark.unit
def test_feature_engineer_creation():
    """Test FeatureEngineer initialization."""
    engineer = FeatureEngineer()
    assert engineer is not None


@pytest.mark.unit
def test_prediction_model_creation(db_session, sample_prediction):
    """Test creating prediction record in database."""
    prediction = Prediction(
        symbol=sample_prediction["symbol"],
        prediction=sample_prediction["prediction"],
        prediction_class=sample_prediction["prediction_class"],
        confidence=sample_prediction["confidence"],
        current_price=sample_prediction["current_price"],
        extra_data="{}"
    )
    db_session.add(prediction)
    db_session.commit()

    fetched = db_session.query(Prediction).filter(
        Prediction.symbol == sample_prediction["symbol"]
    ).first()
    assert fetched is not None
    assert fetched.prediction_class == "BUY"
    assert fetched.confidence == 0.85


@pytest.mark.unit
def test_trade_model_creation(db_session, sample_trade):
    """Test creating trade record in database."""
    trade = Trade(
        symbol=sample_trade["symbol"],
        action=sample_trade["action"],
        price=sample_trade["price"],
        quantity=sample_trade["quantity"],
        notes=sample_trade["notes"]
    )
    db_session.add(trade)
    db_session.commit()

    fetched = db_session.query(Trade).filter(
        Trade.symbol == sample_trade["symbol"]
    ).first()
    assert fetched is not None
    assert fetched.action == "BUY"
    assert fetched.price == 1.0950


@pytest.mark.unit
def test_model_metrics_creation(db_session):
    """Test creating model metrics record."""
    metrics = ModelMetrics(
        model_name="RandomForest",
        model_version="1.0.0",
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        extra_data="{}"
    )
    db_session.add(metrics)
    db_session.commit()

    fetched = db_session.query(ModelMetrics).filter(
        ModelMetrics.model_name == "RandomForest"
    ).first()
    assert fetched is not None
    assert fetched.accuracy == 0.85


@pytest.mark.integration
def test_prediction_to_trade_workflow(db_session):
    """Test workflow from prediction to trade."""
    # Create prediction
    prediction = Prediction(
        symbol="EURUSD=X",
        prediction=1,
        prediction_class="BUY",
        confidence=0.92,
        current_price=1.0950,
        extra_data="{}"
    )
    db_session.add(prediction)
    db_session.commit()

    # Create trade based on prediction
    trade = Trade(
        symbol="EURUSD=X",
        action="BUY",
        price=1.0950,
        quantity=1.0,
        notes="Based on prediction"
    )
    db_session.add(trade)
    db_session.commit()

    # Verify both records exist
    pred_count = db_session.query(Prediction).count()
    trade_count = db_session.query(Trade).count()
    assert pred_count >= 1
    assert trade_count >= 1


@pytest.mark.unit
def test_multiple_predictions_query(db_session):
    """Test querying multiple predictions."""
    predictions = [
        Prediction(symbol="EURUSD=X", prediction=1, prediction_class="BUY",
                  confidence=0.85, current_price=1.0950, extra_data="{}"),
        Prediction(symbol="GBPUSD=X", prediction=0, prediction_class="SELL",
                  confidence=0.78, current_price=1.2750, extra_data="{}"),
    ]
    for pred in predictions:
        db_session.add(pred)
    db_session.commit()

    all_preds = db_session.query(Prediction).all()
    assert len(all_preds) >= 2

    buy_preds = db_session.query(Prediction).filter(
        Prediction.prediction_class == "BUY"
    ).all()
    assert len(buy_preds) >= 1
