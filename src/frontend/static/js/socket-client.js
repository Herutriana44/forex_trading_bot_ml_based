// WebSocket client for real-time updates
const API_BASE_URL = `${window.location.protocol}//${window.location.host}`;

class SocketClient {
    constructor() {
        this.sockets = {
            predictions: null,
            trades: null,
            tasks: null
        };
        this.connectionStats = {
            predictions: 0,
            trades: 0,
            tasks: 0
        };
    }

    connect() {
        // Connect to predictions namespace
        this.sockets.predictions = io(`${API_BASE_URL}/predictions`, {
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: 5
        });

        this.sockets.predictions.on('connect', () => {
            this.logEvent('Connected to predictions stream', 'success');
            this.connectionStats.predictions++;
            this.updateConnectionStats();
        });

        this.sockets.predictions.on('disconnect', () => {
            this.logEvent('Disconnected from predictions stream', 'error');
        });

        this.sockets.predictions.on('new_prediction', (data) => {
            this.logEvent(`New prediction: ${data.data.prediction_class} (${(data.data.confidence * 100).toFixed(1)}%)`, 'success');
            if (window.uiManager) {
                window.uiManager.addPredictionRow(data.data);
            }
        });

        // Connect to trades namespace
        this.sockets.trades = io(`${API_BASE_URL}/trades`, {
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: 5
        });

        this.sockets.trades.on('connect', () => {
            this.logEvent('Connected to trades stream', 'success');
            this.connectionStats.trades++;
            this.updateConnectionStats();
        });

        this.sockets.trades.on('disconnect', () => {
            this.logEvent('Disconnected from trades stream', 'error');
        });

        this.sockets.trades.on('new_trade', (data) => {
            this.logEvent(`New trade: ${data.data.action} ${data.data.symbol} @ ${data.data.price}`, 'success');
            if (window.uiManager) {
                window.uiManager.addTradeRow(data.data);
            }
        });

        // Connect to tasks namespace
        this.sockets.tasks = io(`${API_BASE_URL}/tasks`, {
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: 5
        });

        this.sockets.tasks.on('connect', () => {
            this.logEvent('Connected to tasks stream', 'success');
            this.connectionStats.tasks++;
            this.updateConnectionStats();
        });

        this.sockets.tasks.on('disconnect', () => {
            this.logEvent('Disconnected from tasks stream', 'error');
        });

        this.sockets.tasks.on('task_update', (data) => {
            const status = data.status.toUpperCase();
            const color = data.status === 'success' ? 'success' : data.status === 'error' ? 'error' : 'info';
            this.logEvent(`Task ${data.task_id}: ${status}`, color);
            if (window.uiManager) {
                window.uiManager.updateTaskStatus(data.task_id, data.status);
            }
        });
    }

    disconnect() {
        Object.keys(this.sockets).forEach(key => {
            if (this.sockets[key]) {
                this.sockets[key].disconnect();
            }
        });
    }

    logEvent(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const eventLog = document.getElementById('event-log');
        if (!eventLog) return;

        const eventItem = document.createElement('div');
        eventItem.className = `event-item ${type}`;
        eventItem.textContent = `[${timestamp}] ● ${message}`;
        eventLog.insertBefore(eventItem, eventLog.firstChild);

        // Keep only last 50 items
        while (eventLog.children.length > 50) {
            eventLog.removeChild(eventLog.lastChild);
        }
    }

    updateConnectionStats() {
        document.getElementById('ws-predictions').textContent = this.connectionStats.predictions;
        document.getElementById('ws-trades').textContent = this.connectionStats.trades;
        document.getElementById('ws-tasks').textContent = this.connectionStats.tasks;
    }
}

// Initialize socket client globally
window.socketClient = new SocketClient();
window.socketClient.connect();
