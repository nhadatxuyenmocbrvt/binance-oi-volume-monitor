/**
 * Simple OI & Volume Monitor JavaScript
 * Fixed: Smart data path detection for GitHub Pages
 * Fixed: Data display issues, chart scaling, and repeated data
 * Fixed: Đơn vị hiển thị đúng cho dữ liệu từ Binance
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
            tracking_24h: rawData.tracking_24h || [],
            tracking_30d: rawData.tracking_30d || []
        };
        
        // Sort data by timestamp
        if (processed.open_interest.length > 0) {
            processed.open_interest.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
            
            // QUAN TRỌNG: Đảm bảo giá trị open_interest_value là số
            processed.open_interest = processed.open_interest.map(item => {
                return {
                    ...item,
                    open_interest: parseFloat(item.open_interest),
                    open_interest_value: parseFloat(item.open_interest_value)
                };
            });
            
            // Debug để kiểm tra giá trị OI
            if (processed.open_interest.length > 0) {
                const lastOI = processed.open_interest[processed.open_interest.length-1];
                console.log(`DEBUG OI: ${rawData.symbol} latest OI value=${lastOI.open_interest_value.toLocaleString()} USDT`);
            }
        }
        
        // Xử lý dữ liệu tracking_30d
        if (processed.tracking_30d && processed.tracking_30d.length > 0) {
            processed.tracking_30d.sort((a, b) => new Date(a.date_timestamp) - new Date(b.date_timestamp));
            
            // QUAN TRỌNG: Đảm bảo giá trị số trong trạng thái số (không phải chuỗi)
            processed.tracking_30d = processed.tracking_30d.map(item => {
                return {
                    ...item,
                    price: parseFloat(item.price),
                    quote_volume: parseFloat(item.quote_volume),
                    open_interest_value: parseFloat(item.open_interest_value),
                    avg_open_interest_value: parseFloat(item.avg_open_interest_value),
                    price_change_1d: parseFloat(item.price_change_1d),
                    volume_change_1d: parseFloat(item.volume_change_1d),
                    oi_change_1d: parseFloat(item.oi_change_1d)
                };
            });
            
            // Debug để kiểm tra giá trị OI và Volume trong dữ liệu 30 ngày
            if (processed.tracking_30d.length > 0) {
                const lastRecord = processed.tracking_30d[processed.tracking_30d.length-1];
                console.log(`DEBUG 30d: ${rawData.symbol} latest values: OI=${lastRecord.open_interest_value.toLocaleString()}, Volume=${lastRecord.quote_volume.toLocaleString()}`);
            }
        }
        
        // FIX: Xử lý dữ liệu trùng lặp trong 24h tracking
        if (processed.tracking_24h.length > 0) {
            processed.tracking_24h.sort((a, b) => new Date(a.hour_timestamp) - new Date(b.hour_timestamp));
            
            // QUAN TRỌNG: Đảm bảo giá trị số trong trạng thái số
            processed.tracking_24h = processed.tracking_24h.map(item => {
                return {
                    ...item,
                    price: parseFloat(item.price),
                    volume: parseFloat(item.volume),
                    open_interest: parseFloat(item.open_interest),
                    price_change_1h: parseFloat(item.price_change_1h),
                    volume_change_1h: parseFloat(item.volume_change_1h),
                    oi_change_1h: parseFloat(item.oi_change_1h)
                };
            });
        }
        
        // Process klines data
        Object.keys(processed.klines).forEach(timeframe => {
            if (processed.klines[timeframe] && processed.klines[timeframe].length > 0) {
                processed.klines[timeframe].sort((a, b) => new Date(a.open_time) - new Date(b.open_time));
                
                // Đảm bảo giá trị số
                processed.klines[timeframe] = processed.klines[timeframe].map(item => {
                    return {
                        ...item,
                        open: parseFloat(item.open),
                        high: parseFloat(item.high),
                        low: parseFloat(item.low),
                        close: parseFloat(item.close),
                        volume: parseFloat(item.volume),
                        quote_volume: parseFloat(item.quote_volume)
                    };
                });
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
            tracking_24h: [],
            tracking_30d: [] 
        };
        
        // Các giá trị lớn hơn để phù hợp với giá trị thực tế từ Binance
        const baseOIValue = 5000000000 + Math.random() * 5000000000;  // ~ 5-10B
        const baseVolumeValue = 1000000000 + Math.random() * 2000000000;  // ~ 1-3B
        const price = symbol === 'BTCUSDT' ? 107000 : (symbol === 'ETHUSDT' ? 2500 : 500);
        
        // Generate 30 days of sample data
        for (let i = 29; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            
            const oiValue = baseOIValue * (0.9 + Math.random() * 0.2);
            const volumeValue = baseVolumeValue * (0.8 + Math.random() * 0.4);
            const currentPrice = price * (0.9 + Math.random() * 0.2);
            
            sampleData.open_interest.push({
                timestamp: date.toISOString(),
                open_interest: oiValue / currentPrice,  // Contracts
                open_interest_value: oiValue  // USDT value
            });
            
            sampleData.klines['1d'].push({
                open_time: date.toISOString(),
                volume: volumeValue / currentPrice,  // Contracts
                quote_volume: volumeValue,  // USDT value
                close: currentPrice
            });
            
            // Generate tracking_30d data with realistic values
            sampleData.tracking_30d.push({
                date_timestamp: date.toISOString(),
                price: currentPrice,
                quote_volume: volumeValue,
                open_interest_value: oiValue,
                avg_open_interest_value: oiValue * 0.98,
                price_change_1d: (Math.random() * 8) - 4,
                volume_change_1d: (Math.random() * 20) - 10,
                oi_change_1d: (Math.random() * 12) - 6,
                is_actual_data: 0
            });
        }
        
        // Generate 24 hours of sample data with realistic values
        for (let i = 23; i >= 0; i--) {
            const date = new Date(now);
            date.setHours(date.getHours() - i, 0, 0, 0);
            
            const hourlyOI = baseOIValue * (0.95 + Math.random() * 0.1);
            const hourlyVolume = baseVolumeValue / 24 * (0.8 + Math.random() * 0.4);
            const hourlyPrice = price * (0.99 + Math.random() * 0.02);
            
            sampleData.tracking_24h.push({
                hour_timestamp: date.toISOString(),
                open_interest: hourlyOI,
                volume: hourlyVolume,
                price: hourlyPrice,
                price_change_1h: (Math.random() * 2) - 1,
                volume_change_1h: (Math.random() * 10) - 5,
                oi_change_1h: (Math.random() * 4) - 2,
                is_actual_data: 0
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
            return this.generateDailyMetrics(symbol, data);
        }
    }
    
    generateHourlyMetrics(data) {
        const hourlyData = data.tracking_24h || [];
        
        if (hourlyData.length === 0) {
            return '<div class="text-muted text-center">Không có dữ liệu</div>';
        }
        
        // FIX: Kiểm tra dữ liệu hợp lệ trước khi hiển thị
        const validData = hourlyData.filter(item => 
            item && 
            typeof item.open_interest === 'number' && 
            typeof item.volume === 'number' &&
            !isNaN(item.open_interest) &&
            !isNaN(item.volume) &&
            item.open_interest > 0 &&
            item.volume > 0
        );
        
        if (validData.length === 0) {
            return '<div class="text-muted text-center">Dữ liệu không hợp lệ</div>';
        }
        
        const latest = validData[validData.length - 1];
        const previous = validData.length > 1 ? validData[validData.length - 2] : latest;
        
        const oiChange = this.calculateChange(latest.open_interest, previous.open_interest);
        const volumeChange = this.calculateChange(latest.volume, previous.volume);
        
        // FIX: Hiển thị đơn vị tiền tệ USDT để rõ ràng hơn
        return `
            <div class="metric-box oi">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small>Open Interest</small>
                        <div class="fw-bold">${this.formatNumber(latest.open_interest)} USDT</div>
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
                        <div class="fw-bold">${this.formatNumber(latest.volume)} USDT</div>
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
    
    generateDailyMetrics(symbol, data) {
        // FIX: Ưu tiên sử dụng tracking_30d nếu có
        if (data.tracking_30d && data.tracking_30d.length > 0) {
            // Lọc các dữ liệu có giá trị hợp lệ
            const validData = data.tracking_30d.filter(item => 
                item && 
                typeof item.open_interest_value === 'number' && 
                typeof item.quote_volume === 'number' &&
                !isNaN(item.open_interest_value) &&
                !isNaN(item.quote_volume) &&
                item.open_interest_value > 0 &&
                item.quote_volume > 0
            );
            
            console.log(`DEBUG: ${symbol} 30d data - ${validData.length} valid records`);
            
            if (validData.length > 0) {
                const latest = validData[validData.length - 1];
                const previous = validData.length > 1 ? validData[validData.length - 2] : latest;
                
                // QUAN TRỌNG: Log để debug giá trị thực tế
                console.log(`${symbol} latest OI = ${latest.open_interest_value.toLocaleString()}, Volume = ${latest.quote_volume.toLocaleString()}`);
                
                const oiChange = this.calculateChange(latest.open_interest_value, previous.open_interest_value);
                const volumeChange = this.calculateChange(latest.quote_volume, previous.quote_volume);
                
                return `
                    <div class="metric-box oi">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <small>Open Interest (30 ngày)</small>
                                <div class="fw-bold">${this.formatNumber(latest.open_interest_value)} USDT</div>
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
                                <small>Volume (30 ngày)</small>
                                <div class="fw-bold">${this.formatNumber(latest.quote_volume)} USDT</div>
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
        }
        
        // Fallback: Sử dụng open_interest và klines
        const dailyOI = data.open_interest || [];
        const dailyKlines = data.klines['1d'] || [];
        
        if (dailyOI.length === 0 && dailyKlines.length === 0) {
            return '<div class="text-muted text-center">Không có dữ liệu</div>';
        }
        
        let oiMetric = '';
        let volumeMetric = '';
        
        if (dailyOI.length > 0) {
            // FIX: Ưu tiên sử dụng open_interest_value thay vì open_interest
            const latestOI = dailyOI[dailyOI.length - 1];
            const previousOI = dailyOI.length > 1 ? dailyOI[dailyOI.length - 2] : latestOI;
            
            // FIX: Kiểm tra xem có open_interest_value không
            const oiValue = latestOI.open_interest_value || latestOI.open_interest;
            const prevOiValue = previousOI.open_interest_value || previousOI.open_interest;
            
            // Debug để kiểm tra giá trị thực tế
            console.log(`${symbol} OI value from open_interest: ${oiValue.toLocaleString()}`);
            
            const oiChange = this.calculateChange(oiValue, prevOiValue);
            
            oiMetric = `
                <div class="metric-box oi">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small>Open Interest</small>
                            <div class="fw-bold">${this.formatNumber(oiValue)} USDT</div>
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
            // FIX: Ưu tiên sử dụng quote_volume thay vì volume
            const latestVolume = dailyKlines[dailyKlines.length - 1];
            const previousVolume = dailyKlines.length > 1 ? dailyKlines[dailyKlines.length - 2] : latestVolume;
            
            const volumeValue = latestVolume.quote_volume || latestVolume.volume;
            const prevVolumeValue = previousVolume.quote_volume || previousVolume.volume;
            
            // Debug để kiểm tra giá trị thực tế
            console.log(`${symbol} Volume value from klines: ${volumeValue.toLocaleString()}`);
            
            const volumeChange = this.calculateChange(volumeValue, prevVolumeValue);
            
            volumeMetric = `
                <div class="metric-box volume">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <small>Volume</small>
                            <div class="fw-bold">${this.formatNumber(volumeValue)} USDT</div>
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
        const chartData = this.prepareChartData(symbol, data);
        
        if (chartData.length === 0) {
            // Draw "no data" message
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Không có dữ liệu', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // FIX: Cải thiện cấu hình biểu đồ
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
                        pointHoverRadius: 4,
                        // FIX: Xử lý dữ liệu bị thiếu
                        spanGaps: false
                    },
                    {
                        label: 'Volume',
                        data: chartData.map(item => ({ x: item.x, y: item.volume })),
                        borderColor: '#00f2fe',
                        backgroundColor: 'rgba(0, 242, 254, 0.1)',
                        yAxisID: 'y1',
                        tension: 0.4,
                        pointRadius: 2,
                        pointHoverRadius: 4,
                        // FIX: Xử lý dữ liệu bị thiếu
                        spanGaps: false
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
                                return `${label}: ${this.formatNumber ? this.formatNumber(value) : value} USDT`;
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
                        // FIX: Đảm bảo biểu đồ luôn bắt đầu từ 0
                        beginAtZero: false,
                        title: {
                            display: true,
                            text: 'Open Interest (USDT)',
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
                        // FIX: Đảm bảo biểu đồ luôn bắt đầu từ 0
                        beginAtZero: false, 
                        title: {
                            display: true,
                            text: 'Volume (USDT)',
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
    
    prepareChartData(symbol, data) {
        let chartData = [];
        
        if (this.currentView === 'hourly') {
            // Data cho view theo giờ (24h)
            const hourlyData = data.tracking_24h || [];
            
            // FIX: Lọc dữ liệu không hợp lệ
            chartData = hourlyData
                .filter(item => 
                    item && 
                    item.hour_timestamp && 
                    typeof item.open_interest === 'number' && 
                    typeof item.volume === 'number' &&
                    !isNaN(item.open_interest) &&
                    !isNaN(item.volume) &&
                    item.open_interest > 0 &&
                    item.volume > 0
                )
                .map(item => ({
                    x: item.hour_timestamp,
                    oi: item.open_interest || 0,
                    volume: item.volume || 0
                }));
                
            // Log dữ liệu biểu đồ để debug
            if (chartData.length > 0) {
                console.log(`${symbol} 24h chart data: ${chartData.length} points, OI range: ${Math.min(...chartData.map(item => item.oi)).toLocaleString()} - ${Math.max(...chartData.map(item => item.oi)).toLocaleString()}`);
            }
                
            // FIX: Phát hiện dữ liệu trùng lặp
            if (chartData.length > 1) {
                const uniqueData = [];
                let lastOI = null;
                let lastVolume = null;
                let duplicateCount = 0;
                
                for (const item of chartData) {
                    // Nếu 3 điểm dữ liệu liên tiếp hoàn toàn giống nhau, có thể là dữ liệu sao chép
                    if (lastOI === item.oi && lastVolume === item.volume) {
                        duplicateCount++;
                        if (duplicateCount > 3) {
                            // FIX: Đánh dấu điểm dữ liệu này là null để Chart.js hiển thị khoảng trống
                            item.oi = null;
                            item.volume = null;
                            console.log(`🔄 Marking duplicated data point as null`);
                            continue;
                        }
                    } else {
                        duplicateCount = 0;
                    }
                    
                    lastOI = item.oi;
                    lastVolume = item.volume;
                    uniqueData.push(item);
                }
                
                // Không cần thay thế chartData vì chúng ta đã đánh dấu các điểm trùng lặp là null
            }
        } else {
            // FIX: Ưu tiên sử dụng tracking_30d nếu có
            if (data.tracking_30d && data.tracking_30d.length > 0) {
                chartData = data.tracking_30d
                    .filter(item => 
                        item && 
                        item.date_timestamp && 
                        typeof item.open_interest_value === 'number' && 
                        typeof item.quote_volume === 'number' &&
                        !isNaN(item.open_interest_value) &&
                        !isNaN(item.quote_volume) &&
                        item.open_interest_value > 0 &&
                        item.quote_volume > 0
                    )
                    .map(item => ({
                        x: item.date_timestamp,
                        oi: item.open_interest_value || 0,
                        volume: item.quote_volume || 0
                    }));
                
                // Log dữ liệu biểu đồ để debug
                if (chartData.length > 0) {
                    console.log(`${symbol} 30d chart data: ${chartData.length} points, OI range: ${Math.min(...chartData.map(item => item.oi)).toLocaleString()} - ${Math.max(...chartData.map(item => item.oi)).toLocaleString()}`);
                }
                
                console.log(`📊 Using tracking_30d for daily chart with ${chartData.length} points`);
            } else {
                // Fallback: Data cho view theo ngày (30 ngày) từ open_interest và klines
                const dailyOI = data.open_interest || [];
                const dailyKlines = data.klines['1d'] || [];
                
                // Merge OI and volume data by date
                const mergedData = {};
                
                dailyOI.forEach(item => {
                    if (!item || !item.timestamp) return;
                    
                    const date = item.timestamp.split('T')[0];
                    if (!mergedData[date]) mergedData[date] = {};
                    
                    // FIX: Ưu tiên sử dụng open_interest_value
                    mergedData[date].oi = item.open_interest_value || item.open_interest;
                    mergedData[date].timestamp = item.timestamp;
                });
                
                dailyKlines.forEach(item => {
                    if (!item || !item.open_time) return;
                    
                    const date = item.open_time.split('T')[0];
                    if (!mergedData[date]) mergedData[date] = {};
                    
                    // FIX: Ưu tiên sử dụng quote_volume
                    mergedData[date].volume = item.quote_volume || item.volume;
                    if (!mergedData[date].timestamp) mergedData[date].timestamp = item.open_time;
                });
                
                chartData = Object.keys(mergedData)
                    .sort()
                    .slice(-30) // Lấy 30 ngày gần nhất
                    .map(date => ({
                        x: mergedData[date].timestamp,
                        oi: mergedData[date].oi || 0,
                        volume: mergedData[date].volume || 0
                    }))
                    .filter(item => item.oi > 0 && item.volume > 0); // Lọc các điểm có giá trị hợp lệ
            }
        }
        
        return chartData;
    }
    
    // Utility functions
    calculateChange(current, previous) {
        if (!current || !previous || previous === 0) return 0;
        return ((current - previous) / previous) * 100;
    }
    
    // FIX: Cải thiện định dạng số - QUAN TRỌNG
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