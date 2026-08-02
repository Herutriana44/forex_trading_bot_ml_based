"""
Feature engineering for forex trading bot.
Extracted from simple_bot.py and classification_experiments.py
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import yfinance as yf
from ..config import DEFAULT_SYMBOL, DEFAULT_LOOKBACK_DAYS, FEATURE_COLUMNS


def fetch_latest_data(symbol: str = DEFAULT_SYMBOL, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch latest market data from yfinance.

    Args:
        symbol: Forex pair symbol (e.g., "EURUSD=X")
        lookback_days: Number of days to fetch

    Returns:
        DataFrame with OHLC data
    """
    data = yf.download(symbol, period=f"{lookback_days}d", interval="1d", progress=False)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data


def fetch_current_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch just the current price and basic stats for a symbol.
    Lightweight call for streaming/ticker use.

    Args:
        symbol: Forex pair symbol

    Returns:
        Dict with price info or None on failure
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        hist = ticker.history(period="2d", interval="1d", raise_errors=False)

        if hist.empty:
            return None

        current_price = float(hist["Close"].iloc[-1])
        prev_price = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current_price
        change = current_price - prev_price
        change_pct = (change / prev_price * 100) if prev_price != 0 else 0.0

        return {
            "symbol": symbol,
            "price": round(current_price, 5),
            "open": round(float(hist["Open"].iloc[-1]), 5),
            "high": round(float(hist["High"].iloc[-1]), 5),
            "low": round(float(hist["Low"].iloc[-1]), 5),
            "prev_close": round(prev_price, 5),
            "change": round(change, 5),
            "change_pct": round(change_pct, 4),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception:
        return None


def prepare_features(data: pd.DataFrame, symbol: str = DEFAULT_SYMBOL) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Prepare features for model prediction from raw data.

    Args:
        data: Raw OHLC data from yfinance
        symbol: Forex pair symbol — used to populate metadata correctly

    Returns:
        Tuple of (features_df, metadata) where:
        - features_df: DataFrame with engineered features
        - metadata: Dict with current price and other info
    """
    df = data.copy()

    # Feature Engineering
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Daily_Return'] = df['Close'].pct_change()
    df['Body_Size'] = df['Close'] - df['Open']
    df['High_Low_Chg'] = df['High'] - df['Low']

    # Drop rows with NaN values (from rolling windows)
    df.dropna(inplace=True)

    # Get the latest row for prediction
    latest_row = df.iloc[[-1]].copy()

    # Extract metadata — use the passed symbol, not the hardcoded DEFAULT_SYMBOL
    current_price = float(latest_row['Close'].iloc[0])
    metadata = {
        "current_price": current_price,
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat(),
        "features_used": FEATURE_COLUMNS,
        "open": float(latest_row['Open'].iloc[0]),
        "high": float(latest_row['High'].iloc[0]),
        "low": float(latest_row['Low'].iloc[0]),
    }

    # Return only the feature columns
    return latest_row[FEATURE_COLUMNS], metadata


def prepare_training_data(symbol: str = DEFAULT_SYMBOL, start_date: str = "2019-01-01",
                         end_date: str = datetime.now().strftime("%Y-%m-%d")) -> pd.DataFrame:
    """
    Prepare data for model training.

    Args:
        symbol: Forex pair symbol
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        DataFrame with features and target for training
    """
    print(f"Mengunduh data {symbol} dari {start_date} sampai {end_date}...")
    data = yf.download(symbol, start=start_date, end=end_date)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    print("Membuat fitur teknikal...")
    # Feature Engineering
    data['SMA_10'] = data['Close'].rolling(window=10).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['Daily_Return'] = data['Close'].pct_change()
    data['Body_Size'] = data['Close'] - data['Open']
    data['High_Low_Chg'] = data['High'] - data['Low']

    # Create target: 1 if next day's close > current close, else 0
    data['Target'] = np.where(data['Close'].shift(-1) > data['Close'], 1, 0)

    # Drop rows with NaN values
    data.dropna(inplace=True)

    return data