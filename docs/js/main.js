/**
 * Hệ Thống Theo Dõi OI & Volume Binance - Phiên Bản Cải Tiến V2
 * Tác giả: AI Assistant
 * Mô tả: Hệ thống theo dõi với error handling, performance optimization và UX tốt hơn
 */

class HeThongTheoDoi_Binance_VietNam_V2 {
    constructor() {
        // Cấu hình cơ bản
        this.khungThoiGianHienTai = '1h';
        this.giaiDoanHienTai = '7d';
        this.cacBieuDo = new Map(); // Sử dụng Map thay vì object
        this.danhSachCoin = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        
        // Kho lưu trữ dữ liệu
        this.khoLuuTru = {
            thoiGianThuc: null,
            lichSu: new Map(),
            batThuong: null,
            capNhatLanCuoi: null,
            hourly24h: null,
            trangThaiKetNoi: 'disconnected'
        };
        
        // Cấu hình error handling
        this.soLanThayLoi = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 giây
        
        // Cấu hình performance
        this.debounceTimers = new Map();
        this.requestQueue = [];
        this.isProcessingQueue = false;
        
        // Cấu hình UI
        this.toastContainer = null;
        this.loadingOverlay = null;
        
        // Khởi tạo hệ thống
        this.khoiTao();
    }

    // ================================
    // KHỞI TẠO VÀ SETUP
    // ================================

    async khoiTao() {
        try {
            console.log('🚀 Khởi tạo hệ thống theo dõi Binance V2...');
            
            // Thiết lập UI components
            this.thietLapUIComponents();
            
            // Hiển thị trạng thái kết nối
            this.hienThiTrangThaiKetNoi('connecting');
            
            // Gắn sự kiện
            this.ganCacSuKien();
            
            // Tải dữ liệu ban đầu
            await this.taiDuLieuBanDau();
            
            // Thiết lập auto-refresh
            this.thietLapTuDongLamMoi();
            
            // Thiết lập WebSocket (future feature)
            this.thietLapWebSocket();
            
            // Hiển thị trạng thái kết nối thành công
            this.hienThiTrangThaiKetNoi('connected');
            
            console.log('✅ Hệ thống đã khởi tạo thành công');
            
        } catch (error) {
            console.error('❌ Lỗi khởi tạo hệ thống:', error);
            this.hienThiTrangThaiKetNoi('error');
            this.hienThiThongBaoLoi('Không thể khởi tạo hệ thống. Đang thử lại...');
            
            // Retry sau 5 giây
            setTimeout(() => this.khoiTao(), 5000);
        }
    }

    thietLapUIComponents() {
        // Tạo toast container
        this.taoToastContainer();
        
        // Tạo loading overlay
        this.taoLoadingOverlay();
        
        // Tạo connection status
        this.taoConnectionStatus();
        
        // Thêm CSS cần thiết
        this.themCSSBoSung();
    }

    // ================================
    // UI COMPONENTS
    // ================================

    taoToastContainer() {
        if (document.getElementById('toastContainer')) return;
        
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        this.toastContainer = container;
    }

    taoLoadingOverlay() {
        if (document.getElementById('globalLoadingOverlay')) return;
        
        const overlay = document.createElement('div');
        overlay.id = 'globalLoadingOverlay';
        overlay.className = 'global-loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" style="width: 3rem; height: 3rem;"></div>
                <h5 class="text-white">Đang tải dữ liệu 24H...</h5>
                <p class="text-muted">Vui lòng chờ trong giây lát</p>
                <div class="progress" style="width: 300px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%" id="loadingProgress"></div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        this.loadingOverlay = overlay;
    }

    taoConnectionStatus() {
        if (document.getElementById('connectionStatus')) return;
        
        const status = document.createElement('div');
        status.id = 'connectionStatus';
        status.className = 'connection-status';
        document.body.appendChild(status);
    }

