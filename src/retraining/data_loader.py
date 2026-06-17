"""
Data loader for retraining pipeline.
"""

import pandas as pd
from datetime import datetime
from typing import Optional
import yfinance as yf


def fetch_historical_data(symbol: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """Fetch historical forex data."""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    data = yf.download(symbol, start=start_date, end=end_date)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def validate_data(data: pd.DataFrame) -> bool:
    """Validate that data has enough rows."""
    min_rows = 60  # At least 60 days for SMA_50 + some buffer
    if len(data) < min_rows:
        raise ValueError(f"Insufficient data: {len(data)} rows. Need at least {min_rows}.")
    return True