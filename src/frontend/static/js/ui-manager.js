// UI Manager for handling DOM updates and chart management
class UIManager {
    constructor() {
        this.charts = {};
        this.predictionHistory = [];
        this.tradeHistory = [];
        this.taskStatuses = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initCharts();
        this.loadInitialData();
    }

    setupEventListeners() {
        document.getElementById('btn-predict').addEventListener('click', () => this.handlePredict());
        document.getElementById('btn-retrain').addEventListener('click', () => this.handleRetrain());
        document.getElementById('btn-refresh-status').addEventListener('click', () => this.loadInitialData());
    }

    async handlePredict() {
        const symbol = document.getElementById('symbol-input').value;
        const btn = document.getElementById('btn-predict');

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

        try {
            const response = await window.apiClient.predictSymbol(symbol);
            window.socketClient.logEvent(`Prediction task created: ${response.task_id}`, 'success');
        } catch (error) {
            window.socketClient.logEvent(`Prediction failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Trigger Prediction';
        }
    }

    async handleRetrain() {
        const symbol = document.getElementById('symbol-input').value;
        const startDate = document.getElementById('start-date-input').value;
        const btn = document.getElementById('btn-retrain');

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

        try {
            const response = await window.apiClient.retrainModel(symbol, startDate);
            window.socketClient.logEvent(`Retrain task created: ${response.task_id}`, 'success');
        } catch (error) {
            window.socketClient.logEvent(`Retrain failed: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sync"></i> Retrain Model';
        }
    }

    async loadInitialData() {
        try {
            // Load model status
            const modelStatus = await window.apiClient.getModelStatus();
            this.updateModelStatus(modelStatus);

            // Load trade history
            const tradesResponse = await window.apiClient.getTrades(10);
            this.tradeHistory = tradesResponse.trades || [];
            this.renderTradeHistory();

            // Update metrics
            document.getElementById('metric-predictions').textContent = this.predictionHistory.length;
            document.getElementById('metric-trades').textContent = this.tradeHistory.length;

            window.socketClient.logEvent('Dashboard data loaded', 'success');
        } catch (error) {
            window.socketClient.logEvent(`Error loading data: ${error.message}`, 'error');
        }
    }

    updateModelStatus(status) {
        document.getElementById('model-name').textContent = status.model_name || 'Unknown';
        document.getElementById('model-version').textContent = status.model_version || '--';
        document.getElementById('model-accuracy').textContent =
            status.accuracy ? `${(status.accuracy * 100).toFixed(1)}%` : '--';
        document.getElementById('model-precision').textContent =
            status.precision ? `${(status.precision * 100).toFixed(1)}%` : '--';
        document.getElementById('model-recall').textContent =
            status.recall ? `${(status.recall * 100).toFixed(1)}%` : '--';
        document.getElementById('model-timestamp').textContent =
            status.timestamp ? new Date(status.timestamp).toLocaleString() : '--';
    }

    addPredictionRow(prediction) {
        this.predictionHistory.unshift(prediction);
        this.predictionHistory = this.predictionHistory.slice(0, 20);

        // Update chart
        if (this.charts.confidence) {
            this.updateConfidenceChart();
        }

        // Update table
        this.renderPredictionHistory();

        // Update metric
        document.getElementById('metric-predictions').textContent = this.predictionHistory.length;
    }

    addTradeRow(trade) {
        this.tradeHistory.unshift(trade);
        this.tradeHistory = this.tradeHistory.slice(0, 20);

        // Update chart
        if (this.charts.trades) {
            this.updateTradesChart();
        }

        // Update table
        this.renderTradeHistory();

        // Update metric
        document.getElementById('metric-trades').textContent = this.tradeHistory.length;
    }

    updateTaskStatus(taskId, status) {
        this.taskStatuses[taskId] = status;
    }

    renderPredictionHistory() {
        const tbody = document.getElementById('predictions-table');

        if (this.predictionHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No predictions yet</td></tr>';
            return;
        }

        tbody.innerHTML = this.predictionHistory.map(pred => {
            const timestamp = new Date(pred.timestamp).toLocaleTimeString();
            const predictionClass = pred.prediction_class || (pred.prediction === 1 ? 'BUY' : 'SELL');
            const confidence = (pred.confidence * 100).toFixed(1);
            const badgeClass = pred.prediction === 1 ? 'badge-success' : 'badge-danger';

            return `
                <tr>
                    <td>${timestamp}</td>
                    <td>${pred.symbol}</td>
                    <td><span class="badge ${badgeClass}">${predictionClass}</span></td>
                    <td>${confidence}%</td>
                    <td>${pred.current_price ? pred.current_price.toFixed(5) : 'N/A'}</td>
                </tr>
            `;
        }).join('');
    }

    renderTradeHistory() {
        const tbody = document.getElementById('trades-table');

        if (this.tradeHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No trades yet</td></tr>';
            return;
        }

        tbody.innerHTML = this.tradeHistory.map(trade => {
            const timestamp = new Date(trade.timestamp).toLocaleTimeString();
            const actionBadge = trade.action === 'BUY'
                ? '<span class="badge badge-success">BUY</span>'
                : '<span class="badge badge-danger">SELL</span>';

            return `
                <tr>
                    <td>${timestamp}</td>
                    <td>${trade.symbol}</td>
                    <td>${actionBadge}</td>
                    <td>${trade.price.toFixed(5)}</td>
                    <td>${trade.quantity || 1}</td>
                    <td>${trade.notes || '--'}</td>
                </tr>
            `;
        }).join('');
    }

    initCharts() {
        this.initConfidenceChart();
        this.initTradesChart();
    }

    initConfidenceChart() {
        const ctx = document.getElementById('confidenceChart').getContext('2d');
        this.charts.confidence = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Prediction Confidence',
                    data: [],
                    borderColor: 'rgba(37, 99, 235, 1)',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true, labels: { color: 'rgba(255, 255, 255, 0.6)' } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 1,
                        ticks: { color: 'rgba(255, 255, 255, 0.6)' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    },
                    x: {
                        ticks: { color: 'rgba(255, 255, 255, 0.6)' },
                        grid: { color: 'rgba(255, 255, 255, 0.05)' }
                    }
                }
            }
        });
        this.updateConfidenceChart();
    }

    updateConfidenceChart() {
        if (!this.charts.confidence) return;

        const labels = this.predictionHistory.map((_, i) => `${i}`).reverse();
        const data = this.predictionHistory.map(p => p.confidence).reverse();

        this.charts.confidence.data.labels = labels;
        this.charts.confidence.data.datasets[0].data = data;
        this.charts.confidence.update();
    }

    initTradesChart() {
        const ctx = document.getElementById('tradesChart').getContext('2d');
        this.charts.trades = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['BUY', 'SELL'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(239, 68, 68, 0.8)'
                    ],
                    borderColor: [
                        'rgba(16, 185, 129, 1)',
                        'rgba(239, 68, 68, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: { color: 'rgba(255, 255, 255, 0.6)' }
                    }
                }
            }
        });
        this.updateTradesChart();
    }

    updateTradesChart() {
        if (!this.charts.trades) return;

        const buyCount = this.tradeHistory.filter(t => t.action === 'BUY').length;
        const sellCount = this.tradeHistory.filter(t => t.action === 'SELL').length;

        this.charts.trades.data.datasets[0].data = [buyCount, sellCount];
        this.charts.trades.update();
    }
}

// Initialize UI Manager globally
window.uiManager = new UIManager();
