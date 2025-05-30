/**
 * Simple OI & Volume Monitor JavaScript
 * Tối ưu cho hiển thị dạng bảng
 * Version 3.0.5 - Sửa lỗi hiển thị % thay đổi
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
        this.timeRange = 14; // Số ngày/giờ hiển thị trong bảng
        this.dailyChangeData = {}; // Lưu trữ dữ liệu % thay đổi theo ngày
        
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
            
            // Tính toán % thay đổi dựa trên dữ liệu thực tế
            this.calculateAllChanges();
            
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
    
    // Tính toán phần trăm thay đổi cho tất cả các coins
    calculateAllChanges() {
        const symbols = Object.keys(this.coinsData);
        
        // Xóa dữ liệu thay đổi cũ
        this.dailyChangeData = {};
        
        symbols.forEach(symbol => {
            this.dailyChangeData[symbol] = {};
            
            // Tính toán % thay đổi cho dữ liệu theo ngày
            this.calculateDailyChanges(symbol);
            
            // Tính toán % thay đổi cho dữ liệu theo giờ
            this.calculateHourlyChanges(symbol);
        });
    }
    
    // Tính toán % thay đổi dữ liệu theo ngày
    calculateDailyChanges(symbol) {
        const data = this.coinsData[symbol];
        if (!data || !data.tracking_30d || data.tracking_30d.length < 2) return;
        
        // Sắp xếp dữ liệu theo thời gian
        const sortedData = [...data.tracking_30d].sort((a, b) => 
            new Date(a.date_timestamp) - new Date(b.date_timestamp)
        );
        
        this.dailyChangeData[symbol].daily = {};
        
        // Tính % thay đổi cho mỗi ngày
        for (let i = 1; i < sortedData.length; i++) {
            const current = sortedData[i];
            const previous = sortedData[i-1];
            
            // Lấy ngày để làm key
            const currentDate = current.date_timestamp ? current.date_timestamp.split('T')[0] : null;
            if (!currentDate) continue;
            
            // Tính % thay đổi OI
            const currentOI = current.avg_open_interest_value || current.open_interest_value || 0;
            const previousOI = previous.avg_open_interest_value || previous.open_interest_value || 0;
            
            let oiChange = 0;
            if (previousOI > 0) {
                oiChange = ((currentOI - previousOI) / previousOI) * 100;
            }
            
            // Tính % thay đổi Volume
            const currentVolume = current.quote_volume || 0;
            const previousVolume = previous.quote_volume || 0;
            
            let volumeChange = 0;
            if (previousVolume > 0) {
                volumeChange = ((currentVolume - previousVolume) / previousVolume) * 100;
            }
            
            // Lưu vào đối tượng dailyChangeData
            this.dailyChangeData[symbol].daily[currentDate] = {
                oiChange: oiChange,
                volumeChange: volumeChange
            };
            
            console.log(`${symbol} - ${currentDate}: OI change = ${oiChange.toFixed(2)}%, Volume change = ${volumeChange.toFixed(2)}%`);
        }
    }
    
    // Tính toán % thay đổi dữ liệu theo giờ
    calculateHourlyChanges(symbol) {
        const data = this.coinsData[symbol];
        if (!data || !data.tracking_24h || data.tracking_24h.length < 2) return;
        
        // Sắp xếp dữ liệu theo thời gian
        const sortedData = [...data.tracking_24h].sort((a, b) => 
            new Date(a.hour_timestamp) - new Date(b.hour_timestamp)
        );
        
        this.dailyChangeData[symbol].hourly = {};
        
        // Tính % thay đổi cho mỗi giờ
        for (let i = 1; i < sortedData.length; i++) {
            const current = sortedData[i];
            const previous = sortedData[i-1];
            
            // Lấy giờ để làm key
            if (!current.hour_timestamp) continue;
            const hourTime = new Date(current.hour_timestamp);
            const hourKey = hourTime.getHours().toString().padStart(2, '0');
            
            // Tính % thay đổi OI
            const currentOI = current.open_interest_value || current.open_interest || 0;
            const previousOI = previous.open_interest_value || previous.open_interest || 0;
            
            let oiChange = 0;
            if (previousOI > 0) {
                oiChange = ((currentOI - previousOI) / previousOI) * 100;
            }
            
            // Tính % thay đổi Volume
            const currentVolume = current.quote_volume || current.volume || 0;
            const previousVolume = previous.quote_volume || previous.volume || 0;
            
            let volumeChange = 0;
            if (previousVolume > 0) {
                volumeChange = ((currentVolume - previousVolume) / previousVolume) * 100;
            }
            
            // Lưu vào đối tượng dailyChangeData
            this.dailyChangeData[symbol].hourly[hourKey] = {
                oiChange: oiChange,
                volumeChange: volumeChange
            };
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
                    price_change_1d: parseFloat(item.price_change_1d || 0),
                    volume_change_1d: parseFloat(item.volume_change_1d || 0),
                    oi_change_1d: parseFloat(item.oi_change_1d || 0)
                };
            });
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
                    price_change_1h: parseFloat(item.price_change_1h || 0),
                    volume_change_1h: parseFloat(item.volume_change_1h || 0),
                    oi_change_1h: parseFloat(item.oi_change_1h || 0)
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
    
    // Render dữ liệu dạng bảng theo ngày hoặc giờ
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
        
        // Lấy các ngày/giờ cần hiển thị
        let timePoints = this.generateTimePoints(this.timeRange);
        
        // Đảm bảo thời gian mới nhất ở đầu (trái) và cũ nhất ở cuối (phải)
        timePoints = timePoints.sort((a, b) => b - a);
        
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
        
        // Thêm các cột thời gian, mới nhất ở trái
        timePoints.forEach(time => {
            const th = document.createElement('th');
            th.textContent = this.formatTimePoint(time);
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
            
            // Thêm các ô dữ liệu, thời gian mới nhất ở trái
            timePoints.forEach(time => {
                const td = document.createElement('td');
                
                // Lấy dữ liệu cho thời điểm cụ thể
                let data = null;
                let changeData = null;
                
                if (this.currentView === 'daily') {
                    data = this.getDataForDate(symbol, time);
                    
                    // Lấy dữ liệu % thay đổi
                    const dateStr = time.toISOString().split('T')[0];
                    if (this.dailyChangeData[symbol] && this.dailyChangeData[symbol].daily) {
                        changeData = this.dailyChangeData[symbol].daily[dateStr];
                    }
                } else {
                    data = this.getHourlyData(symbol, time);
                    
                    // Lấy dữ liệu % thay đổi
                    const hourKey = time.getHours().toString().padStart(2, '0');
                    if (this.dailyChangeData[symbol] && this.dailyChangeData[symbol].hourly) {
                        changeData = this.dailyChangeData[symbol].hourly[hourKey];
                    }
                }
                
                td.innerHTML = this.formatCellContent(data, changeData);
                
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
    
    generateTimePoints(count) {
        const timePoints = [];
        const now = new Date();
        
        if (this.currentView === 'daily') {
            // Tạo mảng các ngày, từ hiện tại về quá khứ
            for (let i = 0; i < count; i++) {
                const date = new Date(now);
                date.setDate(date.getDate() - i);
                // Reset về đầu ngày để so sánh chính xác
                date.setHours(0, 0, 0, 0);
                timePoints.push(date);
            }
        } else {
            // Tạo mảng các giờ, từ hiện tại về quá khứ
            const hours = Math.min(count, 24); // Giới hạn ở 24 giờ
            for (let i = 0; i < hours; i++) {
                const date = new Date(now);
                date.setHours(date.getHours() - i);
                // Reset về đầu giờ
                date.setMinutes(0, 0, 0);
                timePoints.push(date);
            }
        }
        
        return timePoints;
    }
    
    formatTimePoint(date) {
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
        
        // Tìm dữ liệu cho giờ cụ thể
        const targetHour = date.getHours();
        
        return data.tracking_24h.find(item => {
            if (!item.hour_timestamp) return false;
            
            const itemDate = new Date(item.hour_timestamp);
            return itemDate.getHours() === targetHour;
        });
    }
    
    formatCellContent(data, changeData) {
        if (!data) return '—';
        
        let content = '';
        
        // Xác định giá trị OI và Volume dựa trên chế độ xem (hourly/daily)
        const oiValue = this.currentView === 'daily' 
            ? (data.avg_open_interest_value || data.open_interest_value || 0)
            : (data.open_interest_value || data.open_interest || 0);
            
        const volumeValue = this.currentView === 'daily'
            ? (data.quote_volume || 0)
            : (data.quote_volume || data.volume || 0);
        
        // Lấy % thay đổi từ dữ liệu tính toán
        let oiChange = 0;
        let volumeChange = 0;
        
        if (changeData) {
            oiChange = changeData.oiChange || 0;
            volumeChange = changeData.volumeChange || 0;
        }
        
        switch (this.dataType) {
            case 'oi':
                // Chỉ hiển thị OI
                content = `<div class="oi-value">${this.formatNumber(oiValue)}</div>`;
                // Hiển thị phần trăm thay đổi
                content += `<div class="${oiChange >= 0 ? 'positive-change' : 'negative-change'}">
                            ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                            </div>`;
                break;
                
            case 'volume':
                // Chỉ hiển thị Volume
                content = `<div class="volume-value">${this.formatNumber(volumeValue)}</div>`;
                // Hiển thị phần trăm thay đổi
                content += `<div class="${volumeChange >= 0 ? 'positive-change' : 'negative-change'}">
                            ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                            </div>`;
                break;
                
            case 'both':
                // Hiển thị cả OI và Volume
                content = `<div class="oi-value">${this.formatNumber(oiValue)}</div>`;
                // Hiển thị phần trăm thay đổi OI
                content += `<div class="${oiChange >= 0 ? 'positive-change' : 'negative-change'}">
                            ${oiChange >= 0 ? '+' : ''}${oiChange.toFixed(2)}%
                            </div>`;
                
                content += `<hr style="margin: 5px 0">`;
                
                content += `<div class="volume-value">${this.formatNumber(volumeValue)}</div>`;
                // Hiển thị phần trăm thay đổi Volume
                content += `<div class="${volumeChange >= 0 ? 'positive-change' : 'negative-change'}">
                            ${volumeChange >= 0 ? '+' : ''}${volumeChange.toFixed(2)}%
                            </div>`;
                break;
        }
        
        return content;
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