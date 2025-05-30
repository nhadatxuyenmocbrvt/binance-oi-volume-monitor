/**
 * Simple OI & Volume Monitor JavaScript
 * Tối ưu cho hiển thị dạng bảng
 * Version 3.0.2 - Chỉ hiển thị dữ liệu dạng bảng với thời gian mới nhất ở đầu tiên
 */

class SimpleOIVolumeMonitor {
    constructor() {
        this.currentView = 'daily'; // Mặc định view theo ngày
        this.displayMode = 'table-view'; // Chỉ sử dụng chế độ bảng
        this.coinsData = {};
        this.charts = {};
        this.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        this.updateInterval = null;
        this.dataSource = null; // Will be detected
        this.dataType = 'oi'; // 'oi', 'volume', 'both'
        this.timeRange = 30; // Số ngày hiển thị trong bảng
        
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
        
        // View switcher buttons (hourly/daily)
        document.getElementById('hourlyBtn')?.addEventListener('click', () => {
            this.switchView('hourly');
        });
        
        document.getElementById('dailyBtn')?.addEventListener('click', () => {
            this.switchView('daily');
        });
        
        // Table view controls
        document.getElementById('oiRadio')?.addEventListener('change', () => {
            this.dataType = 'oi';
            this.renderTableData();
        });
        
        document.getElementById('volumeRadio')?.addEventListener('change', () => {
            this.dataType = 'volume';
            this.renderTableData();
        });
        
        document.getElementById('bothRadio')?.addEventListener('change', () => {
            this.dataType = 'both';
            this.renderTableData();
        });
        
        document.getElementById('timeRangeSelect')?.addEventListener('change', (e) => {
            this.timeRange = parseInt(e.target.value);
            this.renderTableData();
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
        this.renderTableData();
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
            this.renderTableData();
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
            
            // Raw GitHub URLs
            'https://raw.githubusercontent.com/nhadatxuyenmocbrvt/binance-oi-volume-monitor/main/docs/assets/data/',
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
            
            // Đảm bảo giá trị open_interest_value là số
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
            
            // Đảm bảo giá trị số trong trạng thái số (không phải chuỗi)
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
        
        // Xử lý dữ liệu tracking_24h
        if (processed.tracking_24h.length > 0) {
            processed.tracking_24h.sort((a, b) => new Date(a.hour_timestamp) - new Date(b.hour_timestamp));
            
            // Đảm bảo giá trị số trong trạng thái số
            processed.tracking_24h = processed.tracking_24h.map(item => {
                return {
                    ...item,
                    price: parseFloat(item.price),
                    volume: parseFloat(item.volume),
                    quote_volume: parseFloat(item.quote_volume || item.volume),
                    open_interest: parseFloat(item.open_interest),
                    open_interest_value: parseFloat(item.open_interest_value || item.open_interest),
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
        
        // Lấy các ngày hoặc giờ cần hiển thị
        const dates = this.generateDateArray(this.timeRange);
        
        // Đảo ngược thứ tự thời gian: mới nhất ở đầu tiên, xa nhất ở cuối
        dates.reverse();
        
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
        
        // Thêm các cột ngày (thời gian mới nhất ở trước)
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
            
            // Thêm các ô dữ liệu theo thứ tự thời gian mới nhất trước
            dates.forEach(date => {
                const td = document.createElement('td');
                
                // Lấy dữ liệu cho ngày hoặc giờ tùy theo chế độ xem
                let data = null;
                
                if (this.currentView === 'daily') {
                    data = this.getDataForDate(symbol, date);
                } else {
                    // Nếu là chế độ xem theo giờ, lấy dữ liệu 24h gần nhất
                    data = this.getHourlyData(symbol, date);
                }
                
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
        
        if (this.currentView === 'daily') {
            // Nếu là chế độ xem theo ngày, tạo mảng ngày
            for (let i = 0; i < days; i++) {
                const date = new Date(today);
                date.setDate(date.getDate() - i);
                dates.push(date);
            }
        } else {
            // Nếu là chế độ xem theo giờ, tạo mảng giờ (24 giờ gần nhất)
            const hours = Math.min(days, 24); // Giới hạn ở 24 giờ
            for (let i = 0; i < hours; i++) {
                const date = new Date(today);
                date.setHours(date.getHours() - i);
                dates.push(date);
            }
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
    
    getHourlyData(symbol, date) {
        const data = this.coinsData[symbol];
        if (!data || !data.tracking_24h || data.tracking_24h.length === 0) return null;
        
        // Tạo timestamp cho giờ cần tìm (chỉ giữ giờ, phút và giây đặt về 0)
        const targetHour = new Date(date);
        targetHour.setMinutes(0, 0, 0);
        
        // Tìm dữ liệu giờ gần nhất
        const targetTimestamp = targetHour.toISOString();
        
        return data.tracking_24h.find(item => {
            if (!item.hour_timestamp) return false;
            
            const itemHour = new Date(item.hour_timestamp);
            itemHour.setMinutes(0, 0, 0);
            
            return itemHour.toISOString() === targetTimestamp;
        });
    }
    
    formatCellContent(data) {
        if (!data) return '—';
        
        let content = '';
        
        // Xác định giá trị OI và Volume dựa trên chế độ xem (hourly/daily)
        const oiValue = this.currentView === 'daily' 
            ? (data.avg_open_interest_value || data.open_interest_value || 0)
            : (data.open_interest_value || data.open_interest || 0);
            
        const volumeValue = this.currentView === 'daily'
            ? (data.quote_volume || 0)
            : (data.quote_volume || data.volume || 0);
            
        const oiChange = this.currentView === 'daily'
            ? (data.oi_change_1d || 0)
            : (data.oi_change_1h || 0);
            
        const volumeChange = this.currentView === 'daily'
            ? (data.volume_change_1d || 0)
            : (data.volume_change_1h || 0);
        
        switch (this.dataType) {
            case 'oi':
                // Chỉ hiển thị OI
                content = `<div class="oi-value">${this.formatNumber(oiValue)}</div>`;
                if (oiChange) {
                    content += `<div class="${oiChange >= 0 ? 'positive-change' : 'negative-change'}">
                                ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                                </div>`;
                }
                break;
                
            case 'volume':
                // Chỉ hiển thị Volume
                content = `<div class="volume-value">${this.formatNumber(volumeValue)}</div>`;
                if (volumeChange) {
                    content += `<div class="${volumeChange >= 0 ? 'positive-change' : 'negative-change'}">
                                ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                                </div>`;
                }
                break;
                
            case 'both':
                // Hiển thị cả OI và Volume
                content = `<div class="oi-value">${this.formatNumber(oiValue)}</div>`;
                if (oiChange) {
                    content += `<div class="${oiChange >= 0 ? 'positive-change' : 'negative-change'}">
                                ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                                </div>`;
                }
                
                content += `<hr style="margin: 5px 0">`;
                
                content += `<div class="volume-value">${this.formatNumber(volumeValue)}</div>`;
                if (volumeChange) {
                    content += `<div class="${volumeChange >= 0 ? 'positive-change' : 'negative-change'}">
                                ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                                </div>`;
                }
                break;
        }
        
        return content;
    }
    
    formatDate(date) {
        if (this.currentView === 'daily') {
            // Format: DD/MM
            const day = date.getDate().toString().padStart(2, '0');
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            return `${day}/${month}`;
        } else {
            // Format: HH:00
            const hour = date.getHours().toString().padStart(2, '0');
            return `${hour}:00`;
        }
    }
    
    // Utility functions
    calculateChange(current, previous) {
        if (!current || !previous || previous === 0) return 0;
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