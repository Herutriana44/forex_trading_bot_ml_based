"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class PredictionRequest(BaseModel):
    symbol: str = Field("GBPUSD=X", description="Forex pair symbol (e.g. GBPUSD=X, USDJPY=X)")


class PredictionResponse(BaseModel):
    task_id: str = Field(..., description="Task ID for async prediction")
    status: str = Field(..., description="Task status")


class PredictionResult(BaseModel):
    symbol: str
    prediction: int
    prediction_class: str
    confidence: float
    current_price: float
    timestamp: str
    status: str
    error: Optional[str] = None


class RetrainRequest(BaseModel):
    symbol: Optional[str] = Field("GBPUSD=X", description="Forex pair symbol")
    start_date: Optional[str] = Field("2019-01-01", description="Start date for training data")


class RetrainResponse(BaseModel):
    task_id: str = Field(..., description="Task ID for async retraining")
    status: str = Field(..., description="Task status")


class RetrainResult(BaseModel):
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ModelStatus(BaseModel):
    model_name: str
    model_version: str
    accuracy: float
    precision: float
    recall: float
    timestamp: str
    current: bool


class TradeRequest(BaseModel):
    symbol: str = Field(..., description="Forex pair symbol")
    action: str = Field(..., description="BUY or SELL")
    price: float = Field(..., description="Execution price")
    quantity: Optional[float] = Field(1.0, description="Trade quantity")
    notes: Optional[str] = Field(None, description="Additional notes")


class TradeResponse(BaseModel):
    id: int
    symbol: str
    action: str
    price: float
    quantity: float
    timestamp: str
    notes: Optional[str]


class TradeListResponse(BaseModel):
    trades: List[TradeResponse]
    count: int