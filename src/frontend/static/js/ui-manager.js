/**
 * ui-manager.js — Dashboard UI controller
 * Handles: symbol list, live price hero, ticker bar,
 *          charts (price/confidence/doughnut), prediction &
 *          trade tables, task updates, and initial data load.
 */

class UIManager {
  constructor() {
    this.symbols         = [];          // full symbol list from API
    this.symbolMap       = {};          // symbol -> { label, group, … }
    this.latestPrices    = {};          // symbol -> price tick data
    this.selectedSymbol  = null;        // currently focused symbol
    this.predictionHistory = [];
    this.tradeHistory      = [];
    this.priceHistory      = {};        // symbol -> [{t, price}]
    this.charts            = {};
    this._pendingPredTask  = null;

    this._init();
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────

  async _init() {
    this._bindEvents();
    this._initCharts();

    // Load symbols from API, then load the rest
    try {
      const res = await window.apiClient.getSymbols();
      this.symbols = res.symbols || [];
      this.symbolMap = {};
      this.symbols.forEach(s => {
        this.symbolMap[s.symbol] = s;
        this.priceHistory[s.symbol] = [];
      });
      this._renderSymbolList();
      this._renderTickerBar();

      // Select first symbol (EURUSD=X if present, else first)
      const first = this.symbols.find(s => s.symbol === 'EURUSD=X') || this.symbols[0];
      if (first) this.selectSymbol(first.symbol);
    } catch (e) {
      window.socketClient?.log(`Failed to load symbols: ${e.message}`, 'error');
    }

    // Load model status + trade history
    try {
      const [modelStatus, tradesRes] = await Promise.all([
        window.apiClient.getModelStatus().catch(() => null),
        window.apiClient.getTrades(20).catch(() => ({ trades: [] })),
      ]);
      if (modelStatus) this._updateModelStatus(modelStatus);
      this.tradeHistory = tradesRes.trades || [];
      this._renderTradeTable();
      this._updateTradeCounts();
    } catch (e) {
      window.socketClient?.log(`Dashboard load error: ${e.message}`, 'error');
    }
  }

  _bindEvents() {
    document.getElementById('btn-predict')?.addEventListener('click', () => this._triggerPredict());
    document.getElementById('btn-retrain')?.addEventListener('click', () => this._triggerRetrain());
    document.getElementById('btn-refresh-status')?.addEventListener('click', () => this._refreshStatus());
    document.getElementById('btn-clear-log')?.addEventListener('click', () => {
      const log = document.getElementById('event-log');
      if (log) log.innerHTML = '';
    });
    document.getElementById('sym-search')?.addEventListener('input', (e) => {
      this._filterSymbolList(e.target.value.toLowerCase());
    });
  }

  // ── Symbol list (sidebar) ─────────────────────────────────────────────

  _renderSymbolList(filter = '') {
    const container = document.getElementById('sym-list');
    if (!container) return;

    // Group symbols
    const groups = {};
    this.symbols.forEach(s => {
      if (filter && !s.label.toLowerCase().includes(filter) && !s.symbol.toLowerCase().includes(filter)) return;
      if (!groups[s.group]) groups[s.group] = [];
      groups[s.group].push(s);
    });

    let html = '';
    for (const [group, items] of Object.entries(groups)) {
      html += `<div class="sym-group-label">${group}</div>`;
      items.forEach(s => {
        const tick  = this.latestPrices[s.symbol];
        const price = tick ? tick.price.toFixed(5) : '—';
        const dir   = tick ? (tick.change > 0 ? 'up' : tick.change < 0 ? 'down' : 'flat') : '';
        const arrow = tick ? (tick.change > 0 ? '▲' : tick.change < 0 ? '▼' : '') : '';
        const active = this.selectedSymbol === s.symbol ? 'active' : '';
        html += `
          <button class="sym-btn ${active}" data-sym="${s.symbol}">
            <span>${s.label}</span>
            <span class="sym-price-mini ${dir}">${arrow} ${price}</span>
          </button>`;
      });
    }
    container.innerHTML = html || '<div style="color:var(--muted);font-size:.75rem;padding:.5rem">No symbols match</div>';

    container.querySelectorAll('.sym-btn').forEach(btn => {
      btn.addEventListener('click', () => this.selectSymbol(btn.dataset.sym));
    });
  }

  _filterSymbolList(query) {
    this._renderSymbolList(query);
  }

  selectSymbol(symbol) {
    this.selectedSymbol = symbol;
    this._renderSymbolList(document.getElementById('sym-search')?.value.toLowerCase() || '');
    this._updateHeroCard(this.latestPrices[symbol] || null);
    this._updatePriceChart(symbol);
    const info = this.symbolMap[symbol];
    const label = document.getElementById('hero-sym-label');
    if (label) label.textContent = info ? `${info.label}  (${symbol})` : symbol;
  }

  // ── Ticker bar ────────────────────────────────────────────────────────

  _renderTickerBar() {
    const track = document.getElementById('ticker-track');
    if (!track) return;
    // duplicate items for seamless scroll loop
    const items = [...this.symbols, ...this.symbols];
    track.innerHTML = items.map(s => {
      const t   = this.latestPrices[s.symbol];
      const px  = t ? t.price.toFixed(5) : '—';
      const dir = t ? (t.change > 0 ? 'up' : t.change < 0 ? 'down' : 'flat') : '';
      const chg = t ? `${t.change >= 0 ? '+' : ''}${t.change_pct.toFixed(2)}%` : '';
      return `
        <span class="ticker-item" data-sym="${s.symbol}">
          <span class="sym">${s.label}</span>
          <span class="px">${px}</span>
          ${t ? `<span class="chg ${dir}">${chg}</span>` : ''}
        </span>`;
    }).join('');

    track.querySelectorAll('.ticker-item').forEach(el => {
      el.addEventListener('click', () => this.selectSymbol(el.dataset.sym));
    });
  }

  _refreshTickerItem(symbol) {
    const track = document.getElementById('ticker-track');
    if (!track) return;
    const tick = this.latestPrices[symbol];
    if (!tick) return;
    const dir = tick.change > 0 ? 'up' : tick.change < 0 ? 'down' : 'flat';
    const chg = `${tick.change >= 0 ? '+' : ''}${tick.change_pct.toFixed(2)}%`;
    track.querySelectorAll(`[data-sym="${symbol}"]`).forEach(el => {
      el.innerHTML = `
        <span class="sym">${this.symbolMap[symbol]?.label || symbol}</span>
        <span class="px">${tick.price.toFixed(5)}</span>
        <span class="chg ${dir}">${chg}</span>`;
    });
  }

  // ── Price tick handler (from Socket.IO /ticker) ───────────────────────

  handlePriceTick(data) {
    if (!data?.symbol) return;
    const sym = data.symbol;
    this.latestPrices[sym] = data;

    // Keep a rolling 60-point price history per symbol
    if (!this.priceHistory[sym]) this.priceHistory[sym] = [];
    this.priceHistory[sym].push({ t: data.timestamp, price: data.price });
    if (this.priceHistory[sym].length > 60) this.priceHistory[sym].shift();

    // Update sidebar price next to the symbol button
    const btn = document.querySelector(`#sym-list .sym-btn[data-sym="${sym}"]`);
    if (btn) {
      const dir = data.change > 0 ? 'up' : data.change < 0 ? 'down' : 'flat';
      const arrow = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '';
      const mini = btn.querySelector('.sym-price-mini');
      if (mini) {
        mini.className = `sym-price-mini ${dir}`;
        mini.textContent = `${arrow} ${data.price.toFixed(5)}`;
      }
    }

    // Update ticker bar item
    this._refreshTickerItem(sym);

    // Update hero if this is the selected symbol
    if (sym === this.selectedSymbol) {
      this._updateHeroCard(data);
      this._updatePriceChart(sym);
    }

    // Update SSE stat
    const sseEl = document.getElementById('stat-sse');
    if (sseEl && sseEl.textContent === '—') sseEl.textContent = 'ws';
  }

  // ── Hero card ─────────────────────────────────────────────────────────

  _updateHeroCard(tick) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };

