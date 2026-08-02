/**
 * socket-client.js — Socket.IO client
 * Connects to /predictions, /trades, /tasks, and /ticker namespaces.
 * Routes events to window.uiManager and tracks connection state.
 */

const WS_BASE = `${location.protocol}//${location.host}`;

class SocketClient {
  constructor() {
    this.sockets = { predictions: null, trades: null, tasks: null, ticker: null };
    this._connState = { predictions: false, trades: false, tasks: false, ticker: false };
  }

  // ── Connect all namespaces ───────────────────────────────────────────────

  connect() {
    const opts = {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
      reconnectionAttempts: Infinity,
    };

    // /predictions ──────────────────────────────────────────────────────────
    this.sockets.predictions = io(`${WS_BASE}/predictions`, opts);

    this.sockets.predictions.on('connect', () => {
      this._setConn('predictions', true);
      this.log('Connected to predictions stream', 'success');
    });
    this.sockets.predictions.on('disconnect', () => {
      this._setConn('predictions', false);
      this.log('Disconnected from predictions stream', 'error');
    });
    this.sockets.predictions.on('new_prediction', (msg) => {
      const d = msg.data;
      this.log(
        `${d.symbol} → ${d.prediction_class}  conf: ${(d.confidence * 100).toFixed(1)}%`,
        'success'
      );
      window.uiManager?.addPredictionRow(d);
    });

    // /trades ───────────────────────────────────────────────────────────────
    this.sockets.trades = io(`${WS_BASE}/trades`, opts);

    this.sockets.trades.on('connect', () => {
      this._setConn('trades', true);
      this.log('Connected to trades stream', 'success');
    });
    this.sockets.trades.on('disconnect', () => {
      this._setConn('trades', false);
    });
    this.sockets.trades.on('new_trade', (msg) => {
      const d = msg.data;
      this.log(`Trade ${d.action} ${d.symbol} @ ${d.price}`, 'info');
      window.uiManager?.addTradeRow(d);
    });

    // /tasks ────────────────────────────────────────────────────────────────
    this.sockets.tasks = io(`${WS_BASE}/tasks`, opts);

    this.sockets.tasks.on('connect', () => {
      this._setConn('tasks', true);
      this.log('Connected to tasks stream', 'success');
    });
    this.sockets.tasks.on('disconnect', () => {
      this._setConn('tasks', false);
    });
    this.sockets.tasks.on('task_update', (msg) => {
      const type = msg.status === 'success' ? 'success'
                 : msg.status === 'error'   ? 'error'
                 : 'info';
      this.log(`Task ${msg.task_id.slice(0, 8)}… → ${msg.status.toUpperCase()}`, type);
      window.uiManager?.handleTaskUpdate(msg);
    });

    // /ticker ───────────────────────────────────────────────────────────────
    this.sockets.ticker = io(`${WS_BASE}/ticker`, opts);

    this.sockets.ticker.on('connect', () => {
      this._setConn('ticker', true);
      this.log('Connected to price ticker', 'success');
    });
    this.sockets.ticker.on('disconnect', () => {
      this._setConn('ticker', false);
      this.log('Ticker disconnected — will reconnect', 'warn');
    });
    this.sockets.ticker.on('price_tick', (msg) => {
      window.uiManager?.handlePriceTick(msg.data);
    });
  }

  // ── Disconnect ───────────────────────────────────────────────────────────

  disconnect() {
    Object.values(this.sockets).forEach((s) => s?.disconnect());
  }

  // ── Log helper ───────────────────────────────────────────────────────────

  log(message, type = 'info') {
    const ts   = new Date().toLocaleTimeString();
    const log  = document.getElementById('event-log');
    if (!log) return;

    const el       = document.createElement('div');
    el.className   = `ev ${type}`;
    el.textContent = `[${ts}] ${message}`;
    log.insertBefore(el, log.firstChild);

    // Keep latest 100 entries
    while (log.children.length > 100) log.removeChild(log.lastChild);
  }

  // ── Connection state helpers ─────────────────────────────────────────────

  _setConn(ns, state) {
    this._connState[ns] = state;
    this._updatePills();
  }

  _updatePills() {
    const map = {
      ticker:      'pill-ticker',
      predictions: 'pill-predictions',
      tasks:       'pill-tasks',
    };
    let total = 0;
    for (const [ns, id] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('connected', !!this._connState[ns]);
      if (this._connState[ns]) total++;
    }
    // Also update stat counters
    const statMap = { ticker: 'stat-ticker', predictions: 'stat-pred', tasks: 'stat-tasks' };
    for (const [ns, id] of Object.entries(statMap)) {
      const el = document.getElementById(id);
      if (el) el.textContent = this._connState[ns] ? '1' : '0';
    }
    const mcon = document.getElementById('metric-connections');
    if (mcon) mcon.textContent = total;
  }
}

window.socketClient = new SocketClient();
window.socketClient.connect();
