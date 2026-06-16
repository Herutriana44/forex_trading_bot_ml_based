import yfinance as yf
import pandas as pd
import numpy as np
import joblib
import time
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# 1. Konfigurasi Bot
SYMBOL = "EURUSD=X"
MODEL_PATH = "forex_rf_model.pkl"

def load_trading_model():
    try:
        model = joblib.load(MODEL_PATH)
        print(f"✅ Model {MODEL_PATH} berhasil dimuat.")
        return model
    except FileNotFoundError:
        print(f"❌ Model tidak ditemukan! Jalankan kode training terlebih dahulu.")
        exit()

def get_latest_data(symbol):
    # Mengambil data 100 hari terakhir untuk memastikan indikator SMA_50 bisa dihitung
    data = yf.download(symbol, period="100d", interval="1d")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    return data

def prepare_features(data):
    df = data.copy()

    # Membuat fitur yang SAMA PERSIS dengan saat training
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['Daily_Return'] = df['Close'].pct_change()
    df['Body_Size'] = df['Close'] - df['Open']

    # Kita hanya butuh baris terakhir (data hari ini) untuk prediksi esok hari
    latest_row = df.iloc[[-1]]

    features = ['Open', 'High', 'Low', 'Close', 'SMA_10', 'SMA_50', 'Daily_Return', 'Body_Size']
    return latest_row[features]

def execute_mock_trade(prediction, current_price):
    print(f"\n[ANALISIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print(f"Harga EUR/USD Saat Ini: {current_price:.5f}")

    if prediction == 1:
        print("🔮 Prediksi: Harga besok cenderung NAIK.")
        print("🚀 [AKSI BOT]: Sinyal BUY dieksekusi! (Simulasi)")
    elif prediction == 0:
        print("🔮 Prediksi: Harga besok cenderung TURUN.")
        print("📉 [AKSI BOT]: Sinyal SELL/SHORT dieksekusi! (Simulasi)")
    else:
        print("💤 [AKSI BOT]: HOLD / Menunggu peluang selanjutnya.")

def run_bot():
    print("=== MEMULAI BOT TRADING FOREX ML ===")
    model = load_trading_model()

    # Loop berjalan terus-menerus (misal: cek pasar setiap 1 jam atau 24 jam)
    # Untuk demo, kita jalankan sekali. Jika ingin terus berjalan, ubah menjadi loop `while True:`
    try:
        print("\nMengambil data pasar terbaru...")
        raw_data = get_latest_data(SYMBOL)

        # Ambil harga penutupan terakhir
        current_price = raw_data['Close'].iloc[-1]

        # Proses data menjadi fitur untuk model
        features_latest = prepare_features(raw_data)

        # Cek apakah ada nilai kosong (NaN)
        if features_latest.isnull().values.any():
            print("⚠️ Data belum lengkap untuk menghitung indikator. Menunggu data baru...")
            return

        # Prediksi arah pasar
        prediction = model.predict(features_latest)[0]

        # Eksekusi Order (Simulasi)
        execute_mock_trade(prediction, current_price)

    except Exception as e:
        print(f"发生错误 / Terjadi Kesalahan: {e}")

if __name__ == "__main__":
    run_bot()