    if (!tick) {
      set('hero-price', '—');
      set('hero-chg',   '—');
      set('hero-open',  '—');
      set('hero-high',  '—');
      set('hero-low',   '—');
      set('hero-prev',  '—');
      set('hero-last-update', '—');
      return;
    }

    set('hero-price', tick.price.toFixed(5));
    set('hero-open',  tick.open.toFixed(5));
    set('hero-high',  tick.high.toFixed(5));
    set('hero-low',   tick.low.toFixed(5));
    set('hero-prev',  tick.prev_close.toFixed(5));
    set('hero-last-update', new Date(tick.timestamp).toLocaleTimeString());

    const chgEl = document.getElementById('hero-chg');
    if (chgEl) {
      const dir  = tick.change > 0 ? 'up' : tick.change < 0 ? 'down' : 'flat';
      const sign = tick.change >= 0 ? '+' : '';
      chgEl.className   = `price-change ${dir}`;
      chgEl.textContent = `${sign}${tick.change.toFixed(5)} (${sign}${tick.change_pct.toFixed(2)}%)`;
    }
  }

  // ── Model status ──────────────────────────────────────────────────────

  _updateModelStatus(s) {
    const fmt = (v, pct = true) => v != null ? `${(v * 100).toFixed(1)}${pct ? '%' : ''}` : '—';
    ['sb-acc', 'sb-pre', 'sb-rec'].forEach((id, i) => {
      const el = document.getElementById(id);
      if (el) el.textContent = fmt([s.accuracy, s.precision, s.recall][i]);
    });
    const n = document.getElementById('sb-model-name');
    if (n) n.textContent = s.model_name || '—';
    const v = document.getElementById('sb-model-ver');
    if (v) v.textContent = `v${s.model_version || '—'}`;
    const t = document.getElementById('sb-model-ts');
    if (t) t.textContent = s.timestamp ? new Date(s.timestamp).toLocaleDateString() : '—';

    const acc = document.getElementById('metric-accuracy');
    if (acc) acc.textContent = fmt(s.accuracy);
  }

  async _refreshStatus() {
    try {
      const s = await window.apiClient.getModelStatus();
      this._updateModelStatus(s);
      window.socketClient?.log('Model status refreshed', 'info');
    } catch (e) {
      window.socketClient?.log(`Refresh failed: ${e.message}`, 'error');
    }
  }

  // ── Predict / Retrain ────────────────────────────────────────────────

  async _triggerPredict() {
    const symbol = this.selectedSymbol;
    if (!symbol) { window.socketClient?.log('Select a symbol first', 'warn'); return; }
    const btn = document.getElementById('btn-predict');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Predicting…';
    try {
      const res = await window.apiClient.predictSymbol(symbol);
      window.socketClient?.log(`Prediction task queued: ${res.task_id.slice(0, 8)}…`, 'info');
      this._pendingPredTask = res.task_id;
      this._pollPrediction(res.task_id);
    } catch (e) {
      window.socketClient?.log(`Predict error: ${e.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-bolt me-1"></i> Predict Selected';
    }
  }

  _pollPrediction(taskId, attempts = 0) {
    if (attempts > 30) return;
    setTimeout(async () => {
      try {
        const res = await window.apiClient.getPredictionResult(taskId);
        if (res.status === 'pending') {
          this._pollPrediction(taskId, attempts + 1);
        } else if (res.status === 'success') {
          this.addPredictionRow(res);
        } else {
          window.socketClient?.log(`Prediction failed: ${res.error}`, 'error');
        }
      } catch (_) {
        this._pollPrediction(taskId, attempts + 1);
      }
    }, 2000);
  }

  async _triggerRetrain() {
    const symbol    = this.selectedSymbol;
    const startDate = document.getElementById('start-date-input')?.value || '2019-01-01';
    if (!symbol) { window.socketClient?.log('Select a symbol first', 'warn'); return; }
    const btn = document.getElementById('btn-retrain');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Queuing…';
    try {
      const res = await window.apiClient.retrainModel(symbol, startDate);
      window.socketClient?.log(`Retrain task queued: ${res.task_id.slice(0, 8)}…`, 'info');
    } catch (e) {
      window.socketClient?.log(`Retrain error: ${e.message}`, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-sync me-1"></i> Retrain Model';
    }
  }

  // ── Prediction table ──────────────────────────────────────────────────

  addPredictionRow(pred) {
    this.predictionHistory.unshift(pred);
    if (this.predictionHistory.length > 50) this.predictionHistory.pop();
    this._renderPredTable();
    this._updateConfidenceChart();
    const el = document.getElementById('metric-predictions');
    if (el) el.textContent = this.predictionHistory.length;
    const cnt = document.getElementById('pred-count');
    if (cnt) cnt.textContent = this.predictionHistory.length;
  }

  _renderPredTable() {
    const tbody = document.getElementById('predictions-table');
    if (!tbody) return;
    if (!this.predictionHistory.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3" style="color:var(--muted)">No predictions yet</td></tr>';
      return;
    }
    tbody.innerHTML = this.predictionHistory.map(p => {
      const ts    = new Date(p.timestamp).toLocaleTimeString();
      const cls   = p.prediction_class || (p.prediction === 1 ? 'BUY' : 'SELL');
      const badge = p.prediction === 1 ? 'badge-buy' : 'badge-sell';
      const conf  = ((p.confidence || 0) * 100).toFixed(1);
      const px    = p.current_price != null ? p.current_price.toFixed(5) : '—';
      return `<tr>
        <td style="color:var(--muted)">${ts}</td>
        <td style="font-weight:600">${p.symbol}</td>
        <td><span class="${badge}">${cls}</span></td>
        <td style="font-family:var(--font-mono)">${conf}%</td>
        <td style="font-family:var(--font-mono)">${px}</td>
      </tr>`;
    }).join('');
  }

  // ── Trade table ───────────────────────────────────────────────────────

  addTradeRow(trade) {
    this.tradeHistory.unshift(trade);
    if (this.tradeHistory.length > 50) this.tradeHistory.pop();
    this._renderTradeTable();
    this._updateTradeCounts();
    this._updateTradesChart();
  }

  _renderTradeTable() {
    const tbody = document.getElementById('trades-table');
    if (!tbody) return;
    if (!this.tradeHistory.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-3" style="color:var(--muted)">No trades yet</td></tr>';
      return;
    }
    tbody.innerHTML = this.tradeHistory.map(t => {
      const ts    = new Date(t.timestamp).toLocaleTimeString();
      const badge = t.action === 'BUY' ? 'badge-buy' : 'badge-sell';
      return `<tr>
        <td style="color:var(--muted)">${ts}</td>
        <td style="font-weight:600">${t.symbol}</td>
        <td><span class="${badge}">${t.action}</span></td>
        <td style="font-family:var(--font-mono)">${t.price.toFixed(5)}</td>
        <td>${t.quantity || 1}</td>
        <td style="color:var(--muted)">${t.notes || '—'}</td>
      </tr>`;
    }).join('');
  }

  _updateTradeCounts() {
    const el  = document.getElementById('metric-trades');
    const cnt = document.getElementById('trade-count');
    if (el)  el.textContent  = this.tradeHistory.length;
    if (cnt) cnt.textContent = this.tradeHistory.length;
  }

  // ── Task updates ──────────────────────────────────────────────────────

  handleTaskUpdate(msg) {
    if (msg.status === 'success' && msg.result?.prediction != null) {
      this.addPredictionRow(msg.result);
    }
    if (msg.status === 'success') {
      this._refreshStatus();
    }
  }

  // ── Charts ────────────────────────────────────────────────────────────

  _chartDefaults() {
    return {
      color: 'rgba(226,232,240,.6)',
      plugins: {
        legend: { labels: { color: 'rgba(226,232,240,.55)', font: { size: 11 } } },
        tooltip: { backgroundColor: 'rgba(14,24,41,.95)', titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
      },
    };
  }

  _initCharts() {
    this._initPriceChart();
    this._initConfidenceChart();
    this._initTradesChart();
  }

  // Price mini-chart (hero)
  _initPriceChart() {
    const ctx = document.getElementById('priceChart')?.getContext('2d');
    if (!ctx) return;
    this.charts.price = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Price',
          data: [],
          borderColor: 'rgba(59,130,246,1)',
          backgroundColor: 'rgba(59,130,246,.08)',
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        ...this._chartDefaults(),
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { display: false },
          y: {
            ticks: { color: 'rgba(226,232,240,.45)', font: { size: 10 } },
            grid:  { color: 'rgba(255,255,255,.04)' },
          },
        },
        plugins: { legend: { display: false }, tooltip: { mode: 'index', intersect: false } },
        animation: { duration: 250 },
      },
    });
  }

  _updatePriceChart(symbol) {
    if (!this.charts.price) return;
    const hist = this.priceHistory[symbol] || [];
    this.charts.price.data.labels   = hist.map(h => new Date(h.t).toLocaleTimeString());
    this.charts.price.data.datasets[0].data = hist.map(h => h.price);
    this.charts.price.data.datasets[0].label = symbol;
    this.charts.price.update('none');
  }

  // Confidence trend
  _initConfidenceChart() {
    const ctx = document.getElementById('confidenceChart')?.getContext('2d');
    if (!ctx) return;
    this.charts.confidence = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Confidence',
          data: [],
          borderColor: 'rgba(59,130,246,1)',
          backgroundColor: 'rgba(59,130,246,.1)',
          borderWidth: 2,
          tension: 0.35,
          fill: true,
          pointRadius: 3,
          pointBackgroundColor: 'rgba(59,130,246,1)',
        }],
      },
      options: {
        ...this._chartDefaults(),
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            min: 0, max: 1,
            ticks: { color: 'rgba(226,232,240,.45)', font: { size: 10 }, callback: v => `${(v*100).toFixed(0)}%` },
            grid:  { color: 'rgba(255,255,255,.04)' },
          },
          x: {
            ticks: { color: 'rgba(226,232,240,.45)', font: { size: 10 }, maxRotation: 0 },
            grid:  { color: 'rgba(255,255,255,.04)' },
          },
        },
        plugins: { legend: { display: false } },
      },
    });
  }

  _updateConfidenceChart() {
    if (!this.charts.confidence) return;
    const last20 = [...this.predictionHistory].slice(0, 20).reverse();
    this.charts.confidence.data.labels = last20.map(p =>
      `${p.symbol} ${new Date(p.timestamp).toLocaleTimeString()}`
    );
    this.charts.confidence.data.datasets[0].data = last20.map(p => p.confidence);
    this.charts.confidence.update();
  }

  // Trades doughnut
  _initTradesChart() {
    const ctx = document.getElementById('tradesChart')?.getContext('2d');
    if (!ctx) return;
    this.charts.trades = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['BUY', 'SELL'],
        datasets: [{
          data: [0, 0],
          backgroundColor: ['rgba(16,185,129,.8)', 'rgba(239,68,68,.8)'],
          borderColor:      ['rgba(16,185,129,1)',  'rgba(239,68,68,1)'],
          borderWidth: 2,
        }],
      },
      options: {
        ...this._chartDefaults(),
        responsive: true,
        maintainAspectRatio: false,
        cutout: '65%',
        plugins: {
          legend: { position: 'bottom', labels: { color: 'rgba(226,232,240,.55)', font: { size: 11 } } },
        },
      },
    });
  }

  _updateTradesChart() {
    if (!this.charts.trades) return;
    const buy  = this.tradeHistory.filter(t => t.action === 'BUY').length;
    const sell = this.tradeHistory.filter(t => t.action === 'SELL').length;
    this.charts.trades.data.datasets[0].data = [buy, sell];
    this.charts.trades.update();
  }
}

// Bootstrap — wait for DOM + dependencies
window.addEventListener('DOMContentLoaded', () => {
  window.uiManager = new UIManager();
});
