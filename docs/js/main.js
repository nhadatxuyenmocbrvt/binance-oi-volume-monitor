/**
 * Simple OI & Volume Monitor JavaScript
 * Đã cập nhật với chức năng hiển thị biểu đồ dạng cột, hỗ trợ List View và Table View
 * Version 3.0.1 - Chỉ hiển thị dữ liệu thật
 */

class SimpleOIVolumeMonitor {
    constructor() {
        this.currentView = 'hourly';
        this.displayMode = this.getInitialDisplayMode();
        this.coinsData = {};
        this.charts = {};
        this.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        this.updateInterval = null;
        this.dataSource = null; // Will be detected
        this.dataType = 'oi'; // 'oi', 'volume', 'both' - cho chế độ xem bảng
        this.timeRange = 30; // Số ngày hiển thị trong chế độ xem bảng
        
        this.init();
    }
    
    getInitialDisplayMode() {
        // Kiểm tra URL để xác định chế độ hiển thị ban đầu
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get('mode');
        
        if (mode === 'table') {
            return 'table-view';
        } else if (mode === 'list') {
            return 'list-view';
        } else {
            return 'card-view';
        }
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
        
        // Toggle view mode buttons
        document.getElementById('toggleViewBtn')?.addEventListener('click', () => {
            this.toggleDisplayMode();
        });
        
        document.getElementById('cardViewBtn')?.addEventListener('click', () => {
            this.setDisplayMode('card-view');
        });
        
        document.getElementById('listViewBtn')?.addEventListener('click', () => {
            this.setDisplayMode('list-view');
        });
        
        document.getElementById('tableViewBtn')?.addEventListener('click', () => {
            this.setDisplayMode('table-view');
        });
        
        // Table view additional controls
        document.getElementById('oiRadio')?.addEventListener('change', () => {
            this.dataType = 'oi';
            if (this.displayMode === 'table-view') {
                this.renderTableData();
            }
        });
        
        document.getElementById('volumeRadio')?.addEventListener('change', () => {
            this.dataType = 'volume';
            if (this.displayMode === 'table-view') {
                this.renderTableData();
            }
        });
        
        document.getElementById('bothRadio')?.addEventListener('change', () => {
            this.dataType = 'both';
            if (this.displayMode === 'table-view') {
                this.renderTableData();
            }
        });
        
        document.getElementById('timeRangeSelect')?.addEventListener('change', (e) => {
            this.timeRange = parseInt(e.target.value);
            if (this.displayMode === 'table-view') {
                this.renderTableData();
            }
        });
    }
    
    toggleDisplayMode() {
        const container = document.getElementById('contentContainer');
        const toggleBtn = document.getElementById('toggleViewBtn');
        
        if (!container) return;
        
        if (container.classList.contains('list-view')) {
            // Chuyển từ list view sang card view
            this.setDisplayMode('card-view');
        } else {
            // Chuyển từ card view sang list view
            this.setDisplayMode('list-view');
        }
    }
    
    setDisplayMode(mode) {
        this.displayMode = mode;
        
        const container = document.getElementById('contentContainer');
        const toggleBtn = document.getElementById('toggleViewBtn');
        const viewControls = document.getElementById('viewControls');
        const tableViewControls = document.getElementById('tableViewControls');
        
        if (!container) return;
        
        // Xóa tất cả các lớp chế độ hiển thị
        container.classList.remove('card-view', 'list-view', 'table-view');
        
        // Thêm lớp chế độ hiển thị mới
        container.classList.add(mode);
        
        // Cập nhật trạng thái nút chuyển đổi
        if (toggleBtn) {
            if (mode === 'list-view') {
                toggleBtn.innerHTML = '<i class="bi bi-grid"></i> Xem dạng thẻ';
            } else {
                toggleBtn.innerHTML = '<i class="bi bi-list"></i> Xem dạng danh sách';
            }
        }
        
        // Cập nhật nút chuyển đổi chế độ xem nếu có
        const cardBtn = document.getElementById('cardViewBtn');
        const listBtn = document.getElementById('listViewBtn');
        const tableBtn = document.getElementById('tableViewBtn');
        
        if (cardBtn && listBtn && tableBtn) {
            cardBtn.classList.toggle('active', mode === 'card-view');
            listBtn.classList.toggle('active', mode === 'list-view');
            tableBtn.classList.toggle('active', mode === 'table-view');
        }
        
        // Hiển thị/ẩn các điều khiển bổ sung cho chế độ xem bảng
        if (tableViewControls) {
            tableViewControls.style.display = mode === 'table-view' ? 'block' : 'none';
        }
        
        // Render lại dữ liệu với chế độ hiển thị mới
        this.renderContent();
        
        // Cập nhật URL nếu cần
        const url = new URL(window.location.href);
        url.searchParams.set('mode', mode.replace('-view', ''));
        window.history.replaceState({}, '', url);
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
        this.renderContent();
    }
    
