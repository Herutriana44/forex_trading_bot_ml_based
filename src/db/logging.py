"""
Database logging for trades and predictions.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import Dict, Any
import json
from ..config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    prediction = Column(Integer)
    prediction_class = Column(String)
    confidence = Column(Float)
    current_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column("extra_data", Text)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    action = Column(String)
    price = Column(Float)
    quantity = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)


class ModelMetrics(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String)
    model_version = Column(String)
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    extra_data = Column("extra_data", Text)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def log_prediction(prediction_data: Dict[str, Any]):
    """Log prediction to database."""
    db = SessionLocal()
    try:
        pred = Prediction(
            symbol=prediction_data["symbol"],
            prediction=prediction_data["prediction"],
            prediction_class=prediction_data["prediction_class"],
            confidence=prediction_data["confidence"],
            current_price=prediction_data["metadata"]["current_price"],
            extra_data=json.dumps(prediction_data["metadata"])
        )
        db.add(pred)
        db.commit()
    finally:
        db.close()


def log_trade(trade_data: Dict[str, Any]):
    """Log trade execution to database."""
    db = SessionLocal()
    try:
        trade = Trade(
            symbol=trade_data["symbol"],
            action=trade_data["action"],
            price=trade_data["price"],
            quantity=trade_data.get("quantity", 1.0),
            notes=trade_data.get("notes")
        )
        db.add(trade)
        db.commit()
    finally:
        db.close()


def log_model_metrics(metrics_data: Dict[str, Any]):
    """Log model training metrics to database."""
    db = SessionLocal()
    try:
        metrics = ModelMetrics(
            model_name=metrics_data["model_name"],
            model_version=metrics_data["model_version"],
            accuracy=metrics_data["accuracy"],
            precision=metrics_data["precision"],
            recall=metrics_data["recall"],
            extra_data=json.dumps(metrics_data.get("metadata", {}))
        )
        db.add(metrics)
        db.commit()
    finally:
        db.close()
