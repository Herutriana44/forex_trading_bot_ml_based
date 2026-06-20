from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
from datetime import datetime
import json
import requests
import time
from src.db.logging import get_db, Prediction, Trade
from sqlalchemy import desc

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

# Helper function to fetch data from API
def fetch_api_data(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Helper function to fetch data from database
def fetch_latest_predictions(limit=10):
    try:
        db = next(get_db())
        predictions = db.query(Prediction).order_by(desc(Prediction.timestamp)).limit(limit).all()
        result = {
            "predictions": [
                {
                    "id": p.id,
                    "symbol": p.symbol,
                    "prediction": p.prediction,
                    "prediction_class": p.prediction_class,
                    "confidence": p.confidence,
                    "current_price": p.current_price,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    "metadata": json.loads(p.extra_data) if p.extra_data else {}
                }
                for p in predictions
            ]
        }
        db.close()
        return result
    except Exception as e:
        return {"error": str(e), "predictions": []}

def fetch_latest_trades(limit=10):
    try:
        db = next(get_db())
        trades = db.query(Trade).order_by(desc(Trade.timestamp)).limit(limit).all()
        result = {
            "trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "action": t.action,
                    "price": t.price,
                    "quantity": t.quantity,
                    "timestamp": t.timestamp.isoformat() if t.timestamp else None,
                    "notes": t.notes
                }
                for t in trades
            ]
        }
        db.close()
        return result
    except Exception as e:
        return {"error": str(e), "trades": []}

# Helper function to fetch task status
def fetch_task_status(task_id):
    try:
        response = requests.get(f"{API_BASE_URL}/predict/{task_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "status": "error"}

# Streaming endpoint for predictions
@app.route('/stream/predictions')
def stream_predictions():
    def event_stream():
        while True:
            # Fetch latest predictions from DB
            predictions = fetch_latest_predictions()

            # Format data for streaming
            data = {
                "type": "predictions",
                "data": predictions,
                "timestamp": datetime.now().isoformat()
            }

            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)  # Update every 5 seconds

    return Response(event_stream(), mimetype="text/event-stream")

# Streaming endpoint for trades
@app.route('/stream/trades')
def stream_trades():
    def event_stream():
        while True:
            # Fetch latest trades from DB
            trades = fetch_latest_trades()

            # Format data for streaming
            data = {
                "type": "trades",
                "data": trades,
                "timestamp": datetime.now().isoformat()
            }

            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(5)  # Update every 5 seconds

    return Response(event_stream(), mimetype="text/event-stream")

# Main dashboard route
@app.route('/')
def dashboard():
    # Fetch initial data
    model_status = fetch_api_data("model/status")
    recent_predictions = fetch_latest_predictions()
    recent_trades = fetch_latest_trades()

    return render_template(
        'dashboard.html',
        model_status=model_status,
        recent_predictions=recent_predictions,
        recent_trades=recent_trades
    )

# API routes to trigger actions
@app.route('/api/predict', methods=['POST'])
def create_prediction():
    symbol = request.json.get('symbol', 'EURUSD=X')

    try:
        response = requests.post(
            f"{API_BASE_URL}/predict",
            json={"symbol": symbol}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/predict/<task_id>', methods=['GET'])
def get_prediction_status(task_id):
    """Get prediction task status and result."""
    try:
        response = requests.get(f"{API_BASE_URL}/predict/{task_id}", timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/retrain', methods=['POST'])
def create_retrain_task():
    symbol = request.json.get('symbol', 'EURUSD=X')
    start_date = request.json.get('start_date', '2019-01-01')

    try:
        response = requests.post(
            f"{API_BASE_URL}/model/retrain",
            json={"symbol": symbol, "start_date": start_date}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/retrain/<task_id>', methods=['GET'])
def get_retrain_status(task_id):
    """Get retrain task status and result."""
    try:
        response = requests.get(f"{API_BASE_URL}/model/retrain/{task_id}", timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade', methods=['POST'])
def create_trade():
    trade_data = request.json

    try:
        response = requests.post(
            f"{API_BASE_URL}/trades",
            json=trade_data
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
