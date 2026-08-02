/**
 * api-client.js — REST + SSE client
 * Handles all HTTP calls and the Server-Sent Events price stream.
 */

const API_BASE = `${location.protocol}//${location.host}/api/v1`;

class APIClient {
  constructor() {
    this.baseURL  = API_BASE;
    this._sseConn = null; // active EventSource
  }

  // ── Generic fetch wrapper ────────────────────────────────────────────────

  async request(endpoint, options = {}) {
    const res = await fetch(`${this.baseURL}${endpoint}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
    return res.json();
  }

  // ── Symbol list ──────────────────────────────────────────────────────────

  async getSymbols() {
    return this.request('/symbols');
  }

  // ── Model ────────────────────────────────────────────────────────────────

  async getModelStatus() {
    return this.request('/model/status');
  }

  // ── Predictions ──────────────────────────────────────────────────────────

  async predictSymbol(symbol) {
    return this.request('/predict', {
      method: 'POST',
      body: JSON.stringify({ symbol }),
    });
  }

  async getPredictionResult(taskId) {
    return this.request(`/predict/${taskId}`);
  }

  // ── Retraining ───────────────────────────────────────────────────────────

  async retrainModel(symbol, startDate) {
    return this.request('/model/retrain', {
      method: 'POST',
      body: JSON.stringify({ symbol, start_date: startDate }),
    });
  }

  async getRetrainResult(taskId) {
    return this.request(`/model/retrain/${taskId}`);
  }

  // ── Trades ───────────────────────────────────────────────────────────────

  async getTrades(limit = 50) {
    return this.request(`/trades?limit=${limit}`);
  }

  async createTrade(tradeData) {
    return this.request('/trades', {
      method: 'POST',
      body: JSON.stringify(tradeData),
    });
  }

  // ── Health ───────────────────────────────────────────────────────────────

  async healthCheck() {
    const res = await fetch(`${location.protocol}//${location.host}/health`);
    return res.json();
  }

  // ── SSE price stream ─────────────────────────────────────────────────────

  /**
   * Open an SSE connection to /api/v1/stream/prices.
   * @param {string[]} symbols  — array of symbol strings to subscribe to
   * @param {function} onTick   — called with each price tick object
   * @param {function} onError  — called on connection error
   */
  openPriceStream(symbols = [], onTick, onError) {
    this.closePriceStream();

    const query = symbols.length
      ? `?symbols=${encodeURIComponent(symbols.join(','))}`
      : '';

    const es = new EventSource(`${this.baseURL}/stream/prices${query}`);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'tick' && typeof onTick === 'function') {
          onTick(data);
        }
      } catch (_) {}
    };

    es.onerror = () => {
      if (typeof onError === 'function') onError();
    };

    this._sseConn = es;
    return es;
  }

  closePriceStream() {
    if (this._sseConn) {
      this._sseConn.close();
      this._sseConn = null;
    }
  }

  get sseConnected() {
    return this._sseConn && this._sseConn.readyState === EventSource.OPEN;
  }
}

window.apiClient = new APIClient();
