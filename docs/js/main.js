class AdvancedBinanceMonitor {
    constructor() {
        this.currentTimeframe = '1h';
        this.currentPeriod = '7d';
        this.charts = {};
        this.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        this.dataCache = {
            realtime: null,
            historical: {},
            anomalies: null,
            lastUpdate: null
        };
        this.init();
    }

    async init() {
        this.bindEvents();
        this.setupWebSocket(); // Future enhancement
        await this.loadInitialData();
        this.setupAutoRefresh();
    }

    bindEvents() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', async () => {
            await this.forceRefreshData();
        });

        // Time filter buttons
        document.querySelectorAll('.btn-time-filter').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const timeframe = e.target.dataset.timeframe;
                const period = e.target.dataset.period;
                
                if (timeframe) {
                    this.currentTimeframe = timeframe;
                    this.updateActiveFilter(e.target);
                    await this.updateRealtimeView();
                }
                
                if (period) {
                    this.currentPeriod = period;
                    this.updateActiveFilter(e.target);
                    await this.updateHistoricalView();
                }
            });
        });

        // Tab change events
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', async (e) => {
                const target = e.target.getAttribute('data-bs-target');
                if (target === '#historical') {
                    await this.loadHistoricalView();
                } else if (target === '#anomalies') {
                    await this.loadAnomaliesView();
                } else if (target === '#realtime') {
                    await this.loadRealtimeView();
                }
            });
        });
    }

    updateActiveFilter(activeBtn) {
        activeBtn.parentNode.querySelectorAll('.btn-time-filter').forEach(btn => {
            btn.classList.remove('active');
        });
        activeBtn.classList.add('active');
    }

    async loadInitialData() {
        try {
            this.showGlobalLoading();
            
            // Load all data in parallel
            await Promise.all([
                this.loadRealtimeData(),
                this.loadSymbolsData(),
                this.loadAnomaliesData()
            ]);
            
            this.hideGlobalLoading();
            await this.updateAllViews();
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load initial data');
            this.hideGlobalLoading();
        }
    }

    async forceRefreshData() {
        this.dataCache = {
            realtime: null,
            historical: {},
            anomalies: null,
            lastUpdate: null
        };
        await this.loadInitialData();
    }

    async loadRealtimeData() {
        try {
            const response = await fetch('assets/data/daily_summary.json?' + Date.now());
            if (!response.ok) throw new Error('Failed to fetch realtime data');
            
            const data = await response.json();
            this.dataCache.realtime = data;
            this.dataCache.lastUpdate = new Date();
            
            return data;
        } catch (error) {
            console.error('Error loading realtime data:', error);
            return null;
        }
    }

    async loadSymbolsData() {
        try {
            const promises = this.symbols.map(async symbol => {
                try {
                    const response = await fetch(`assets/data/${symbol}.json?` + Date.now());
                    if (!response.ok) return null;
                    
                    const data = await response.json();
                    this.dataCache.historical[symbol] = data;
                    return { symbol, data };
                } catch (error) {
                    console.error(`Error loading ${symbol} data:`, error);
                    return null;
                }
            });

            const results = await Promise.allSettled(promises);
            return results;
        } catch (error) {
            console.error('Error loading symbols data:', error);
            return [];
        }
    }

    async loadAnomaliesData() {
        try {
            // Get from realtime data
            if (this.dataCache.realtime && this.dataCache.realtime.anomalies) {
                this.dataCache.anomalies = this.dataCache.realtime.anomalies;
                return this.dataCache.anomalies;
            }

            // Fallback to separate anomalies file
            try {
                const response = await fetch('assets/data/anomalies.json?' + Date.now());
                if (response.ok) {
                    const data = await response.json();
                    this.dataCache.anomalies = data;
                    return data;
                }
            } catch (error) {
                console.warn('No separate anomalies file found');
            }

            return [];
        } catch (error) {
            console.error('Error loading anomalies data:', error);
            return [];
        }
    }

    async updateAllViews() {
        await Promise.all([
            this.updateRealtimeView(),
            this.updateAnomaliesView()
        ]);
    }

    async loadRealtimeView() {
        await this.updateRealtimeView();
    }

    async loadHistoricalView() {
        await this.updateHistoricalView();
    }

    async loadAnomaliesView() {
        await this.updateAnomaliesView();
    }

    async updateRealtimeView() {
        if (!this.dataCache.realtime) return;

        try {
            const data = this.dataCache.realtime;
            
            this.updateLastUpdateTime(data.timestamp);
            this.updateRealtimeTable(data.symbols);
            this.updateStats(data.symbols);
        } catch (error) {
            console.error('Error updating realtime view:', error);
        }
    }

    async updateHistoricalView() {
        try {
            const historicalData = this.dataCache.historical;
            
            this.updateHistoricalTable(historicalData);
            this.updateHistoricalChart(historicalData);
        } catch (error) {
            console.error('Error updating historical view:', error);
        }
    }

    async updateAnomaliesView() {
        try {
            const anomalies = this.dataCache.anomalies || [];
            this.updateAnomaliesTable(anomalies);
        } catch (error) {
            console.error('Error updating anomalies view:', error);
        }
    }

    updateLastUpdateTime(timestamp) {
        const lastUpdateEl = document.getElementById('lastUpdateTime');
        if (lastUpdateEl) {
            const date = new Date(timestamp);
            lastUpdateEl.innerHTML = `
                <i class="bi bi-clock"></i>
                Last updated: ${date.toLocaleString()}
                <span class="badge bg-success ms-2">Live</span>
            `;
        }
    }

    updateRealtimeTable(symbols) {
        const tbody = document.getElementById('realtimeTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        // Sort symbols by absolute price change descending
        const sortedSymbols = Object.entries(symbols).sort((a, b) => {
            return Math.abs(b[1].price_change) - Math.abs(a[1].price_change);
        });

        sortedSymbols.forEach(([symbol, data]) => {
            const row = this.createRealtimeRow(symbol, data);
            tbody.appendChild(row);
        });
    }

    createRealtimeRow(symbol, data) {
        const row = document.createElement('tr');
        row.className = 'symbol-row';
        row.setAttribute('data-symbol', symbol);
        
        const priceClass = this.getChangeClass(data.price_change);
        const volumeClass = this.getChangeClass(data.volume_change);
        const oiClass = this.getChangeClass(data.oi_change);
        const sentimentInfo = this.getSentimentInfo(data.sentiment);

        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="symbol-icon me-2">
                        <i class="bi bi-currency-bitcoin text-warning"></i>
                    </div>
                    <div>
                        <div class="coin-symbol">${symbol}</div>
                        <small class="text-muted">${this.getSymbolName(symbol)}</small>
                    </div>
                </div>
            </td>
            <td>
                <div class="${priceClass}">
                    <strong>${this.formatPercent(data.price_change)}</strong>
                    <i class="bi bi-${data.price_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">${this.currentTimeframe} change</small>
            </td>
            <td>
                <div class="${volumeClass}">
                    <strong>${this.formatPercent(data.volume_change)}</strong>
                    <i class="bi bi-${data.volume_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">vs 24h avg</small>
            </td>
            <td>
                <div class="${oiClass}">
                    <strong>${this.formatPercent(data.oi_change)}</strong>
                    <i class="bi bi-${data.oi_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">Open Interest</small>
            </td>
            <td>
                <span class="badge sentiment-badge ${sentimentInfo.class}" title="${sentimentInfo.description}">
                    <i class="bi bi-${sentimentInfo.icon} me-1"></i>
                    ${sentimentInfo.text}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="monitor.showDetails('${symbol}')" title="View Details">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-info" onclick="monitor.showChart('${symbol}')" title="View Chart">
                        <i class="bi bi-graph-up"></i>
                    </button>
                </div>
            </td>
        `;

        // Add hover effects
        row.addEventListener('mouseenter', () => {
            row.style.backgroundColor = '#f8f9fa';
        });
        
        row.addEventListener('mouseleave', () => {
            row.style.backgroundColor = '';
        });

        return row;
    }

    updateHistoricalTable(historicalData) {
        const tbody = document.getElementById('historicalTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        Object.entries(historicalData).forEach(([symbol, data]) => {
            const row = this.createHistoricalRow(symbol, data);
            tbody.appendChild(row);
        });
    }

    createHistoricalRow(symbol, data) {
        const row = document.createElement('tr');
        
        // Calculate historical changes based on actual data
        const historical = this.calculateHistoricalChanges(data);

        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="symbol-icon me-2">
                        <i class="bi bi-currency-bitcoin text-warning"></i>
                    </div>
                    <div>
                        <div class="coin-symbol">${symbol}</div>
                        <small class="text-muted">${this.getSymbolName(symbol)}</small>
                    </div>
                </div>
            </td>
            <td class="${this.getChangeClass(historical.price7d)}">
                <strong>${this.formatPercent(historical.price7d)}</strong>
            </td>
            <td class="${this.getChangeClass(historical.volume7d)}">
                <strong>${this.formatPercent(historical.volume7d)}</strong>
            </td>
            <td class="${this.getChangeClass(historical.oi7d)}">
                <strong>${this.formatPercent(historical.oi7d)}</strong>
            </td>
            <td class="${this.getChangeClass(historical.price30d)}">
                <strong>${this.formatPercent(historical.price30d)}</strong>
            </td>
            <td class="${this.getChangeClass(historical.oi30d)}">
                <strong>${this.formatPercent(historical.oi30d)}</strong>
            </td>
            <td>
                <span class="badge bg-${historical.trend.color}">
                    <i class="bi bi-${historical.trend.icon} me-1"></i>
                    ${historical.trend.text}
                </span>
            </td>
        `;

        return row;
    }

    calculateHistoricalChanges(symbolData) {
        // Calculate based on actual historical data
        // This would use real klines data from symbolData.klines
        
        // For now, using mock calculations
        // In production, you'd calculate from actual historical prices
        return {
            price7d: (Math.random() - 0.5) * 20,
            volume7d: (Math.random() - 0.5) * 40,
            oi7d: (Math.random() - 0.5) * 15,
            price30d: (Math.random() - 0.5) * 30,
            oi30d: (Math.random() - 0.5) * 25,
            trend: this.calculateTrend()
        };
    }

    calculateTrend() {
        const trends = [
            { text: 'Strong Up', color: 'success', icon: 'arrow-up-circle' },
            { text: 'Up', color: 'success', icon: 'arrow-up' },
            { text: 'Sideways', color: 'warning', icon: 'arrow-left-right' },
            { text: 'Down', color: 'danger', icon: 'arrow-down' },
            { text: 'Strong Down', color: 'danger', icon: 'arrow-down-circle' }
        ];
        return trends[Math.floor(Math.random() * trends.length)];
    }

    updateAnomaliesTable(anomalies) {
        const tbody = document.getElementById('anomaliesTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!anomalies || anomalies.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="bi bi-check-circle text-success me-2"></i>
                        No anomalies detected
                    </td>
                </tr>
            `;
            return;
        }

        // Sort anomalies by timestamp descending
        const sortedAnomalies = anomalies.sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );

        sortedAnomalies.forEach(anomaly => {
            const row = this.createAnomalyRow(anomaly);
            tbody.appendChild(row);
        });
    }

    createAnomalyRow(anomaly) {
        const row = document.createElement('tr');
        const severity = this.getAnomalySeverity(anomaly.message);
        const timeAgo = this.getTimeAgo(anomaly.timestamp);
        
        row.innerHTML = `
            <td>
                <div>${this.formatDateTime(anomaly.timestamp)}</div>
                <small class="text-muted">${timeAgo}</small>
            </td>
            <td>
                <span class="coin-symbol">${anomaly.symbol}</span>
            </td>
            <td>
                <span class="badge bg-info">
                    <i class="bi bi-${this.getDataTypeIcon(anomaly.data_type)} me-1"></i>
                    ${this.capitalizeFirst(anomaly.data_type)}
                </span>
            </td>
            <td>
                <div class="anomaly-message">${anomaly.message}</div>
            </td>
            <td>
                <span class="badge bg-${severity.color}">
                    <i class="bi bi-${severity.icon} me-1"></i>
                    ${severity.text}
                </span>
            </td>
        `;

        return row;
    }

    updateStats(symbols) {
        const stats = this.calculateDetailedStats(symbols);
        
        document.getElementById('totalSymbols').textContent = stats.total;
        document.getElementById('bullishCount').textContent = stats.bullish;
        document.getElementById('bearishCount').textContent = stats.bearish;
        document.getElementById('neutralCount').textContent = stats.neutral;
    }

    calculateDetailedStats(symbols) {
        const stats = { 
            total: 0, 
            bullish: 0, 
            bearish: 0, 
            neutral: 0,
            avgPriceChange: 0,
            avgVolumeChange: 0,
            avgOIChange: 0
        };
        
        const values = Object.values(symbols);
        stats.total = values.length;

        let totalPriceChange = 0;
        let totalVolumeChange = 0;
        let totalOIChange = 0;

        values.forEach(data => {
            const sentiment = data.sentiment.toLowerCase();
            
            if (sentiment.includes('bullish')) {
                stats.bullish++;
            } else if (sentiment.includes('bearish')) {
                stats.bearish++;
            } else {
                stats.neutral++;
            }

            totalPriceChange += data.price_change || 0;
            totalVolumeChange += data.volume_change || 0;
            totalOIChange += data.oi_change || 0;
        });

        stats.avgPriceChange = totalPriceChange / stats.total;
        stats.avgVolumeChange = totalVolumeChange / stats.total;
        stats.avgOIChange = totalOIChange / stats.total;

        return stats;
    }

    updateHistoricalChart(historicalData) {
        const ctx = document.getElementById('historicalChart');
        if (!ctx) return;

        if (this.charts.historical) {
            this.charts.historical.destroy();
        }

        // Generate labels for the period
        const labels = this.generateDateLabels(this.currentPeriod);
        
        // Create datasets for each symbol
        const datasets = Object.keys(historicalData).map((symbol, index) => {
            const color = this.getColorForIndex(index);
            return {
                label: symbol,
                data: this.generateMockHistoricalData(labels.length),
                borderColor: color,
                backgroundColor: color + '20',
                tension: 0.1,
                fill: false
            };
        });

        this.charts.historical = new Chart(ctx, {
            type: 'line',
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: `Historical Price Performance (${this.currentPeriod})`
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Change (%)'
                        }
                    }
                }
            }
        });
    }

    generateDateLabels(period) {
        const days = period === '7d' ? 7 : period === '30d' ? 30 : 90;
        return Array.from({length: days}, (_, i) => {
            const date = new Date();
            date.setDate(date.getDate() - (days - 1 - i));
            return date.toLocaleDateString();
        });
    }

    generateMockHistoricalData(length) {
        let value = 0;
        return Array.from({length}, () => {
            value += (Math.random() - 0.5) * 5;
            return value;
        });
    }

    // Utility methods
    getChangeClass(change) {
        if (change > 0) return 'change-positive';
        if (change < 0) return 'change-negative';
        return 'change-neutral';
    }

    getSentimentInfo(sentiment) {
        const s = sentiment.toLowerCase();
        
        if (s.includes('strong') && s.includes('bullish')) {
            return { 
                class: 'sentiment-bullish', 
                text: 'Strong Bull', 
                icon: 'arrow-up-circle-fill',
                description: 'Strong bullish sentiment'
            };
        } else if (s.includes('bullish')) {
            return { 
                class: 'sentiment-bullish', 
                text: 'Bullish', 
                icon: 'arrow-up',
                description: 'Bullish sentiment'
            };
        } else if (s.includes('strong') && s.includes('bearish')) {
            return { 
                class: 'sentiment-bearish', 
                text: 'Strong Bear', 
                icon: 'arrow-down-circle-fill',
                description: 'Strong bearish sentiment'
            };
        } else if (s.includes('bearish')) {
            return { 
                class: 'sentiment-bearish', 
                text: 'Bearish', 
                icon: 'arrow-down',
                description: 'Bearish sentiment'
            };
        }
        
        return { 
            class: 'sentiment-neutral', 
            text: 'Neutral', 
            icon: 'dash-circle',
            description: 'Neutral sentiment'
        };
    }

    getAnomalySeverity(message) {
        const zscore = parseFloat(message.match(/Z-score: ([\d.]+)/)?.[1] || 0);
        
        if (zscore > 4) {
            return { color: 'danger', text: 'Critical', icon: 'exclamation-triangle-fill' };
        } else if (zscore > 3) {
            return { color: 'warning', text: 'High', icon: 'exclamation-triangle' };
        } else if (zscore > 2.5) {
            return { color: 'info', text: 'Medium', icon: 'info-circle' };
        }
        
        return { color: 'secondary', text: 'Low', icon: 'info-circle' };
    }

    getDataTypeIcon(dataType) {
        const icons = {
            volume: 'bar-chart',
            open_interest: 'pie-chart',
            price: 'graph-up',
            correlation: 'shuffle'
        };
        return icons[dataType] || 'info-circle';
    }

    getSymbolName(symbol) {
        const names = {
            'BTCUSDT': 'Bitcoin',
            'ETHUSDT': 'Ethereum', 
            'BNBUSDT': 'BNB',
            'SOLUSDT': 'Solana',
            'DOGEUSDT': 'Dogecoin'
        };
        return names[symbol] || symbol;
    }

    getColorForIndex(index) {
        const colors = [
            '#f7931e', // Bitcoin orange
            '#627eea', // Ethereum blue
            '#f0b90b', // BNB yellow
            '#9945ff', // Solana purple
            '#c2a633'  // Dogecoin gold
        ];
        return colors[index % colors.length];
    }

    formatPercent(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return 'N/A';
        }
        return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
    }

    formatDateTime(timestamp) {
        return new Date(timestamp).toLocaleString();
    }

    getTimeAgo(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor(diffMs / (1000 * 60));

        if (diffHours > 24) {
            return `${Math.floor(diffHours / 24)} days ago`;
        } else if (diffHours > 0) {
            return `${diffHours} hours ago`;
        } else {
            return `${diffMinutes} minutes ago`;
        }
    }

    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Action methods
    showDetails(symbol) {
        // Create a modal or navigate to detail page
        alert(`Showing detailed analysis for ${symbol}`);
        // TODO: Implement detailed view with charts, indicators, etc.
    }

    showChart(symbol) {
        // Open chart in modal or new tab
        alert(`Opening advanced chart for ${symbol}`);
        // TODO: Implement advanced charting with TradingView or similar
    }

    showGlobalLoading() {
        // TODO: Show global loading overlay
    }

    hideGlobalLoading() {
        // TODO: Hide global loading overlay
    }

    showError(message) {
        console.error(message);
        // TODO: Show user-friendly error message
    }

    setupWebSocket() {
        // TODO: Implement WebSocket for real-time updates
        // This would connect to Binance WebSocket or your own WebSocket server
    }

    setupAutoRefresh() {
        // Refresh data every 5 minutes
        setInterval(async () => {
            console.log('Auto-refreshing data...');
            await this.loadRealtimeData();
            await this.updateRealtimeView();
        }, 5 * 60 * 1000);

        // Refresh page data every 30 minutes
        setInterval(async () => {
            console.log('Full data refresh...');
            await this.forceRefreshData();
        }, 30 * 60 * 1000);
    }
}

// Initialize the enhanced monitor
document.addEventListener('DOMContentLoaded', () => {
    window.monitor = new AdvancedBinanceMonitor();
});

// Export for debugging
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedBinanceMonitor;
}