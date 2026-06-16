import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib
import warnings
import datetime

warnings.filterwarnings('ignore')

x = datetime.datetime.now()
now_date = x.strftime("%Y-%m-%d")

def prepare_data(symbol="EURUSD=X", start_date="2019-01-01", end_date=now_date):
    print(f"Mengunduh data {symbol}...")
    data = yf.download(symbol, start=start_date, end=end_date)

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    print("Membuat fitur teknikal...")
    # Feature Engineering
    data['SMA_10'] = data['Close'].rolling(window=10).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    data['Daily_Return'] = data['Close'].pct_change()
    data['Body_Size'] = data['Close'] - data['Open']

    # Indikator tambahan untuk algoritma yang lebih kompleks
    data['High_Low_Chg'] = data['High'] - data['Low']
    data['Target'] = np.where(data['Close'].shift(-1) > data['Close'], 1, 0)

    data.dropna(inplace=True)
    return data

def run_experiment():
    df = prepare_data()

    features = ['Open', 'High', 'Low', 'Close', 'SMA_10', 'SMA_50', 'Daily_Return', 'Body_Size', 'High_Low_Chg']
    X = df[features]
    y = df['Target']

    # Split data (80% Train, 20% Test) - Tanpa shuffle karena time-series
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # Kamus Kamus Algoritma yang akan dieksperimenkan
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=100, learning_rate=0.05, max_depth=3, random_state=42, eval_metric='logloss')
    }

    results = []
    best_accuracy = 0
    best_model = None
    best_model_name = ""

    print("\n=== MEMULAI EKSPERIMEN ===")
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)

        # Prediksi
        y_pred = model.predict(X_test)

        # Hitung Metrik
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)

        results.append({
            "Model": name,
            "Accuracy": f"{acc*100:.2f}%",
            "Precision (Buy)": f"{prec*100:.2f}%",
            "Recall (Buy)": f"{rec*100:.2f}%"
        })

        model_filename = f"{name.lower()}_model.pkl"
        joblib.dump(model, model_filename)
        print(f"Mengekspor {model_filename}...")

        # Cari model terbaik berdasarkan Akurasi
        if acc > best_accuracy:
            best_accuracy = acc
            best_model = model
            best_model_name = name

    # Tampilkan Hasil dalam bentuk Tabel DataFrame
    df_results = pd.DataFrame(results)
    print("\n--- HASIL PERBANDINGAN MODEL ---")
    print(df_results.to_string(index=False))

    df_results = pd.DataFrame(results)
    excel_filename = "experiment_results.xlsx"
    
    # Menggunakan engine openpyxl untuk nulis format excel
    df_results.to_excel(excel_filename, index=False)

    # Simpan model terbaik
    filename = f"best_forex_model_{best_model_name.lower().replace(' ', '_')}.pkl"
    joblib.dump(best_model, filename)
    print(f"\nModel terbaik adalah {best_model_name} dengan akurasi {best_accuracy*100:.2f}%")
    print(f"Model tersebut telah disimpan sebagai '{filename}'")

if __name__ == "__main__":
    run_experiment()