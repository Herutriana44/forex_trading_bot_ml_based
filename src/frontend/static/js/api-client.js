// REST API client for backend communication
const API_BASE_URL = `${window.location.protocol}//${window.location.host}/api/v1`;

class APIClient {
    constructor() {
        this.baseURL = API_BASE_URL;
        this.taskIds = {};
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status} ${response.statusText}`);
        }

        return await response.json();
    }

    async getModelStatus() {
        try {
            return await this.request('/model/status');
        } catch (error) {
            console.error('Error fetching model status:', error);
            throw error;
        }
    }

    async predictSymbol(symbol) {
        try {
            const response = await this.request('/predict', {
                method: 'POST',
                body: JSON.stringify({ symbol })
            });
            this.taskIds.predict = response.task_id;
            return response;
        } catch (error) {
            console.error('Error creating prediction:', error);
            throw error;
        }
    }

    async getPredictionResult(taskId) {
        try {
            return await this.request(`/predict/${taskId}`);
        } catch (error) {
            console.error('Error fetching prediction result:', error);
            throw error;
        }
    }

    async retrainModel(symbol, startDate) {
        try {
            const response = await this.request('/model/retrain', {
                method: 'POST',
                body: JSON.stringify({
                    symbol,
                    start_date: startDate
                })
            });
            this.taskIds.retrain = response.task_id;
            return response;
        } catch (error) {
            console.error('Error creating retrain task:', error);
            throw error;
        }
    }

    async getRetrainResult(taskId) {
        try {
            return await this.request(`/model/retrain/${taskId}`);
        } catch (error) {
            console.error('Error fetching retrain result:', error);
            throw error;
        }
    }

    async getTrades(limit = 50) {
        try {
            return await this.request(`/trades?limit=${limit}`);
        } catch (error) {
            console.error('Error fetching trades:', error);
            throw error;
        }
    }

    async createTrade(tradeData) {
        try {
            return await this.request('/trades', {
                method: 'POST',
                body: JSON.stringify(tradeData)
            });
        } catch (error) {
            console.error('Error creating trade:', error);
            throw error;
        }
    }

    async healthCheck() {
        try {
            const url = `${window.location.protocol}//${window.location.host}/health`;
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('Error checking health:', error);
            throw error;
        }
    }
}

// Initialize API client globally
window.apiClient = new APIClient();