    renderContent() {
        if (this.displayMode === 'table-view') {
            this.renderTableData();
        } else {
            this.renderCoins();
        }
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
            this.renderContent();
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
            
            // Không tạo dữ liệu mẫu nếu không load được
            console.error(`❌ Không tải được dữ liệu cho ${symbol}`);
        }
    }
    
    processSymbolData(rawData) {
        // Xử lý và làm sạch dữ liệu
        const processed = {
            symbol: rawData.symbol,
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
                    date: item.date_timestamp ? new Date(item.date_timestamp) : null,
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
    
    renderCoins() {
        const container = document.getElementById('coinsContainer');
        if (!container) {
            console.error('Không tìm thấy phần tử #coinsContainer');
            return;
        }
        
        container.innerHTML = '';
        
        // Use loaded symbols if available
        const symbolsToRender = Object.keys(this.coinsData);
        
        if (symbolsToRender.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">Không có dữ liệu để hiển thị</div>';
            return;
        }
            
        const isListView = this.displayMode === 'list-view';
        
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
        let chartData = this.prepareChartData(symbol, data);
        
        if (chartData.length === 0) {
            // Draw "no data" message
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Không có dữ liệu', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Giới hạn số lượng điểm dữ liệu
        if (this.currentView === 'hourly') {
            // Lấy tối đa 24 điểm dữ liệu cho chế độ giờ
            chartData = chartData.slice(-24);
        } else {
            // Lấy tối đa 30 điểm dữ liệu cho chế độ ngày
            chartData = chartData.slice(-30);
        }
        
        // Tạo nhãn thời gian cho trục x
        const labels = [];
        if (this.currentView === 'hourly') {
            // Tạo nhãn giờ: 00:00, 01:00, ...
            for (let i = 0; i < 24; i++) {
                const hour = i.toString().padStart(2, '0');
                labels.push(`${hour}:00`);
            }
        } else {
            // Tạo nhãn ngày: DD/MM
            const endDate = new Date();
            for (let i = 29; i >= 0; i--) {
                const date = new Date(endDate);
                date.setDate(date.getDate() - i);
                const day = date.getDate().toString().padStart(2, '0');
                const month = (date.getMonth() + 1).toString().padStart(2, '0');
                labels.push(`${day}/${month}`);
            }
        }
        
        // Kiểm tra và đảm bảo số lượng điểm dữ liệu khớp với số lượng nhãn
        if (chartData.length !== labels.length) {
            console.warn(`Số lượng điểm dữ liệu (${chartData.length}) khác với số lượng nhãn (${labels.length})`);
            
            // Nếu thiếu điểm dữ liệu, cắt bớt labels cho khớp với dữ liệu
            if (chartData.length < labels.length) {
                labels.splice(0, labels.length - chartData.length);
            } else {
                // Nếu thừa điểm dữ liệu, giữ lại các điểm mới nhất
                chartData = chartData.slice(-labels.length);
            }
        }
        
        // Tính toán giá trị min và max cho trục y (Open Interest)
        const oiValues = chartData.map(item => item.oi).filter(v => v !== null && v !== undefined);
        const minOI = oiValues.length > 0 ? Math.min(...oiValues) * 0.95 : 0; // Giảm 5% để có khoảng cách
        const maxOI = oiValues.length > 0 ? Math.max(...oiValues) * 1.05 : 0; // Tăng 5% để có khoảng cách
        
        // Tính toán giá trị min và max cho trục y1 (Volume)
        const volumeValues = chartData.map(item => item.volume).filter(v => v !== null && v !== undefined);
        const minVolume = volumeValues.length > 0 ? Math.min(...volumeValues) * 0.95 : 0;
        const maxVolume = volumeValues.length > 0 ? Math.max(...volumeValues) * 1.05 : 0;
        
        // Kiểm tra xem Chart đã được định nghĩa chưa
        if (typeof Chart === 'undefined') {
            console.error('Chart.js chưa được tải! Hãy kiểm tra thẻ script trong HTML.');
            ctx.fillStyle = '#dc3545';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Lỗi: Chart.js chưa được tải', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Thay đổi loại biểu đồ từ 'line' sang 'bar'
        try {
            this.charts[symbol] = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Open Interest',
                            data: chartData.map(item => item.oi),
                            backgroundColor: 'rgba(245, 87, 108, 0.7)',
                            borderColor: '#f5576c',
                            borderWidth: 1,
                            yAxisID: 'y',
                            barPercentage: 0.9, // Tăng độ rộng của cột
                            categoryPercentage: 0.8, // Giảm khoảng cách giữa các nhóm cột
                            order: 1
                        },
                        {
                            label: 'Volume',
                            data: chartData.map(item => item.volume),
                            backgroundColor: 'rgba(0, 242, 254, 0.7)',
                            borderColor: '#00f2fe',
                            borderWidth: 1,
                            yAxisID: 'y1',
                            barPercentage: 0.9, // Tăng độ rộng của cột
                            categoryPercentage: 0.8, // Giảm khoảng cách giữa các nhóm cột
                            order: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1000, // Hiệu ứng animation rõ ràng
                        easing: 'easeOutQuad'
                    },
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
                            type: 'category', // Thay đổi từ 'time' sang 'category' để hiển thị rõ hơn
                            grid: {
                                display: false
                            },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0,
                                font: {
                                    size: 10
                                },
                                autoSkip: true,
                                maxTicksLimit: this.currentView === 'hourly' ? 12 : 15 // Hiển thị số nhãn phù hợp
                            }
                        },
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            // Đặt min và max dựa trên dữ liệu thực tế
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
                            // Đặt min và max dựa trên dữ liệu thực tế
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
        } catch (error) {
            console.error('Lỗi khi tạo biểu đồ:', error);
            ctx.fillStyle = '#dc3545';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Lỗi: ' + error.message, canvas.width / 2, canvas.height / 2);
        }
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
        let chartData = this.prepareChartData(symbol, data);
        
        if (chartData.length === 0) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Không có dữ liệu', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Giới hạn số lượng điểm dữ liệu - 6 điểm để biểu đồ mini rõ ràng hơn
        if (chartData.length > 6) {
            const step = Math.floor(chartData.length / 6);
            const newData = [];
            for (let i = 0; i < chartData.length; i += step) {
                if (newData.length < 6) {
                    newData.push(chartData[i]);
                }
            }
            // Đảm bảo luôn có điểm dữ liệu mới nhất
            if (newData.length > 0 && chartData.length > 0) {
                newData[newData.length - 1] = chartData[chartData.length - 1];
            }
            chartData = newData;
        }
        
        // Kiểm tra xem Chart đã được định nghĩa chưa
        if (typeof Chart === 'undefined') {
            console.error('Chart.js chưa được tải! Hãy kiểm tra thẻ script trong HTML.');
            ctx.fillStyle = '#dc3545';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Lỗi: Chart.js chưa được tải', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // Cấu hình mini chart đơn giản hơn với dạng cột (rõ ràng hơn)
        try {
            this.charts[`mini-${symbol}`] = new Chart(ctx, {
                type: 'bar', // Đảm bảo luôn dùng bar chart
                data: {
                    datasets: [
                        {
                            label: 'OI',
                            data: chartData.map(item => ({ x: item.x, y: item.oi })),
                            backgroundColor: 'rgba(245, 87, 108, 0.8)', // Tăng độ đậm
                            borderColor: '#f5576c',
                            borderWidth: 1,
                            barPercentage: 0.9, // Tăng độ rộng của cột
                            categoryPercentage: 0.9 // Tăng độ rộng của cột
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1000, // Hiệu ứng animation rõ ràng
                        easing: 'easeOutQuad'
                    },
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
                            type: 'category', // Thay đổi từ 'time' sang 'category' để hiển thị rõ hơn
                            display: false,
                            grid: {
                                display: false
                            }
                        },
                        y: {
                            display: false,
                            beginAtZero: false,
                            grid: {
                                display: false
                            }
                        }
                    },
                    layout: {
                        padding: 0
                    }
                }
            });
        } catch (error) {
            console.error('Lỗi khi tạo biểu đồ mini:', error);
            ctx.fillStyle = '#dc3545';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Lỗi: ' + error.message, canvas.width / 2, canvas.height / 2);
        }
    }
    
    prepareChartData(symbol, data) {
        let chartData = [];
        
        if (this.currentView === 'hourly') {
            // Data cho view theo giờ (24h)
            const hourlyData = data.tracking_24h || [];
            
            // Lọc dữ liệu không hợp lệ - luôn sử dụng quote_volume và open_interest_value
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
        } else {
            // Ưu tiên sử dụng tracking_30d nếu có
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
                    
                    // Ưu tiên sử dụng open_interest_value
                    mergedData[date].oi = item.open_interest_value || item.open_interest || 0;
                    mergedData[date].timestamp = item.timestamp;
                });
                
                dailyKlines.forEach(item => {
                    if (!item || !item.open_time) return;
                    
                    const date = item.open_time.split('T')[0];
                    if (!mergedData[date]) mergedData[date] = {};
                    
                    // Ưu tiên sử dụng quote_volume
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
    
    // Render dữ liệu dạng bảng theo ngày
    renderTableData() {
        const tableViewContainer = document.getElementById('tableViewContainer');
        if (!tableViewContainer) {
            console.warn('Không tìm thấy phần tử #tableViewContainer');
            return;
        }
        
        // Kiểm tra xem có dữ liệu không
        if (Object.keys(this.coinsData).length === 0) {
            tableViewContainer.innerHTML = '<div class="alert alert-warning">Không có dữ liệu để hiển thị</div>';
            return;
        }
        
        // Lấy các ngày cần hiển thị
        const dates = this.generateDateArray(this.timeRange);
        
        // Tạo bảng
        const table = document.createElement('table');
        table.className = 'data-table';
        table.id = 'dataTable';
        
        // Tạo header của bảng
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        headerRow.id = 'tableHeader';
        
        // Thêm cột đầu tiên (Symbol)
        const symbolHeader = document.createElement('th');
        symbolHeader.className = 'symbol-cell';
        symbolHeader.textContent = 'Symbol';
        headerRow.appendChild(symbolHeader);
        
        // Thêm các cột ngày
        dates.forEach(date => {
            const th = document.createElement('th');
            th.textContent = this.formatDate(date);
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Tạo body của bảng
        const tbody = document.createElement('tbody');
        tbody.id = 'tableBody';
        
        // Lấy danh sách symbol
        const symbols = Object.keys(this.coinsData);
        
        // Render từng dòng
        symbols.forEach(symbol => {
            const row = document.createElement('tr');
            
            // Thêm ô symbol
            const symbolCell = document.createElement('td');
            symbolCell.className = 'symbol-cell';
            symbolCell.textContent = symbol.replace('USDT', '');
            row.appendChild(symbolCell);
            
            // Thêm các ô dữ liệu
            dates.forEach(date => {
                const td = document.createElement('td');
                const data = this.getDataForDate(symbol, date);
                
                td.innerHTML = this.formatCellContent(data);
                
                row.appendChild(td);
            });
            
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        
        // Xóa nội dung cũ và thêm bảng mới
        tableViewContainer.innerHTML = '';
        tableViewContainer.appendChild(table);
        
        // Hiển thị container
        this.hideLoading();
        document.getElementById('contentDiv')?.classList.remove('d-none');
    }
    
    generateDateArray(days) {
        const dates = [];
        const today = new Date();
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            dates.push(date);
        }
        
        return dates;
    }
    
    getDataForDate(symbol, date) {
        const data = this.coinsData[symbol];
        if (!data || !data.tracking_30d) return null;
        
        // Format date as yyyy-MM-dd for comparison
        const dateStr = date.toISOString().split('T')[0];
        
        // Find data for the date
        return data.tracking_30d.find(item => {
            const itemDate = item.date_timestamp ? item.date_timestamp.split('T')[0] : 
                             (item.date ? item.date.toISOString().split('T')[0] : null);
            return itemDate === dateStr;
        });
    }
    
    formatCellContent(data) {
        if (!data) return '—';
        
        let content = '';
        
        switch (this.dataType) {
            case 'oi':
                // Chỉ hiển thị OI
                content = `<div class="oi-value">${this.formatNumber(data.avg_open_interest_value || data.open_interest_value || 0)}</div>`;
                if (data.oi_change_1d) {
                    content += `<div class="${data.oi_change_1d >= 0 ? 'positive-change' : 'negative-change'}">
                                ${data.oi_change_1d >= 0 ? '+' : ''}${data.oi_change_1d.toFixed(2)}%
                                </div>`;
                }
                break;
                
            case 'volume':
                // Chỉ hiển thị Volume
                content = `<div class="volume-value">${this.formatNumber(data.quote_volume || 0)}</div>`;
                if (data.volume_change_1d) {
                    content += `<div class="${data.volume_change_1d >= 0 ? 'positive-change' : 'negative-change'}">
                                ${data.volume_change_1d >= 0 ? '+' : ''}${data.volume_change_1d.toFixed(2)}%
                                </div>`;
                }
                break;
                
            case 'both':
                // Hiển thị cả OI và Volume
                content = `<div class="oi-value">${this.formatNumber(data.avg_open_interest_value || data.open_interest_value || 0)}</div>`;
                if (data.oi_change_1d) {
                    content += `<div class="${data.oi_change_1d >= 0 ? 'positive-change' : 'negative-change'}">
                                ${data.oi_change_1d >= 0 ? '+' : ''}${data.oi_change_1d.toFixed(2)}%
                                </div>`;
                }
                
                content += `<hr style="margin: 5px 0">`;
                
                content += `<div class="volume-value">${this.formatNumber(data.quote_volume || 0)}</div>`;
                if (data.volume_change_1d) {
                    content += `<div class="${data.volume_change_1d >= 0 ? 'positive-change' : 'negative-change'}">
                                ${data.volume_change_1d >= 0 ? '+' : ''}${data.volume_change_1d.toFixed(2)}%
                                </div>`;
                }
                break;
        }
        
        return content;
    }
    
    formatDate(date) {
        const day = date.getDate().toString().padStart(2, '0');
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        return `${day}/${month}`;
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
                try {
                    chart.destroy();
                } catch (e) {
                    console.warn('Error destroying chart:', e);
                }
            }
        });
        
        this.charts = {};
    }
}

// Khởi tạo monitor khi DOM ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Kiểm tra xem Chart.js đã được tải chưa
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js chưa được tải, đang tải...');
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
            script.onload = function() {
                console.log('Đã tải Chart.js, khởi tạo SimpleOIVolumeMonitor');
                window.simpleMonitor = new SimpleOIVolumeMonitor();
            };
            document.head.appendChild(script);
        } else {
            window.simpleMonitor = new SimpleOIVolumeMonitor();
        }
    } catch (error) {
        console.error('Lỗi khi khởi tạo SimpleOIVolumeMonitor:', error);
        alert('Đã xảy ra lỗi khi khởi tạo ứng dụng. Xem Console để biết thêm chi tiết.');
    }
});

// Cleanup khi unload
window.addEventListener('beforeunload', function() {
    if (window.simpleMonitor) {
        window.simpleMonitor.destroy();
    }
});