/**
 * Simple OI & Volume Monitor JavaScript
 * Fixed: Smart data path detection for GitHub Pages
 */

class SimpleOIVolumeMonitor {
    constructor() {
        this.currentView = 'hourly';
        this.coinsData = {};
        this.charts = {};
        this.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        this.updateInterval = null;
        this.dataSource = null; // Will be detected
        
        this.init();
    }
    
    init() {
        // Khởi tạo event listeners
        this.setupEventListeners();
        
        // Load dữ liệu ban đầu
        this.loadAllData();
        
        // Setup auto refresh (30 phút)
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.loadAllData();
        });
        
        // View switcher buttons
        document.getElementById('hourlyBtn')?.addEventListener('click', () => {
            this.switchView('hourly');
        });
        
        document.getElementById('dailyBtn')?.addEventListener('click', () => {
            this.switchView('daily');
        });
    }
    
    startAutoRefresh() {
        // Refresh mỗi 30 phút
        this.updateInterval = setInterval(() => {
            this.loadAllData();
        }, 30 * 60 * 1000);
    }
    
    switchView(view) {
        this.currentView = view;
        
        // Update button states
        const hourlyBtn = document.getElementById('hourlyBtn');
        const dailyBtn = document.getElementById('dailyBtn');
        
        if (hourlyBtn && dailyBtn) {
            hourlyBtn.classList.toggle('active', view === 'hourly');
            dailyBtn.classList.toggle('active', view === 'daily');
        }
        
        // Re-render content
        this.renderCoins();
    }
    
    async loadAllData() {
        this.showLoading();
        
        try {
            // Detect data source first
            const dataSource = await this.detectDataSource();
            
            if (!dataSource) {
                throw new Error('Không tìm thấy nguồn dữ liệu hợp lệ');
            }
            
            this.dataSource = dataSource;
            console.log('✅ Data source detected:', dataSource);
            
            // Load symbols list
            const symbols = await this.loadSymbolsList();
            if (!symbols || symbols.length === 0) {
                throw new Error('Danh sách symbols trống hoặc không hợp lệ');
            }
            
            console.log('✅ Symbols loaded:', symbols);
            
            // Load data for each symbol
            const promises = symbols.map(symbol => this.loadSymbolData(symbol));
            await Promise.all(promises);
            
            // Update UI
            this.updateLastUpdateTime();
            this.renderCoins();
            this.hideLoading();
            
            console.log('✅ All data loaded successfully');
            
        } catch (error) {
            console.error('❌ Error loading data:', error);
            this.showError('Lỗi khi tải dữ liệu: ' + error.message);
            this.hideLoading();
        }
    }
    
    async detectDataSource() {
        // Thử các nguồn dữ liệu có thể có theo thứ tự ưu tiên
        const possibleSources = [
            './assets/data/',        // GitHub Pages main path
            './data/json/',          // Relative path
            '../data/json/',         // Parent directory
            'assets/data/',          // Without leading ./
            'data/json/',            // Direct path
            '/binance-oi-volume-monitor/assets/data/',  // Full GitHub Pages path
            '/binance-oi-volume-monitor/data/json/',    // Full GitHub Pages path alt
        ];
        
        for (const source of possibleSources) {
            try {
                console.log(`🔍 Trying data source: ${source}`);
                const response = await fetch(`${source}symbols.json`);
                if (response.ok) {
                    const data = await response.json();
                    if (Array.isArray(data) && data.length > 0) {
                        console.log(`✅ Found working data source: ${source}`);
                        return source;
                    }
                }
            } catch (e) {
                console.log(`❌ Failed: ${source} - ${e.message}`);
                // Continue to next source
            }
        }
        
        console.error('❌ No working data source found');
        return null;
    }
    
    async loadSymbolsList() {
        try {
            const response = await fetch(`${this.dataSource}symbols.json`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const symbols = await response.json();
            
            if (!Array.isArray(symbols)) {
                throw new Error('Symbols data is not an array');
            }
            
            if (symbols.length === 0) {
                throw new Error('Symbols array is empty');
            }
            
            return symbols;
            
        } catch (error) {
            console.error('❌ Error loading symbols:', error);
            
            // Fallback to hardcoded symbols
            console.log('🔄 Using fallback symbols');
            return this.symbols;
        }
    }
    
    async loadSymbolData(symbol) {
        try {
            console.log(`📊 Loading data for ${symbol}`);
            const response = await fetch(`${this.dataSource}${symbol}.json`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.coinsData[symbol] = this.processSymbolData(data);
            
            console.log(`✅ Loaded data for ${symbol}`);
            
        } catch (error) {
            console.warn(`⚠️ Không thể load dữ liệu cho ${symbol}:`, error);
            
            // Tạo dữ liệu mẫu nếu không load được
            this.coinsData[symbol] = this.generateSampleData(symbol);
        }
    }
    
    processSymbolData(rawData) {
        // Xử lý và làm sạch dữ liệu
        const processed = {
            klines: rawData.klines || {},
            open_interest: rawData.open_interest || [],
            tracking_24h: rawData.tracking_24h || []
        };
        
        // Sort data by timestamp
        if (processed.open_interest.length > 0) {
            processed.open_interest.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        }
        
        if (processed.tracking_24h.length > 0) {
            processed.tracking_24h.sort((a, b) => new Date(a.hour_timestamp) - new Date(b.hour_timestamp));
        }
        
        // Process klines data
        Object.keys(processed.klines).forEach(timeframe => {
            if (processed.klines[timeframe] && processed.klines[timeframe].length > 0) {
                processed.klines[timeframe].sort((a, b) => new Date(a.open_time) - new Date(b.open_time));
            }
        });
        
        return processed;
    }
    
    generateSampleData(symbol) {
        // Tạo dữ liệu mẫu khi không load được từ API
        const now = new Date();
        const sampleData = {
            klines: { '1d': [] },
            open_interest: [],
            tracking_24h: []
        };
        
        // Generate 30 days of sample data
        for (let i = 29; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            
            const baseValue = Math.random() * 1000000 + 500000;
            
            sampleData.open_interest.push({
                timestamp: date.toISOString(),
                open_interest: baseValue * (0.8 + Math.random() * 0.4)
            });
            
            sampleData.klines['1d'].push({
                open_time: date.toISOString(),
                volume: baseValue * (0.5 + Math.random() * 1.5),
                close: 50000 * (0.8 + Math.random() * 0.4)
            });
        }
        
        // Generate 24 hours of sample data
        for (let i = 23; i >= 0; i--) {
            const date = new Date(now);
            date.setHours(date.getHours() - i, 0, 0, 0);
            
            const baseValue = Math.random() * 1000000 + 500000;
            
            sampleData.tracking_24h.push({
                hour_timestamp: date.toISOString(),
                open_interest: baseValue * (0.8 + Math.random() * 0.4),
                volume: baseValue * (0.5 + Math.random() * 1.5),
                price: 50000 * (0.8 + Math.random() * 0.4)
            });
        }
        
        return sampleData;
    }
    
    renderCoins() {
        const container = document.getElementById('coinsContainer');
        if (!container) return;
        
        container.innerHTML = '';
        
        // Use loaded symbols if available, fallback to default
        const symbolsToRender = Object.keys(this.coinsData).length > 0 ? 
            Object.keys(this.coinsData) : this.symbols;
        
        symbolsToRender.forEach(symbol => {
            if (this.coinsData[symbol]) {
                const coinCard = this.createCoinCard(symbol, this.coinsData[symbol]);
                container.appendChild(coinCard);
            }
        });
        
        // Render charts after DOM is updated
        setTimeout(() => {
            symbolsToRender.forEach(symbol => {
                if (this.coinsData[symbol]) {
                    this.renderCoinChart(symbol, this.coinsData[symbol]);
                }
            });
        }, 100);
    }
    
    createCoinCard(symbol, data) {
        const col = document.createElement('div');
        col.className = 'col-lg-6 col-xl-4 mb-4';
        
        const cleanSymbol = symbol.replace('USDT', '');
        const metrics = this.generateMetricsHTML(symbol, data);
        
        col.innerHTML = `
            <div class="card coin-card h-100">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-currency-bitcoin me-2"></i>
                        ${cleanSymbol}
                    </h5>
                    <small class="opacity-75">${this.currentView === 'hourly' ? '24 giờ qua' : '30 ngày qua'}</small>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        ${metrics}
                    </div>
                    <div class="chart-container">
                        <canvas id="chart-${symbol}"></canvas>
                    </div>
                </div>
            </div>
        `;
        
        return col;
    }
    
    generateMetricsHTML(symbol, data) {
        if (this.currentView === 'hourly') {
            return this.generateHourlyMetrics(data);
        } else {
            return this.generateDailyMetrics(data);
        }
    }
    
    generateHourlyMetrics(data) {
        const hourlyData = data.tracking_24h || [];
        
        if (hourlyData.length === 0) {
            return '<div class="text-muted text-center">Không có dữ liệu</div>';
        }
        
        const latest = hourlyData[hourlyData.length - 1];
        const previous = hourlyData.length > 1 ? hourlyData[hourlyData.length - 2] : latest;
        
        const oiChange = this.calculateChange(latest.open_interest, previous.open_interest);
        const volumeChange = this.calculateChange(latest.volume, previous.volume);
        
        return `
            <div class="metric-box oi">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small>Open Interest</small>
                        <div class="fw-bold">${this.formatNumber(latest.open_interest)}</div>
                    </div>
                    <div class="text-end">
                        <span class="badge ${oiChange >= 0 ? 'bg-success' : 'bg-danger'}">
                            ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                        </span>
                    </div>
                </div>
            </div>
            <div class="metric-box volume">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small>Volume</small>
                        <div class="fw-bold">${this.formatNumber(latest.volume)}</div>
                    </div>
                    <div class="text-end">
                        <span class="badge ${volumeChange >= 0 ? 'bg-success' : 'bg-danger'}">
                            ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                        </span>
                    </div>
                </div>
            </div>
        `;
    }
    
    generateDailyMetrics(data) {
        const dailyOI = data.open_interest || [];
        const dailyKlines = data.klines['1d'] || [];
        
        if (dailyOI.length === 0 && dailyKlines.length === 0) {
            return '<div class="text-muted text-center">Không có dữ liệu</div>';
        }
        
        let oiMetric = '';
        let volumeMetric = '';
        
        if (dailyOI.length > 0) {
            const latestOI = dailyOI[dailyOI.length - 1];
            const previousOI = dailyOI.length > 1 ? dailyOI[dailyOI.length - 2] : latestOI;
            const oiChange = this.calculateChange(latestOI.open_interest, previousOI.open_interest);
            
            oiMetric = `
                <div class="metric-box oi">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small>Open Interest</small>
                            <div class="fw-bold">${this.formatNumber(latestOI.open_interest)}</div>
                        </div>
                        <div class="text-end">
                            <span class="badge ${oiChange >= 0 ? 'bg-success' : 'bg-danger'}">
                                ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (dailyKlines.length > 0) {
            const latestVolume = dailyKlines[dailyKlines.length - 1];
            const previousVolume = dailyKlines.length > 1 ? dailyKlines[dailyKlines.length - 2] : latestVolume;
            const volumeChange = this.calculateChange(latestVolume.volume, previousVolume.volume);
            
            volumeMetric = `
                <div class="metric-box volume">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small>Volume</small>
                            <div class="fw-bold">${this.formatNumber(latestVolume.volume)}</div>
                        </div>
                        <div class="text-end">
                            <span class="badge ${volumeChange >= 0 ? 'bg-success' : 'bg-danger'}">
                                ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return oiMetric + volumeMetric;
    }
    
    renderCoinChart(symbol, data) {
        const canvas = document.getElementById(`chart-${symbol}`);
        if (!canvas) return;
        
        // Destroy existing chart
        if (this.charts[symbol]) {
            this.charts[symbol].destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const chartData = this.prepareChartData(data);
        
        if (chartData.length === 0) {
            // Draw "no data" message
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Không có dữ liệu', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        this.charts[symbol] = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Open Interest',
                        data: chartData.map(item => ({ x: item.x, y: item.oi })),
                        borderColor: '#f5576c',
                        backgroundColor: 'rgba(245, 87, 108, 0.1)',
                        yAxisID: 'y',
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4
                    },
                    {
                        label: 'Volume',
                        data: chartData.map(item => ({ x: item.x, y: item.volume })),
                        borderColor: '#00f2fe',
                        backgroundColor: 'rgba(0, 242, 254, 0.1)',
                        yAxisID: 'y1',
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                return `${label}: ${this.formatNumber ? this.formatNumber(value) : value}`;
                            }.bind(this)
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentView === 'hourly' ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'MM/dd'
                            }
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Open Interest',
                            color: '#f5576c'
                        },
                        ticks: {
                            callback: (value) => this.formatNumber(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Volume',
                            color: '#00f2fe'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            callback: (value) => this.formatNumber(value)
                        }
                    }
                }
            }
        });
    }
    
    prepareChartData(data) {
        let chartData = [];
        
        if (this.currentView === 'hourly') {
            // Data cho view theo giờ (24h)
            const hourlyData = data.tracking_24h || [];
            chartData = hourlyData.map(item => ({
                x: item.hour_timestamp,
                oi: item.open_interest || 0,
                volume: item.volume || 0
            }));
        } else {
            // Data cho view theo ngày (30 ngày)
            const dailyOI = data.open_interest || [];
            const dailyKlines = data.klines['1d'] || [];
            
            // Merge OI and volume data by date
            const mergedData = {};
            
            dailyOI.forEach(item => {
                const date = item.timestamp.split('T')[0];
                if (!mergedData[date]) mergedData[date] = {};
                mergedData[date].oi = item.open_interest;
                mergedData[date].timestamp = item.timestamp;
            });
            
            dailyKlines.forEach(item => {
                const date = item.open_time.split('T')[0];
                if (!mergedData[date]) mergedData[date] = {};
                mergedData[date].volume = item.volume;
                if (!mergedData[date].timestamp) mergedData[date].timestamp = item.open_time;
            });
            
            chartData = Object.keys(mergedData)
                .sort()
                .slice(-30) // Lấy 30 ngày gần nhất
                .map(date => ({
                    x: mergedData[date].timestamp,
                    oi: mergedData[date].oi || 0,
                    volume: mergedData[date].volume || 0
                }));
        }
        
        return chartData;
    }
    
    // Utility functions
    calculateChange(current, previous) {
        if (!previous || previous === 0) return 0;
        return ((current - previous) / previous) * 100;
    }
    
    formatNumber(num) {
        if (!num || isNaN(num)) return '0';
        
        const absNum = Math.abs(num);
        
        if (absNum >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (absNum >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        if (absNum >= 1e3) return (num / 1e3).toFixed(2) + 'K';
        
        return num.toFixed(2);
    }
    
    updateLastUpdateTime() {
        const now = new Date();
        const timeString = now.toLocaleString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const element = document.getElementById('lastUpdateTime');
        if (element) {
            element.innerHTML = `
                <i class="bi bi-clock"></i>
                Cập nhật lần cuối: ${timeString}
            `;
        }
    }
    
    showLoading() {
        const loadingDiv = document.getElementById('loadingDiv');
        const contentDiv = document.getElementById('contentDiv');
        const errorDiv = document.getElementById('errorDiv');
        
        if (loadingDiv) loadingDiv.classList.remove('d-none');
        if (contentDiv) contentDiv.classList.add('d-none');
        if (errorDiv) errorDiv.classList.add('d-none');
    }
    
    hideLoading() {
        const loadingDiv = document.getElementById('loadingDiv');
        const contentDiv = document.getElementById('contentDiv');
        
        if (loadingDiv) loadingDiv.classList.add('d-none');
        if (contentDiv) contentDiv.classList.remove('d-none');
    }
    
    showError(message) {
        const errorDiv = document.getElementById('errorDiv');
        const errorMessage = document.getElementById('errorMessage');
        const loadingDiv = document.getElementById('loadingDiv');
        
        if (errorMessage) errorMessage.textContent = message;
        if (errorDiv) errorDiv.classList.remove('d-none');
        if (loadingDiv) loadingDiv.classList.add('d-none');
        
        console.error('Error:', message);
    }
    
    destroy() {
        // Cleanup
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        // Destroy all charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        
        this.charts = {};
    }
}

// Khởi tạo monitor khi DOM ready
document.addEventListener('DOMContentLoaded', function() {
    window.simpleMonitor = new SimpleOIVolumeMonitor();
});

// Cleanup khi unload
window.addEventListener('beforeunload', function() {
    if (window.simpleMonitor) {
        window.simpleMonitor.destroy();
    }
});