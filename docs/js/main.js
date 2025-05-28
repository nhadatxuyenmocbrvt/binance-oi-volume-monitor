/**
 * Simple OI & Volume Monitor JavaScript - List View Version
 * Đã chuyển đổi từ Card View sang List View
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
        // Debug data availability
        this.debugDataAvailability();
        
        // Khởi tạo event listeners
        this.setupEventListeners();
        
        // Load dữ liệu ban đầu
        this.loadAllData();
        
        // Setup auto refresh (30 phút)
        this.startAutoRefresh();
    }
    
    async debugDataAvailability() {
        console.group('🔍 Kiểm tra khả năng truy cập dữ liệu');
        
        const paths = [
            './assets/data/symbols.json',
            '/binance-oi-volume-monitor/assets/data/symbols.json',
            'https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/assets/data/symbols.json',
            './data/json/symbols.json',
            '/binance-oi-volume-monitor/data/json/symbols.json',
            'https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/data/json/symbols.json',
            'https://raw.githubusercontent.com/nhadatxuyenmocbrvt/binance-oi-volume-monitor/main/docs/assets/data/symbols.json',
            'https://raw.githubusercontent.com/nhadatxuyenmocbrvt/binance-oi-volume-monitor/main/data/json/symbols.json'
        ];
        
        console.log('🌐 Current URL:', window.location.href);
        console.log('🌐 Base URL:', window.location.origin + window.location.pathname);
        
        for (const path of paths) {
            try {
                console.log(`🔍 Trying: ${path}`);
                const response = await fetch(path);
                if (response.ok) {
                    const contentType = response.headers.get('content-type');
                    console.log(`✅ Success! Content-Type: ${contentType}`);
                    
                    if (contentType && contentType.includes('application/json')) {
                        const data = await response.json();
                        console.log(`📋 Data: ${JSON.stringify(data)}`);
                    }
                } else {
                    console.log(`❌ Failed with status: ${response.status}`);
                }
            } catch (e) {
                console.log(`❌ Error: ${e.message}`);
            }
        }
        
        console.groupEnd();
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
        
        // Toggle view button (List/Card)
        document.getElementById('toggleViewBtn')?.addEventListener('click', () => {
            this.toggleDisplayMode();
        });
    }
    
    toggleDisplayMode() {
        const container = document.getElementById('contentContainer');
        const toggleBtn = document.getElementById('toggleViewBtn');
        
        if (container.classList.contains('list-view')) {
            // Chuyển từ list view sang card view
            container.classList.remove('list-view');
            container.classList.add('card-view');
            toggleBtn.innerHTML = '<i class="bi bi-list"></i> Xem dạng danh sách';
        } else {
            // Chuyển từ card view sang list view
            container.classList.remove('card-view');
            container.classList.add('list-view');
            toggleBtn.innerHTML = '<i class="bi bi-grid"></i> Xem dạng thẻ';
        }
        
        // Render lại dữ liệu với chế độ hiển thị mới
        this.renderCoins();
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
            // Đường dẫn GitHub Pages từ /docs
            './assets/data/',                                      // Tương đối từ trang hiện tại (trong /docs)
            '/binance-oi-volume-monitor/assets/data/',             // Tuyệt đối từ root domain
            'https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/assets/data/',  // URL đầy đủ
            
            // Đường dẫn từ /data/json
            './data/json/',                                        // Tương đối
            '../data/json/',                                       // Lên một cấp
            '/binance-oi-volume-monitor/data/json/',               // Tuyệt đối
            'https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/data/json/',  // URL đầy đủ
            
            // Đường dẫn từ /docs/assets/data (raw GitHub URLs)
            'https://raw.githubusercontent.com/nhadatxuyenmocbrvt/binance-oi-volume-monitor/main/docs/assets/data/',
            
            // Đường dẫn từ /data/json (raw GitHub URLs)
            'https://raw.githubusercontent.com/nhadatxuyenmocbrvt/binance-oi-volume-monitor/main/data/json/',
            
            // Các đường dẫn khác
            'assets/data/',                                        // Không có ./
            'data/json/',                                          // Không có ./
        ];
        
        // Log vị trí hiện tại để debug
        console.log('Current URL:', window.location.href);
        console.log('Base URL:', window.location.origin + window.location.pathname);
        
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
        console.log(`⚠️ Sử dụng dữ liệu mẫu cho ${symbol} vì không tải được dữ liệu thực`);
        
        // Tạo dữ liệu mẫu khi không load được từ API
        const now = new Date();
        const sampleData = {
            symbol: symbol,
            klines: { '1d': [] },
            open_interest: [],
            tracking_24h: [],
            tracking_30d: [] 
        };
        
        // Các giá trị cơ sở tùy thuộc vào loại tiền
        let basePrice, baseOIValue, baseVolumeValue;
        
        switch(symbol) {
            case 'BTCUSDT':
                basePrice = 107000;
                baseOIValue = 9270000000; // 9.27B
                baseVolumeValue = 16790000000; // 16.79B
                break;
            case 'ETHUSDT':
                basePrice = 2500;
                baseOIValue = 4040000000; // 4.04B
                baseVolumeValue = 8700000000; // 8.7B
                break;
            case 'BNBUSDT':
                basePrice = 650;
                baseOIValue = 1200000000; // 1.2B
                baseVolumeValue = 2500000000; // 2.5B
                break;
            case 'SOLUSDT':
                basePrice = 180;
                baseOIValue = 850000000; // 850M
                baseVolumeValue = 1800000000; // 1.8B
                break;
            case 'DOGEUSDT':
                basePrice = 0.15;
                baseOIValue = 450000000; // 450M
                baseVolumeValue = 1200000000; // 1.2B
                break;
            default:
                basePrice = 500;
                baseOIValue = 1000000000; // 1B
                baseVolumeValue = 2000000000; // 2B
        }
        
        // Generate 30 days of sample data with realistic fluctuations
        for (let i = 29; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            
            // Create realistic daily changes (range of ±3% from base with some randomness)
            const dailyFactor = 0.97 + (Math.random() * 0.06); // 0.97 to 1.03
            const currentPrice = basePrice * dailyFactor;
            const oiValue = baseOIValue * (0.95 + (Math.random() * 0.1)); // ±5%
            const volumeValue = baseVolumeValue * (0.9 + (Math.random() * 0.2)); // ±10%
            
            // Add to open_interest array
            sampleData.open_interest.push({
                timestamp: date.toISOString(),
                open_interest: oiValue / currentPrice,  // Contracts
                open_interest_value: oiValue  // USDT value
            });
            
            // Add to klines
            sampleData.klines['1d'].push({
                open_time: date.toISOString(),
                open: currentPrice * 0.99,
                high: currentPrice * 1.02,
                low: currentPrice * 0.98,
                close: currentPrice,
                volume: volumeValue / currentPrice,  // Contracts
                quote_volume: volumeValue,  // USDT value
                count: Math.floor(5000 + Math.random() * 15000) // Number of trades
            });
            
            // Add to tracking_30d
            sampleData.tracking_30d.push({
                date_timestamp: date.toISOString(),
                price: currentPrice,
                quote_volume: volumeValue,
                open_interest_value: oiValue,
                avg_open_interest_value: oiValue * 0.98,
                price_change_1d: (Math.random() * 6) - 3, // -3% to +3%
                volume_change_1d: (Math.random() * 20) - 10, // -10% to +10%
                oi_change_1d: (Math.random() * 10) - 5, // -5% to +5%
                is_actual_data: 0
            });
        }
        
        // Generate 24 hours of sample data
        for (let i = 23; i >= 0; i--) {
            const date = new Date(now);
            date.setHours(date.getHours() - i, 0, 0, 0);
            
            // Create hourly fluctuations
            const hourlyFactor = 0.99 + (Math.random() * 0.02); // 0.99 to 1.01
            const hourlyPrice = basePrice * hourlyFactor;
            const hourlyOI = baseOIValue * (0.98 + (Math.random() * 0.04)); // ±2%
            const hourlyVolume = baseVolumeValue / 24 * (0.8 + (Math.random() * 0.4)); // ±20%
            
            sampleData.tracking_24h.push({
                hour_timestamp: date.toISOString(),
                open_interest: hourlyOI,
                volume: hourlyVolume,
                price: hourlyPrice,
                price_change_1h: (Math.random() * 2) - 1, // -1% to +1%
                volume_change_1h: (Math.random() * 14) - 7, // -7% to +7%
                oi_change_1h: (Math.random() * 4) - 2, // -2% to +2%
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
            
        const isListView = document.getElementById('contentContainer').classList.contains('list-view');
        
        if (isListView) {
            this.renderListView(symbolsToRender);
        } else {
            this.renderCardView(symbolsToRender);
        }
    }
    
    renderListView(symbols) {
        const container = document.getElementById('coinsContainer');
        if (!container) return;
        
        // Tạo bảng cho list view
        const table = document.createElement('table');
        table.className = 'table table-striped table-hover coins-table';
        
        // Tạo phần thead của bảng
        const thead = document.createElement('thead');
        thead.className = 'table-dark';
        
        thead.innerHTML = `
            <tr>
                <th scope="col">Coin</th>
                <th scope="col">Giá</th>
                <th scope="col">Open Interest</th>
                <th scope="col">OI Change</th>
                <th scope="col">Volume</th>
                <th scope="col">Volume Change</th>
                <th scope="col" class="text-center">Biểu đồ</th>
            </tr>
        `;
        
        table.appendChild(thead);
        
        // Tạo phần tbody của bảng
        const tbody = document.createElement('tbody');
        
        symbols.forEach(symbol => {
            if (this.coinsData[symbol]) {
                const row = this.createCoinRow(symbol, this.coinsData[symbol]);
                tbody.appendChild(row);
            }
        });
        
        table.appendChild(tbody);
        container.appendChild(table);
        
        // Render biểu đồ mini sau khi DOM đã cập nhật
        setTimeout(() => {
            symbols.forEach(symbol => {
                if (this.coinsData[symbol]) {
                    this.renderMiniChart(symbol, this.coinsData[symbol]);
                }
            });
        }, 100);
    }
    
    createCoinRow(symbol, data) {
        const row = document.createElement('tr');
        const cleanSymbol = symbol.replace('USDT', '');
        
        let price = 0;
        let oiValue = 0;
        let oiChange = 0;
        let volumeValue = 0;
        let volumeChange = 0;
        
        // Lấy dữ liệu cần hiển thị
        if (this.currentView === 'hourly') {
            const hourlyData = data.tracking_24h || [];
            if (hourlyData.length > 0) {
                const latest = hourlyData[hourlyData.length - 1];
                const previous = hourlyData.length > 1 ? hourlyData[hourlyData.length - 2] : latest;
                
                price = latest.price || 0;
                oiValue = latest.open_interest_value || 0;
                volumeValue = latest.quote_volume || 0;
                oiChange = this.calculateChange(latest.open_interest_value, previous.open_interest_value);
                volumeChange = this.calculateChange(latest.quote_volume, previous.quote_volume);
            }
        } else {
            // Dữ liệu 30 ngày
            if (data.tracking_30d && data.tracking_30d.length > 0) {
                const latest = data.tracking_30d[data.tracking_30d.length - 1];
                const previous = data.tracking_30d.length > 1 ? data.tracking_30d[data.tracking_30d.length - 2] : latest;
                
                price = latest.price || 0;
                oiValue = latest.avg_open_interest_value || latest.open_interest_value || 0;
                volumeValue = latest.quote_volume || 0;
                oiChange = this.calculateChange(oiValue, previous.avg_open_interest_value || previous.open_interest_value);
                volumeChange = this.calculateChange(latest.quote_volume, previous.quote_volume);
            }
        }
        
        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <i class="bi bi-currency-bitcoin me-2"></i>
                    <strong>${cleanSymbol}</strong>
                </div>
            </td>
            <td>${price.toFixed(2)} USDT</td>
            <td>${this.formatNumber(oiValue)} USDT</td>
            <td>
                <span class="badge ${oiChange >= 0 ? 'bg-success' : 'bg-danger'}">
                    ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                </span>
            </td>
            <td>${this.formatNumber(volumeValue)} USDT</td>
            <td>
                <span class="badge ${volumeChange >= 0 ? 'bg-success' : 'bg-danger'}">
                    ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                </span>
            </td>
            <td>
                <div class="mini-chart-container">
                    <canvas id="minichart-${symbol}" width="150" height="50"></canvas>
                </div>
            </td>
        `;
        
        return row;
    }
    
    renderCardView(symbols) {
        const container = document.getElementById('coinsContainer');
        if (!container) return;
        
        symbols.forEach(symbol => {
            if (this.coinsData[symbol]) {
                const coinCard = this.createCoinCard(symbol, this.coinsData[symbol]);
                container.appendChild(coinCard);
            }
        });
        
        // Render charts after DOM is updated
        setTimeout(() => {
            symbols.forEach(symbol => {
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
        
        // FIX: Kiểm tra dữ liệu hợp lệ trước khi hiển thị - luôn dùng quote_volume và open_interest_value
        const validData = hourlyData.filter(item => 
            item && 
            typeof item.open_interest_value === 'number' && 
            typeof item.quote_volume === 'number' &&
            !isNaN(item.open_interest_value) &&
            !isNaN(item.quote_volume) &&
            item.open_interest_value > 0 &&
            item.quote_volume > 0
        );
        
        if (validData.length === 0) {
            return '<div class="text-muted text-center">Dữ liệu không hợp lệ</div>';
        }
        
        const latest = validData[validData.length - 1];
        const previous = validData.length > 1 ? validData[validData.length - 2] : latest;
        
        const oiChange = this.calculateChange(latest.open_interest_value, previous.open_interest_value);
        const volumeChange = this.calculateChange(latest.quote_volume, previous.quote_volume);
        
        // FIX: Hiển thị đơn vị tiền tệ USDT để rõ ràng hơn và luôn dùng quote_volume
        return `
            <div class="metric-box oi">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <small>Open Interest</small>
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
                        <small>Volume</small>
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

    // Sửa hàm generateDailyMetrics để luôn sử dụng quote_volume và avg_open_interest_value
    generateDailyMetrics(symbol, data) {
        // FIX: Ưu tiên sử dụng tracking_30d nếu có
        if (data.tracking_30d && data.tracking_30d.length > 0) {
            // Lọc các dữ liệu có giá trị hợp lệ - ưu tiên dùng avg_open_interest_value và quote_volume
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
                
                // FIX: Đảm bảo sử dụng avg_open_interest_value nếu có, nếu không thì dùng open_interest_value
                const oiValueToDisplay = latest.avg_open_interest_value || latest.open_interest_value;
                
                return `
                    <div class="metric-box oi">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <small>Open Interest (30 ngày)</small>
                                <div class="fw-bold">${this.formatNumber(oiValueToDisplay)} USDT</div>
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
            
            // FIX: Đảm bảo sử dụng open_interest_value để hiển thị giá trị USDT
            const oiValue = latestOI.open_interest_value || 0;
            const prevOiValue = previousOI.open_interest_value || 0;
            
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
            
            const volumeValue = latestVolume.quote_volume || 0;
            const prevVolumeValue = previousVolume.quote_volume || 0;
            
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
        
        // Tính toán giá trị min và max cho trục y (Open Interest)
        const oiValues = chartData.map(item => item.oi).filter(v => v !== null && v !== undefined);
        const minOI = oiValues.length > 0 ? Math.min(...oiValues) * 0.98 : 0; // Giảm 2% để có khoảng cách
        const maxOI = oiValues.length > 0 ? Math.max(...oiValues) * 1.02 : 0; // Tăng 2% để có khoảng cách
        
        // Tính toán giá trị min và max cho trục y1 (Volume)
        const volumeValues = chartData.map(item => item.volume).filter(v => v !== null && v !== undefined);
        const minVolume = volumeValues.length > 0 ? Math.min(...volumeValues) * 0.98 : 0;
        const maxVolume = volumeValues.length > 0 ? Math.max(...volumeValues) * 1.02 : 0;
        
        // Log để debug
        console.log(`${symbol} OI range: ${this.formatNumber(minOI)} - ${this.formatNumber(maxOI)}`);
        console.log(`${symbol} Volume range: ${this.formatNumber(minVolume)} - ${this.formatNumber(maxVolume)}`);
        
        // FIX: Cải thiện cấu hình biểu đồ với min/max đã tính toán
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
                        // FIX: Đặt min và max dựa trên dữ liệu thực tế
                        min: minOI,
                        max: maxOI,
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
                        // FIX: Đặt min và max dựa trên dữ liệu thực tế
                        min: minVolume,
                        max: maxVolume,
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
    
    // Render mini chart cho list view
    renderMiniChart(symbol, data) {
        const canvas = document.getElementById(`minichart-${symbol}`);
        if (!canvas) return;
        
        // Xóa biểu đồ cũ nếu có
        if (this.charts[`mini-${symbol}`]) {
            this.charts[`mini-${symbol}`].destroy();
        }
        
        const ctx = canvas.getContext('2d');
        const chartData = this.prepareChartData(symbol, data);
        
        if (chartData.length === 0) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Không có dữ liệu', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Cấu hình mini chart đơn giản hơn
        this.charts[`mini-${symbol}`] = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'OI',
                        data: chartData.map(item => ({ x: item.x, y: item.oi })),
                        borderColor: '#f5576c',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        display: false
                    },
                    y: {
                        display: false
                    }
                },
                elements: {
                    point: {
                        radius: 0
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
            
            // FIX: Lọc dữ liệu không hợp lệ - luôn sử dụng quote_volume và open_interest_value
            chartData = hourlyData
                .filter(item => 
                    item && 
                    item.hour_timestamp && 
                    typeof (item.open_interest_value || item.open_interest) === 'number' && 
                    typeof (item.quote_volume || item.volume) === 'number' &&
                    !isNaN(item.open_interest_value || item.open_interest) &&
                    !isNaN(item.quote_volume || item.volume) &&
                    (item.open_interest_value || item.open_interest) > 0 &&
                    (item.quote_volume || item.volume) > 0
                )
                .map(item => ({
                    x: item.hour_timestamp,
                    oi: item.open_interest_value || item.open_interest || 0, 
                    volume: item.quote_volume || item.volume || 0
                }));
                    
            // Log dữ liệu biểu đồ để debug
            if (chartData.length > 0) {
                console.log(`${symbol} 24h chart data: ${chartData.length} points, Volume range: ${Math.min(...chartData.map(item => item.volume)).toLocaleString()} - ${Math.max(...chartData.map(item => item.volume)).toLocaleString()}`);
            }
        } else {
            // FIX: Ưu tiên sử dụng tracking_30d nếu có
            if (data.tracking_30d && data.tracking_30d.length > 0) {
                chartData = data.tracking_30d
                    .filter(item => 
                        item && 
                        item.date_timestamp && 
                        typeof (item.open_interest_value || item.avg_open_interest_value) === 'number' && 
                        typeof item.quote_volume === 'number' &&
                        !isNaN(item.open_interest_value || item.avg_open_interest_value) &&
                        !isNaN(item.quote_volume) &&
                        (item.open_interest_value || item.avg_open_interest_value) > 0 &&
                        item.quote_volume > 0
                    )
                    .map(item => ({
                        x: item.date_timestamp,
                        oi: item.avg_open_interest_value || item.open_interest_value || 0,
                        volume: item.quote_volume || 0
                    }));
                
                // Log dữ liệu biểu đồ để debug
                if (chartData.length > 0) {
                    console.log(`${symbol} 30d chart data: ${chartData.length} points, Volume range: ${Math.min(...chartData.map(item => item.volume)).toLocaleString()} - ${Math.max(...chartData.map(item => item.volume)).toLocaleString()}`);
                }
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
                    mergedData[date].oi = item.open_interest_value || item.open_interest || 0;
                    mergedData[date].timestamp = item.timestamp;
                });
                
                dailyKlines.forEach(item => {
                    if (!item || !item.open_time) return;
                    
                    const date = item.open_time.split('T')[0];
                    if (!mergedData[date]) mergedData[date] = {};
                    
                    // FIX: Ưu tiên sử dụng quote_volume
                    mergedData[date].volume = item.quote_volume || (item.volume * item.close) || 0;
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