    themCSSBoSung() {
        if (document.getElementById('enhanced-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'enhanced-styles';
        style.textContent = `
            .connection-status {
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 8px 12px;
                border-radius: 20px;
                font-size: 0.8rem;
                font-weight: 500;
                z-index: 1000;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .status-connecting {
                background: linear-gradient(135deg, #ffc107, #fd7e14);
                color: white;
                animation: pulse 2s infinite;
            }
            
            .status-connected {
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
            }
            
            .status-error {
                background: linear-gradient(135deg, #dc3545, #fd7e14);
                color: white;
                animation: shake 0.5s ease-in-out;
            }
            
            .global-loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                backdrop-filter: blur(5px);
            }
            
            .loading-content {
                text-align: center;
                color: white;
                padding: 2rem;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.1);
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-5px); }
                75% { transform: translateX(5px); }
            }
            
            .mini-chart-container {
                width: 120px;
                height: 50px;
                position: relative;
                margin: 0 auto;
                background: rgba(247, 147, 30, 0.05);
                border-radius: 8px;
                padding: 5px;
                border: 1px solid rgba(247, 147, 30, 0.1);
                transition: all 0.3s ease;
            }
            
            .mini-chart-container:hover {
                transform: scale(1.05);
                box-shadow: 0 4px 12px rgba(247, 147, 30, 0.2);
            }
            
            .chart-cell {
                width: 140px;
                text-align: center;
                padding: 8px 5px !important;
            }
            
            .symbol-row {
                transition: all 0.3s ease;
            }
            
            .symbol-row:hover {
                background-color: rgba(247, 147, 30, 0.03) !important;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .error-message {
                background: linear-gradient(135deg, #f8d7da, #f5c6cb);
                border: 1px solid #f1aeb5;
                color: #721c24;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                text-align: center;
            }
            
            .retry-button {
                background: linear-gradient(135deg, #17a2b8, #138496);
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            
            .retry-button:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 8px rgba(23, 162, 184, 0.3);
            }
        `;
        document.head.appendChild(style);
    }

    // ================================
    // TRẠNG THÁI VÀ THÔNG BÁO
    // ================================

    hienThiTrangThaiKetNoi(trangThai) {
        const statusElement = document.getElementById('connectionStatus');
        if (!statusElement) return;

        const trangThaiMap = {
            'connecting': { 
                text: 'Đang kết nối...', 
                class: 'status-connecting', 
                icon: 'arrow-clockwise',
                spin: true
            },
            'connected': { 
                text: 'Đã kết nối', 
                class: 'status-connected', 
                icon: 'wifi',
                spin: false
            },
            'error': { 
                text: 'Lỗi kết nối', 
                class: 'status-error', 
                icon: 'wifi-off',
                spin: false
            },
            'disconnected': { 
                text: 'Mất kết nối', 
                class: 'status-disconnected', 
                icon: 'exclamation-triangle',
                spin: false
            }
        };

        const status = trangThaiMap[trangThai] || trangThaiMap['disconnected'];
        const iconClass = status.spin ? `bi-${status.icon} spin` : `bi-${status.icon}`;
        
        statusElement.innerHTML = `
            <i class="bi ${iconClass}"></i>
            <span>${status.text}</span>
        `;
        statusElement.className = `connection-status ${status.class}`;
        
        this.khoLuuTru.trangThaiKetNoi = trangThai;
    }

    hienThiThongBaoLoi(thongDiep, loai = 'error', tuDongDong = true) {
        const toastElement = document.createElement('div');
        toastElement.className = `toast align-items-center text-white bg-${loai === 'error' ? 'danger' : 'warning'} border-0`;
        toastElement.setAttribute('role', 'alert');
        toastElement.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${loai === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                    ${thongDiep}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        this.toastContainer.appendChild(toastElement);
        
        // Sử dụng Bootstrap Toast
        const toast = new bootstrap.Toast(toastElement, { 
            delay: tuDongDong ? 5000 : 0,
            autohide: tuDongDong
        });
        toast.show();

        // Xóa element sau khi ẩn
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        return toast;
    }

    hienThiThongBaoThanhCong(thongDiep) {
        this.hienThiThongBaoLoi(thongDiep, 'success', true);
    }

    // ================================
    // FETCH VỚI ERROR HANDLING
    // ================================

    async fetchVoiRetry(url, options = {}) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                // Thêm timeout controller
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 15000); // 15s timeout

                const response = await fetch(url + '?' + Date.now(), {
                    ...options,
                    signal: controller.signal,
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        ...options.headers
                    }
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                // Kiểm tra content type
                const contentType = response.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    throw new Error('Response không phải JSON');
                }

                const data = await response.json();
                
                // Validate dữ liệu cơ bản
                if (!this.validateData(data, url)) {
                    throw new Error('Dữ liệu không hợp lệ');
                }

                return { data, response };

            } catch (error) {
                lastError = error;
                console.warn(`Lần thử ${attempt}/${this.maxRetries} thất bại cho ${url}:`, error.message);
                
                if (attempt < this.maxRetries) {
                    // Exponential backoff
                    const delay = this.retryDelay * Math.pow(2, attempt - 1);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw lastError;
    }

    validateData(data, url) {
        // Validate cơ bản dựa trên URL
        if (url.includes('daily_summary.json')) {
            return data && data.symbols && typeof data.symbols === 'object';
        }
        
        if (url.includes('hourly_24h_summary.json')) {
            return data && data.summary_type === '24h_hourly';
        }
        
        if (url.includes('.json') && !url.includes('summary')) {
            return data && (data.klines || data.open_interest);
        }
        
        return true; // Default validation
    }

    // ================================
    // TỐI ƯU LOADING VÀ PROGRESS
    // ================================

    hienThiDangTaiToanCuc(showProgress = true) {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'flex';
            
            if (showProgress) {
                this.capNhatProgress(0);
            }
        }
    }

    anDangTaiToanCuc() {
        if (this.loadingOverlay) {
            this.loadingOverlay.style.display = 'none';
        }
    }

    capNhatProgress(percentage) {
        const progressBar = document.getElementById('loadingProgress');
        if (progressBar) {
            progressBar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        }
    }

    // ================================
    // TẢI DỮ LIỆU VỚI PROGRESS TRACKING
    // ================================

    async taiDuLieuBanDau() {
        try {
            this.hienThiDangTaiToanCuc(true);
            
            const tasks = [
                { name: 'Dữ liệu thời gian thực', fn: () => this.taiDuLieuThoiGianThuc() },
                { name: 'Dữ liệu 24h theo giờ', fn: () => this.taiDuLieu24hTheoGio() },
                { name: 'Dữ liệu các coin', fn: () => this.taiDuLieuCacCoin() },
                { name: 'Dữ liệu bất thường', fn: () => this.taiDuLieuBatThuong() }
            ];

            const results = [];
            
            for (let i = 0; i < tasks.length; i++) {
                const task = tasks[i];
                try {
                    console.log(`📡 Đang tải: ${task.name}...`);
                    const result = await task.fn();
                    results.push({ success: true, data: result, name: task.name });
                    
                    // Cập nhật progress
                    this.capNhatProgress(((i + 1) / tasks.length) * 100);
                    
                } catch (error) {
                    console.error(`❌ Lỗi tải ${task.name}:`, error);
                    results.push({ success: false, error, name: task.name });
                }
            }

            // Đánh giá kết quả
            const successCount = results.filter(r => r.success).length;
            const failCount = results.length - successCount;

            if (successCount === 0) {
                throw new Error('Không thể tải bất kỳ dữ liệu nào');
            }

            if (failCount > 0) {
                this.hienThiThongBaoLoi(
                    `Đã tải ${successCount}/${results.length} nguồn dữ liệu. ${failCount} nguồn thất bại.`,
                    'warning'
                );
            } else {
                this.hienThiThongBaoThanhCong('Đã tải tất cả dữ liệu thành công!');
            }
            
            this.anDangTaiToanCuc();
            await this.capNhatTatCaGiaoDien();
            
        } catch (error) {
            console.error('❌ Lỗi nghiêm trọng khi tải dữ liệu:', error);
            this.anDangTaiToanCuc();
            this.hienThiLoi(error.message);
        }
    }

    async taiDuLieuThoiGianThuc() {
        try {
            const { data } = await this.fetchVoiRetry('assets/data/daily_summary.json');
            
            this.khoLuuTru.thoiGianThuc = data;
            this.khoLuuTru.capNhatLanCuoi = new Date();
            this.hienThiTrangThaiKetNoi('connected');
            
            return data;
        } catch (error) {
            this.hienThiTrangThaiKetNoi('error');
            
            // Fallback to cache nếu có
            if (this.khoLuuTru.thoiGianThuc) {
                console.warn('Sử dụng dữ liệu cache cho thời gian thực');
                return this.khoLuuTru.thoiGianThuc;
            }
            
            throw new Error(`Không thể tải dữ liệu thời gian thực: ${error.message}`);
        }
    }

    async taiDuLieu24hTheoGio() {
        try {
            const { data } = await this.fetchVoiRetry('assets/data/hourly_24h_summary.json');
            
            this.khoLuuTru.hourly24h = data;
            
            // Hiển thị section 24h nếu có dữ liệu
            const hourlyOverview = document.getElementById('hourlyOverview');
            if (hourlyOverview && data) {
                hourlyOverview.style.display = 'block';
                this.capNhatTongQuan24h(data);
            }
            
            console.log('✅ Đã tải dữ liệu 24h theo giờ');
            return data;
        } catch (error) {
            console.warn('⚠️ Không thể tải dữ liệu 24h theo giờ:', error.message);
            return null;
        }
    }

    async taiDuLieuCacCoin() {
        const results = await Promise.allSettled(
            this.danhSachCoin.map(async coin => {
                try {
                    const { data } = await this.fetchVoiRetry(`assets/data/${coin}.json`);
                    this.khoLuuTru.lichSu.set(coin, data);
                    return { coin, data };
                } catch (error) {
                    console.warn(`⚠️ Không thể tải dữ liệu ${coin}:`, error.message);
                    return null;
                }
            })
        );

        const successCount = results.filter(r => r.status === 'fulfilled' && r.value).length;
        console.log(`✅ Đã tải dữ liệu cho ${successCount}/${this.danhSachCoin.length} coins`);
        
        return results;
    }

    async taiDuLieuBatThuong() {
        try {
            // Ưu tiên lấy từ daily_summary
            if (this.khoLuuTru.thoiGianThuc?.anomalies) {
                this.khoLuuTru.batThuong = this.khoLuuTru.thoiGianThuc.anomalies;
                return this.khoLuuTru.batThuong;
            }

            // Fallback sang file riêng
            const { data } = await this.fetchVoiRetry('assets/data/anomalies.json');
            this.khoLuuTru.batThuong = data;
            return data;
            
        } catch (error) {
            console.warn('⚠️ Không thể tải dữ liệu bất thường:', error.message);
            this.khoLuuTru.batThuong = [];
            return [];
        }
    }

    // ================================
    // XỬ LÝ LỖI VÀ FALLBACK
    // ================================

    hienThiLoi(message) {
        const errorContainer = document.getElementById('errorContainer') || this.taoErrorContainer();
        
        errorContainer.innerHTML = `
            <div class="error-message">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>Có lỗi xảy ra:</strong> ${message}
                <br>
                <button class="retry-button mt-2" onclick="monitor.lamMoiDuLieuManh()">
                    <i class="bi bi-arrow-clockwise me-1"></i>
                    Thử lại
                </button>
            </div>
        `;
        errorContainer.style.display = 'block';
    }

    taoErrorContainer() {
        const container = document.createElement('div');
        container.id = 'errorContainer';
        container.style.display = 'none';
        
        // Thêm vào container chính
        const mainContainer = document.querySelector('.container');
        if (mainContainer) {
            mainContainer.insertBefore(container, mainContainer.firstChild);
        }
        
        return container;
    }

    anThongBaoLoi() {
        const errorContainer = document.getElementById('errorContainer');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    }

    // ================================
    // PERFORMANCE VÀ MEMORY MANAGEMENT
    // ================================

    // Debounce function calls
    debounce(func, delay, key) {
        if (this.debounceTimers.has(key)) {
            clearTimeout(this.debounceTimers.get(key));
        }
        
        const timer = setTimeout(() => {
            func();
            this.debounceTimers.delete(key);
        }, delay);
        
        this.debounceTimers.set(key, timer);
    }

    // Cleanup biểu đồ để tránh memory leak
    cleanupBieuDo(key) {
        if (this.cacBieuDo.has(key)) {
            const chart = this.cacBieuDo.get(key);
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
            this.cacBieuDo.delete(key);
        }
    }

    // Cleanup toàn bộ biểu đồ
    cleanupTatCaBieuDo() {
        this.cacBieuDo.forEach((chart, key) => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.cacBieuDo.clear();
    }

    // ================================
    // CÁC METHODS GỐC (ĐƯỢC CẢI THIỆN)
    // ================================

    ganCacSuKien() {
        // Nút làm mới với debounce
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.debounce(async () => {
                    await this.lamMoiDuLieuManh();
                }, 1000, 'refresh');
            });
        }

        // Các nút bộ lọc thời gian với debounce
        document.querySelectorAll('.btn-time-filter').forEach(nut => {
            nut.addEventListener('click', (e) => {
                const khungThoiGian = e.target.dataset.timeframe;
                const giaiDoan = e.target.dataset.period;
                
                this.debounce(async () => {
                    if (khungThoiGian) {
                        this.khungThoiGianHienTai = khungThoiGian;
                        this.capNhatBoLocHoatDong(e.target);
                        await this.capNhatGiaoDienThoiGianThuc();
                    }
                    
                    if (giaiDoan) {
                        this.giaiDoanHienTai = giaiDoan;
                        this.capNhatBoLocHoatDong(e.target);
                        await this.capNhatGiaoDienLichSu();
                    }
                }, 300, `filter-${khungThoiGian || giaiDoan}`);
            });
        });

        // Sự kiện chuyển tab
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', async (e) => {
                const target = e.target.getAttribute('data-bs-target');
                
                this.debounce(async () => {
                    if (target === '#historical') {
                        await this.taiGiaoDienLichSu();
                    } else if (target === '#anomalies') {
                        await this.taiGiaoDienBatThuong();
                    } else if (target === '#realtime') {
                        await this.taiGiaoDienThoiGianThuc();
                        await this.taiDuLieu24hTheoGio();
                    }
                }, 200, `tab-${target}`);
            });
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.lamMoiDuLieuManh();
                        break;
                }
            }
        });
    }

    async lamMoiDuLieuManh() {
        try {
            this.anThongBaoLoi();
            console.log('🔄 Làm mới dữ liệu mạnh...');
            
            // Reset trạng thái
            this.soLanThayLoi = 0;
            this.khoLuuTru.trangThaiKetNoi = 'connecting';
            
            // Cleanup memory
            this.cleanupTatCaBieuDo();
            
            // Reset dữ liệu
            this.khoLuuTru = {
                thoiGianThuc: null,
                lichSu: new Map(),
                batThuong: null,
                capNhatLanCuoi: null,
                hourly24h: null,
                trangThaiKetNoi: 'connecting'
            };
            
            await this.taiDuLieuBanDau();
            
        } catch (error) {
            console.error('❌ Lỗi khi làm mới dữ liệu:', error);
            this.hienThiLoi(error.message);
        }
    }

    // ================================
    // TỐI ƯU AUTO REFRESH
    // ================================

    thietLapTuDongLamMoi() {
        // Clear existing intervals
        if (this.refreshIntervals) {
            this.refreshIntervals.forEach(interval => clearInterval(interval));
        }
        this.refreshIntervals = [];

        // Làm mới dữ liệu nhẹ mỗi 5 phút
        const lightRefresh = setInterval(async () => {
            if (this.khoLuuTru.trangThaiKetNoi === 'connected') {
                try {
                    console.log('🔄 Làm mới dữ liệu nhẹ...');
                    await this.taiDuLieuThoiGianThuc();
                    await this.taiDuLieu24hTheoGio();
                    await this.capNhatGiaoDienThoiGianThuc();
                    this.soLanThayLoi = 0;
                } catch (error) {
                    this.soLanThayLoi++;
                    console.error(`❌ Lỗi làm mới lần ${this.soLanThayLoi}:`, error);
                    
                    if (this.soLanThayLoi >= 3) {
                        this.hienThiThongBaoLoi('Mất kết nối liên tục. Sẽ thử lại sau.', 'warning');
                    }
                }
            }
        }, 5 * 60 * 1000);

        // Làm mới toàn bộ mỗi 30 phút
        const fullRefresh = setInterval(async () => {
            console.log('🔄 Làm mới toàn bộ dữ liệu...');
            await this.lamMoiDuLieuManh();
        }, 30 * 60 * 1000);

        this.refreshIntervals = [lightRefresh, fullRefresh];
    }

    // ================================
    // PLACEHOLDER METHODS (CẦN IMPLEMENT)
    // ================================

    async capNhatTatCaGiaoDien() {
        // Implementation needed
        console.log('Cập nhật tất cả giao diện...');
    }

    async capNhatGiaoDienThoiGianThuc() {
        // Implementation needed
        console.log('Cập nhật giao diện thời gian thực...');
    }

    async capNhatGiaoDienLichSu() {
        // Implementation needed
        console.log('Cập nhật giao diện lịch sử...');
    }

    async capNhatGiaoDienBatThuong() {
        // Implementation needed
        console.log('Cập nhật giao diện bất thường...');
    }

    async taiGiaoDienThoiGianThuc() {
        await this.capNhatGiaoDienThoiGianThuc();
    }

    async taiGiaoDienLichSu() {
        await this.capNhatGiaoDienLichSu();
    }

    async taiGiaoDienBatThuong() {
        await this.capNhatGiaoDienBatThuong();
    }

    capNhatBoLocHoatDong(nutHoatDong) {
        nutHoatDong.parentNode.querySelectorAll('.btn-time-filter').forEach(nut => {
            nut.classList.remove('active');
        });
        nutHoatDong.classList.add('active');
    }

    capNhatTongQuan24h(data) {
        // Implementation needed
        console.log('Cập nhật tổng quan 24h:', data);
    }

    thietLapWebSocket() {
        // Future implementation
        console.log('WebSocket sẽ được triển khai trong tương lai...');
    }

    // ================================
    // CLEANUP VÀ DESTROY
    // ================================

    destroy() {
        // Cleanup intervals
        if (this.refreshIntervals) {
            this.refreshIntervals.forEach(interval => clearInterval(interval));
        }

        // Cleanup timers
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();

        // Cleanup charts
        this.cleanupTatCaBieuDo();

        // Remove event listeners
        document.removeEventListener('keydown', this.handleKeydown);

        console.log('🧹 Đã cleanup hệ thống');
    }
}

// ================================
// KHỞI TẠO HỆ THỐNG
// ================================

document.addEventListener('DOMContentLoaded', () => {
    // Cleanup hệ thống cũ nếu có
    if (window.monitor && typeof window.monitor.destroy === 'function') {
        window.monitor.destroy();
    }
    
    // Khởi tạo hệ thống mới
    window.monitor = new HeThongTheoDoi_Binance_VietNam_V2();
    
    // Expose để debug
    window.debugMonitor = {
        getState: () => window.monitor.khoLuuTru,
        getCharts: () => window.monitor.cacBieuDo,
        forceRefresh: () => window.monitor.lamMoiDuLieuManh(),
        cleanup: () => window.monitor.destroy()
    };
});

// Cleanup khi unload
window.addEventListener('beforeunload', () => {
    if (window.monitor && typeof window.monitor.destroy === 'function') {
        window.monitor.destroy();
    }
});

// Export cho module environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeThongTheoDoi_Binance_VietNam_V2;
}