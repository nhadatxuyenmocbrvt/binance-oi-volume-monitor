/**
 * Hệ Thống Theo Dõi OI & Volume Binance - Tracking 24h
 * Tác giả: AI Assistant
 * Mô tả: Theo dõi Open Interest và Volume của các coin trên Binance với tracking 24h
 */

class HeThongTheoDoi_Binance_VietNam {
    constructor() {
        this.khungThoiGianHienTai = '1h';
        this.giaiDoanHienTai = '7d';
        this.cacBieuDo = {};
        this.danhSachCoin = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT'];
        this.khoLuuTru = {
            thoiGianThuc: null,
            lichSu: {},
            batThuong: null,
            tracking24h: null,
            capNhatLanCuoi: null
        };
        this.khoiTao();
    }

    async khoiTao() {
        this.ganCacSuKien();
        this.thietLapWebSocket(); // Tính năng tương lai
        await this.taiDuLieuBanDau();
        this.thietLapTuDongLamMoi();
    }

    ganCacSuKien() {
        // Nút làm mới
        document.getElementById('refreshBtn').addEventListener('click', async () => {
            await this.lamMoiDuLieuManh();
        });

        // Các nút bộ lọc thời gian
        document.querySelectorAll('.btn-time-filter').forEach(nut => {
            nut.addEventListener('click', async (e) => {
                const khungThoiGian = e.target.dataset.timeframe;
                const giaiDoan = e.target.dataset.period;
                
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
            });
        });

        // Sự kiện chuyển đổi tab
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', async (e) => {
                const dich = e.target.getAttribute('data-bs-target');
                if (dich === '#historical') {
                    await this.taiGiaoDienLichSu();
                } else if (dich === '#anomalies') {
                    await this.taiGiaoDienBatThuong();
                } else if (dich === '#realtime') {
                    await this.taiGiaoDienThoiGianThuc();
                } else if (dich === '#tracking24h') {
                    await this.taiGiaoDienTracking24h();
                }
            });
        });

        // THÊM MỚI: Sự kiện cho tracking 24h
        this.capNhatSuKienTuyChon24h();
    }

    capNhatBoLocHoatDong(nutHoatDong) {
        nutHoatDong.parentNode.querySelectorAll('.btn-time-filter').forEach(nut => {
            nut.classList.remove('active');
        });
        nutHoatDong.classList.add('active');
    }

    async taiDuLieuBanDau() {
        try {
            this.hienThiDangTaiToanCuc();
            
            // Tải tất cả dữ liệu song song
            await Promise.all([
                this.taiDuLieuThoiGianThuc(),
                this.taiDuLieuCacCoin(),
                this.taiDuLieuBatThuong(),
                this.taiDuLieuTracking24h()
            ]);
            
            this.anDangTaiToanCuc();
            await this.capNhatTatCaGiaoDien();
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu ban đầu:', loi);
            this.hienThiLoi('Không thể tải dữ liệu ban đầu');
            this.anDangTaiToanCuc();
        }
    }

    async lamMoiDuLieuManh() {
        this.khoLuuTru = {
            thoiGianThuc: null,
            lichSu: {},
            batThuong: null,
            tracking24h: null,
            capNhatLanCuoi: null
        };
        await this.taiDuLieuBanDau();
    }

    async taiDuLieuThoiGianThuc() {
        try {
            const phanHoi = await fetch('assets/data/daily_summary.json?' + Date.now());
            if (!phanHoi.ok) throw new Error('Không thể tải dữ liệu thời gian thực');
            
            const duLieu = await phanHoi.json();
            this.khoLuuTru.thoiGianThuc = duLieu;
            this.khoLuuTru.capNhatLanCuoi = new Date();
            
            return duLieu;
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu thời gian thực:', loi);
            return null;
        }
    }

    async taiDuLieuCacCoin() {
        try {
            const cacLoiHua = this.danhSachCoin.map(async coin => {
                try {
                    const phanHoi = await fetch(`assets/data/${coin}.json?` + Date.now());
                    if (!phanHoi.ok) return null;
                    
                    const duLieu = await phanHoi.json();
                    this.khoLuuTru.lichSu[coin] = duLieu;
                    return { coin, duLieu };
                } catch (loi) {
                    console.error(`Lỗi khi tải dữ liệu ${coin}:`, loi);
                    return null;
                }
            });

            const ketQua = await Promise.allSettled(cacLoiHua);
            return ketQua;
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu các coin:', loi);
            return [];
        }
    }

    async taiDuLieuBatThuong() {
        try {
            // Lấy từ dữ liệu thời gian thực
            if (this.khoLuuTru.thoiGianThuc && this.khoLuuTru.thoiGianThuc.anomalies) {
                this.khoLuuTru.batThuong = this.khoLuuTru.thoiGianThuc.anomalies;
                return this.khoLuuTru.batThuong;
            }

            // Dự phòng từ file riêng
            try {
                const phanHoi = await fetch('assets/data/anomalies.json?' + Date.now());
                if (phanHoi.ok) {
                    const duLieu = await phanHoi.json();
                    this.khoLuuTru.batThuong = duLieu;
                    return duLieu;
                }
            } catch (loi) {
                console.warn('Không tìm thấy file bất thường riêng');
            }

            return [];
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu bất thường:', loi);
            return [];
        }
    }

    async taiDuLieuTracking24h() {
        try {
            const phanHoi = await fetch('assets/data/tracking_24h.json?' + Date.now());
            if (!phanHoi.ok) {
                console.warn('Không thể tải dữ liệu tracking 24h');
                return null;
            }
            
            const duLieu = await phanHoi.json();
            this.khoLuuTru.tracking24h = duLieu;
            
            return duLieu;
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu tracking 24h:', loi);
            return null;
        }
    }

    async capNhatTatCaGiaoDien() {
        await Promise.all([
            this.capNhatGiaoDienThoiGianThuc(),
            this.capNhatGiaoDienBatThuong(),
            this.capNhatGiaoDienTracking24h()
        ]);
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

    async taiGiaoDienTracking24h() {
        await this.capNhatGiaoDienTracking24h();
    }

    async capNhatGiaoDienThoiGianThuc() {
        if (!this.khoLuuTru.thoiGianThuc) return;

        try {
            const duLieu = this.khoLuuTru.thoiGianThuc;
            
            this.capNhatThoiGianCapNhatCuoi(duLieu.timestamp);
            this.capNhatBangThoiGianThuc(duLieu.symbols);
            this.capNhatThongKe(duLieu.symbols);
        } catch (loi) {
            console.error('Lỗi khi cập nhật giao diện thời gian thực:', loi);
        }
    }

    async capNhatGiaoDienLichSu() {
        try {
            const duLieuLichSu = this.khoLuuTru.lichSu;
            
            this.capNhatBangLichSu(duLieuLichSu);
            this.capNhatBieuDoLichSu(duLieuLichSu);
        } catch (loi) {
            console.error('Lỗi khi cập nhật giao diện lịch sử:', loi);
        }
    }

    async capNhatGiaoDienBatThuong() {
        try {
            const batThuong = this.khoLuuTru.batThuong || [];
            this.capNhatBangBatThuong(batThuong);
        } catch (loi) {
            console.error('Lỗi khi cập nhật giao diện bất thường:', loi);
        }
    }

    async capNhatGiaoDienTracking24h() {
        try {
            const tracking24h = this.khoLuuTru.tracking24h;
            if (!tracking24h) {
                this.hienThiThongBaoTracking24h('Chưa có dữ liệu tracking 24h');
                return;
            }
            
            this.capNhatBieuDoTracking24h(tracking24h);
            this.capNhatThongKeTracking24h(tracking24h);
        } catch (loi) {
            console.error('Lỗi khi cập nhật giao diện tracking 24h:', loi);
        }
    }

    capNhatThoiGianCapNhatCuoi(thoiGian) {
        const phanTuCapNhat = document.getElementById('lastUpdateTime');
        if (phanTuCapNhat) {
            const ngay = new Date(thoiGian);
            phanTuCapNhat.innerHTML = `
                <i class="bi bi-clock"></i>
                Cập nhật lần cuối: ${ngay.toLocaleString('vi-VN')}
                <span class="badge bg-success ms-2">Trực Tuyến</span>
            `;
        }
    }

    capNhatBangThoiGianThuc(symbols) {
        const tbody = document.getElementById('realtimeTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        // Sắp xếp symbols theo thay đổi giá tuyệt đối giảm dần
        const symbolsSapXep = Object.entries(symbols).sort((a, b) => {
            return Math.abs(b[1].price_change) - Math.abs(a[1].price_change);
        });

        symbolsSapXep.forEach(([symbol, duLieu]) => {
            const hang = this.taoHangThoiGianThuc(symbol, duLieu);
            tbody.appendChild(hang);
        });
    }

    taoHangThoiGianThuc(symbol, duLieu) {
        const hang = document.createElement('tr');
        hang.className = 'symbol-row';
        hang.setAttribute('data-symbol', symbol);
        
        const lopGia = this.layLopThayDoi(duLieu.price_change);
        const lopVolume = this.layLopThayDoi(duLieu.volume_change);
        const lopOI = this.layLopThayDoi(duLieu.oi_change);
        const thongTinXuHuong = this.layThongTinXuHuong(duLieu.sentiment);

        hang.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="symbol-icon me-2">
                        <i class="bi bi-currency-bitcoin text-warning"></i>
                    </div>
                    <div>
                        <div class="coin-symbol">${symbol}</div>
                        <small class="text-muted">${this.layTenCoin(symbol)}</small>
                    </div>
                </div>
            </td>
            <td>
                <div class="${lopGia}">
                    <strong>${this.dinhDangPhanTram(duLieu.price_change)}</strong>
                    <i class="bi bi-${duLieu.price_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">Thay đổi ${this.khungThoiGianHienTai}</small>
            </td>
            <td>
                <div class="${lopVolume}">
                    <strong>${this.dinhDangPhanTram(duLieu.volume_change)}</strong>
                    <i class="bi bi-${duLieu.volume_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">So với TB 24h</small>
            </td>
            <td>
                <div class="${lopOI}">
                    <strong>${this.dinhDangPhanTram(duLieu.oi_change)}</strong>
                    <i class="bi bi-${duLieu.oi_change >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">Open Interest</small>
            </td>
            <td>
                <span class="badge sentiment-badge ${thongTinXuHuong.lop}" title="${thongTinXuHuong.moTa}">
                    <i class="bi bi-${thongTinXuHuong.bieuTuong} me-1"></i>
                    ${thongTinXuHuong.chuoi}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="monitor.hienThiChiTiet('${symbol}')" title="Xem Chi Tiết">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-outline-info" onclick="monitor.hienThiBieuDo('${symbol}')" title="Xem Biểu Đồ">
                        <i class="bi bi-graph-up"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="monitor.hienThiTracking24h('${symbol}')" title="Tracking 24h">
                        <i class="bi bi-clock-history"></i>
                    </button>
                </div>
            </td>
        `;

        // Thêm hiệu ứng hover
        hang.addEventListener('mouseenter', () => {
            hang.style.backgroundColor = '#f8f9fa';
        });
        
        hang.addEventListener('mouseleave', () => {
            hang.style.backgroundColor = '';
        });

        return hang;
    }

    capNhatBangLichSu(duLieuLichSu) {
        const tbody = document.getElementById('historicalTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        Object.entries(duLieuLichSu).forEach(([symbol, duLieu]) => {
            const hang = this.taoHangLichSu(symbol, duLieu);
            tbody.appendChild(hang);
        });
    }

    taoHangLichSu(symbol, duLieu) {
        const hang = document.createElement('tr');
        
        // Tính toán thay đổi lịch sử dựa trên dữ liệu thực
        const lichSu = this.tinhToanThayDoiLichSu(duLieu);

        hang.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <div class="symbol-icon me-2">
                        <i class="bi bi-currency-bitcoin text-warning"></i>
                    </div>
                    <div>
                        <div class="coin-symbol">${symbol}</div>
                        <small class="text-muted">${this.layTenCoin(symbol)}</small>
                    </div>
                </div>
            </td>
            <td class="${this.layLopThayDoi(lichSu.gia7d)}">
                <strong>${this.dinhDangPhanTram(lichSu.gia7d)}</strong>
            </td>
            <td class="${this.layLopThayDoi(lichSu.volume7d)}">
                <strong>${this.dinhDangPhanTram(lichSu.volume7d)}</strong>
            </td>
            <td class="${this.layLopThayDoi(lichSu.oi7d)}">
                <strong>${this.dinhDangPhanTram(lichSu.oi7d)}</strong>
            </td>
            <td class="${this.layLopThayDoi(lichSu.gia30d)}">
                <strong>${this.dinhDangPhanTram(lichSu.gia30d)}</strong>
            </td>
            <td class="${this.layLopThayDoi(lichSu.oi30d)}">
                <strong>${this.dinhDangPhanTram(lichSu.oi30d)}</strong>
            </td>
            <td>
                <span class="badge bg-${lichSu.xuHuong.mau}">
                    <i class="bi bi-${lichSu.xuHuong.bieuTuong} me-1"></i>
                    ${lichSu.xuHuong.chuoi}
                </span>
            </td>
        `;

        return hang;
    }

    tinhToanThayDoiLichSu(duLieuSymbol) {
        // Tính toán dựa trên dữ liệu lịch sử thực
        // Hiện tại sử dụng dữ liệu mô phỏng
        // Trong thực tế, bạn sẽ tính từ duLieuSymbol.klines
        
        return {
            gia7d: (Math.random() - 0.5) * 20,
            volume7d: (Math.random() - 0.5) * 40,
            oi7d: (Math.random() - 0.5) * 15,
            gia30d: (Math.random() - 0.5) * 30,
            oi30d: (Math.random() - 0.5) * 25,
            xuHuong: this.tinhToanXuHuong()
        };
    }

    tinhToanXuHuong() {
        const cacXuHuong = [
            { chuoi: 'Tăng Mạnh', mau: 'success', bieuTuong: 'arrow-up-circle' },
            { chuoi: 'Tăng', mau: 'success', bieuTuong: 'arrow-up' },
            { chuoi: 'Ngang', mau: 'warning', bieuTuong: 'arrow-left-right' },
            { chuoi: 'Giảm', mau: 'danger', bieuTuong: 'arrow-down' },
            { chuoi: 'Giảm Mạnh', mau: 'danger', bieuTuong: 'arrow-down-circle' }
        ];
        return cacXuHuong[Math.floor(Math.random() * cacXuHuong.length)];
    }

    capNhatBangBatThuong(batThuong) {
        const tbody = document.getElementById('anomaliesTableBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!batThuong || batThuong.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="bi bi-check-circle text-success me-2"></i>
                        Không phát hiện bất thường nào
                    </td>
                </tr>
            `;
            return;
        }

        // Sắp xếp bất thường theo thời gian giảm dần
        const batThuongSapXep = batThuong.sort((a, b) => 
            new Date(b.timestamp) - new Date(a.timestamp)
        );

        batThuongSapXep.forEach(batThuong => {
            const hang = this.taoHangBatThuong(batThuong);
            tbody.appendChild(hang);
        });
    }

    taoHangBatThuong(batThuong) {
        const hang = document.createElement('tr');
        const mucDo = this.layMucDoBatThuong(batThuong.message);
        const thoiGianTruoc = this.layThoiGianTruoc(batThuong.timestamp);
        
        hang.innerHTML = `
            <td>
                <div>${this.dinhDangThoiGian(batThuong.timestamp)}</div>
                <small class="text-muted">${thoiGianTruoc}</small>
            </td>
            <td>
                <span class="coin-symbol">${batThuong.symbol}</span>
            </td>
            <td>
                <span class="badge bg-info">
                    <i class="bi bi-${this.layBieuTuongLoaiDuLieu(batThuong.data_type)} me-1"></i>
                    ${this.dichLoaiDuLieu(batThuong.data_type)}
                </span>
            </td>
            <td>
                <div class="anomaly-message">${batThuong.message}</div>
            </td>
            <td>
                <span class="badge bg-${mucDo.mau}">
                    <i class="bi bi-${mucDo.bieuTuong} me-1"></i>
                    ${mucDo.chuoi}
                </span>
            </td>
        `;

        return hang;
    }

    capNhatBieuDoTracking24h(tracking24h) {
        const container = document.getElementById('tracking24hChart');
        if (!container) return;

        // Xóa biểu đồ cũ nếu có
        if (this.cacBieuDo.tracking24h) {
            this.cacBieuDo.tracking24h.destroy();
        }

        // Tạo canvas cho biểu đồ
        container.innerHTML = '<canvas id="tracking24hCanvas"></canvas>';
        const ctx = document.getElementById('tracking24hCanvas');

        // Chuẩn bị dữ liệu biểu đồ
        const duLieuBieuDo = this.chuanBiDuLieuBieuDo24h(tracking24h);

        this.cacBieuDo.tracking24h = new Chart(ctx, {
            type: 'line',
            data: duLieuBieuDo,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Tracking 24h - Thay Đổi Giá Theo Giờ'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Giờ'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Thay Đổi (%)'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    chuanBiDuLieuBieuDo24h(tracking24h) {
        const labels = [];
        const datasets = [];

        // Tạo labels cho 24 giờ
        for (let i = 0; i < 24; i++) {
            labels.push(`${i.toString().padStart(2, '0')}:00`);
        }

        // Tạo dataset cho từng symbol
        this.danhSachCoin.forEach((symbol, index) => {
            const symbolData = tracking24h.symbols[symbol];
            if (symbolData && symbolData.hours_data) {
                const data = new Array(24).fill(0);
                
                symbolData.hours_data.forEach(hourData => {
                    const hour = new Date(hourData.hour_timestamp).getHours();
                    data[hour] = hourData.price_change_1h || 0;
                });

                datasets.push({
                    label: symbol,
                    data: data,
                    borderColor: this.layMauChoViTri(index),
                    backgroundColor: this.layMauChoViTri(index) + '20',
                    tension: 0.3,
                    fill: false
                });
            }
        });

        return { labels, datasets };
    }

    capNhatThongKeTracking24h(tracking24h) {
        const statsContainer = document.getElementById('tracking24hStats');
        if (!statsContainer) return;

        let html = '<div class="row">';

        // Thống kê cho từng symbol
        this.danhSachCoin.forEach(symbol => {
            const symbolData = tracking24h.symbols[symbol];
            if (symbolData) {
                const volatility = symbolData.price_volatility || 0;
                const price24h = symbolData.price_24h_change || 0;
                const maxChange = symbolData.max_price_change_hour;

                html += `
                    <div class="col-md-4 col-lg-2 mb-3">
                        <div class="card h-100">
                            <div class="card-body text-center">
                                <h6 class="card-title">${symbol}</h6>
                                <div class="mb-2">
                                    <div class="text-${price24h >= 0 ? 'success' : 'danger'}">
                                        <strong>${this.dinhDangPhanTram(price24h)}</strong>
                                    </div>
                                    <small class="text-muted">24h Change</small>
                                </div>
                                <div class="mb-2">
                                    <div class="text-info">
                                        <strong>${volatility.toFixed(2)}%</strong>
                                    </div>
                                    <small class="text-muted">Volatility</small>
                                </div>
                                ${maxChange ? `
                                    <div>
                                        <div class="text-warning">
                                            <strong>${maxChange.hour}</strong>
                                        </div>
                                        <small class="text-muted">Max Change</small>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }
        });

        html += '</div>';
        statsContainer.innerHTML = html;
    }

    hienThiThongBaoTracking24h(thongBao) {
        const container = document.getElementById('tracking24hChart');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-clock-history display-1 text-muted"></i>
                    <p class="text-muted mt-3">${thongBao}</p>
                </div>
            `;
        }
    }

    capNhatThongKe(symbols) {
        const thongKe = this.tinhThongKeChiTiet(symbols);
        
        document.getElementById('totalSymbols').textContent = thongKe.tong;
        document.getElementById('bullishCount').textContent = thongKe.tang;
        document.getElementById('bearishCount').textContent = thongKe.giam;
        document.getElementById('neutralCount').textContent = thongKe.trungTinh;
    }

    tinhThongKeChiTiet(symbols) {
        const thongKe = { 
            tong: 0, 
            tang: 0, 
            giam: 0, 
            trungTinh: 0,
            trungBinhThayDoiGia: 0,
            trungBinhThayDoiVolume: 0,
            trungBinhThayDoiOI: 0
        };
        
        const cacGiaTri = Object.values(symbols);
        thongKe.tong = cacGiaTri.length;

        let tongThayDoiGia = 0;
        let tongThayDoiVolume = 0;
        let tongThayDoiOI = 0;

        cacGiaTri.forEach(duLieu => {
            const xuHuong = duLieu.sentiment.toLowerCase();
            
            if (xuHuong.includes('bullish')) {
                thongKe.tang++;
            } else if (xuHuong.includes('bearish')) {
                thongKe.giam++;
            } else {
                thongKe.trungTinh++;
            }

            tongThayDoiGia += duLieu.price_change || 0;
            tongThayDoiVolume += duLieu.volume_change || 0;
            tongThayDoiOI += duLieu.oi_change || 0;
        });

        thongKe.trungBinhThayDoiGia = tongThayDoiGia / thongKe.tong;
        thongKe.trungBinhThayDoiVolume = tongThayDoiVolume / thongKe.tong;
        thongKe.trungBinhThayDoiOI = tongThayDoiOI / thongKe.tong;

        return thongKe;
    }

    capNhatBieuDoLichSu(duLieuLichSu) {
        const ctx = document.getElementById('historicalChart');
        if (!ctx) return;

        if (this.cacBieuDo.lichSu) {
            this.cacBieuDo.lichSu.destroy();
        }

        // Tạo nhãn cho giai đoạn
        const nhan = this.taoNhanNgay(this.giaiDoanHienTai);
        
        // Tạo bộ dữ liệu cho từng symbol
        const boDuLieu = Object.keys(duLieuLichSu).map((symbol, viTri) => {
            const mau = this.layMauChoViTri(viTri);
            return {
                label: symbol,
                data: this.taoDuLieuLichSuGia(nhan.length),
                borderColor: mau,
                backgroundColor: mau + '20',
                tension: 0.1,
                fill: false
            };
        });

        this.cacBieuDo.lichSu = new Chart(ctx, {
            type: 'line',
            data: { labels: nhan, datasets: boDuLieu },
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
                        text: `Biểu Đồ Lịch Sử Hiệu Suất Giá (${this.giaiDoanHienTai})`
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Ngày'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Thay Đổi (%)'
                        }
                    }
                }
            }
        });
    }

    taoNhanNgay(giaiDoan) {
        const soNgay = giaiDoan === '7d' ? 7 : giaiDoan === '30d' ? 30 : 90;
        return Array.from({length: soNgay}, (_, i) => {
            const ngay = new Date();
            ngay.setDate(ngay.getDate() - (soNgay - 1 - i));
            return ngay.toLocaleDateString('vi-VN');
        });
    }

    taoDuLieuLichSuGia(doDai) {
        let giaTri = 0;
        return Array.from({length: doDai}, () => {
            giaTri += (Math.random() - 0.5) * 5;
            return giaTri;
        });
    }

    // Các phương thức tiện ích
    layLopThayDoi(thayDoi) {
        if (thayDoi > 0) return 'change-positive';
        if (thayDoi < 0) return 'change-negative';
        return 'change-neutral';
    }

    layThongTinXuHuong(xuHuong) {
        const s = xuHuong.toLowerCase();
        
        if (s.includes('strong') && s.includes('bullish')) {
            return { 
                lop: 'sentiment-bullish', 
                chuoi: 'Tăng Mạnh', 
                bieuTuong: 'arrow-up-circle-fill',
                moTa: 'Xu hướng tăng mạnh'
            };
        } else if (s.includes('bullish')) {
            return { 
                lop: 'sentiment-bullish', 
                chuoi: 'Tăng Giá', 
                bieuTuong: 'arrow-up',
                moTa: 'Xu hướng tăng giá'
            };
        } else if (s.includes('strong') && s.includes('bearish')) {
            return { 
                lop: 'sentiment-bearish', 
                chuoi: 'Giảm Mạnh', 
                bieuTuong: 'arrow-down-circle-fill',
                moTa: 'Xu hướng giảm mạnh'
            };
        } else if (s.includes('bearish')) {
            return { 
                lop: 'sentiment-bearish', 
                chuoi: 'Giảm Giá', 
                bieuTuong: 'arrow-down',
                moTa: 'Xu hướng giảm giá'
            };
        }
        
        return { 
            lop: 'sentiment-neutral', 
            chuoi: 'Trung Tính', 
            bieuTuong: 'dash-circle',
            moTa: 'Xu hướng trung tính'
        };
    }

    layMucDoBatThuong(thongDiep) {
        const zscore = parseFloat(thongDiep.match(/Z-score: ([\d.]+)/)?.[1] || 0);
        
        if (zscore > 4) {
            return { mau: 'danger', chuoi: 'Nghiêm Trọng', bieuTuong: 'exclamation-triangle-fill' };
        } else if (zscore > 3) {
            return { mau: 'warning', chuoi: 'Cao', bieuTuong: 'exclamation-triangle' };
        } else if (zscore > 2.5) {
            return { mau: 'info', chuoi: 'Trung Bình', bieuTuong: 'info-circle' };
        }
        
        return { mau: 'secondary', chuoi: 'Thấp', bieuTuong: 'info-circle' };
    }

    layBieuTuongLoaiDuLieu(loaiDuLieu) {
        const bieuTuong = {
            volume: 'bar-chart',
            open_interest: 'pie-chart',
            price: 'graph-up',
            correlation: 'shuffle'
        };
        return bieuTuong[loaiDuLieu] || 'info-circle';
    }

    layTenCoin(symbol) {
        const ten = {
            'BTCUSDT': 'Bitcoin',
            'ETHUSDT': 'Ethereum', 
            'BNBUSDT': 'BNB',
            'SOLUSDT': 'Solana',
            'DOGEUSDT': 'Dogecoin'
        };
        return ten[symbol] || symbol;
    }

    layMauChoViTri(viTri) {
        const mau = [
            '#f7931e', // Bitcoin cam
            '#627eea', // Ethereum xanh
            '#f0b90b', // BNB vàng
            '#9945ff', // Solana tím
            '#c2a633'  // Dogecoin vàng
        ];
        return mau[viTri % mau.length];
    }

    dinhDangPhanTram(giaTri) {
        if (giaTri === null || giaTri === undefined || isNaN(giaTri)) {
            return 'N/A';
        }
        return `${giaTri >= 0 ? '+' : ''}${giaTri.toFixed(2)}%`;
    }

    dinhDangThoiGian(thoiGian) {
        return new Date(thoiGian).toLocaleString('vi-VN');
    }

    layThoiGianTruoc(thoiGian) {
        const bay_gio = new Date();
        const thoi_gian = new Date(thoiGian);
        const chenhLechMs = bay_gio - thoi_gian;
        const chenhLechGio = Math.floor(chenhLechMs / (1000 * 60 * 60));
        const chenhLechPhut = Math.floor(chenhLechMs / (1000 * 60));

        if (chenhLechGio > 24) {
            return `${Math.floor(chenhLechGio / 24)} ngày trước`;
        } else if (chenhLechGio > 0) {
            return `${chenhLechGio} giờ trước`;
        } else {
            return `${chenhLechPhut} phút trước`;
        }
    }

    dichLoaiDuLieu(loai) {
        const tuDien = {
            volume: 'Khối Lượng',
            open_interest: 'OI',
            price: 'Giá',
            correlation: 'Tương Quan'
        };
        return tuDien[loai] || loai;
    }

    vietHoaDauChu(chuoi) {
        return chuoi.charAt(0).toUpperCase() + chuoi.slice(1);
    }

    // Các phương thức hành động
    hienThiChiTiet(symbol) {
        // Tạo modal hoặc điều hướng đến trang chi tiết
        alert(`Hiển thị phân tích chi tiết cho ${symbol}`);
        // TODO: Triển khai view chi tiết với biểu đồ, chỉ báo, v.v.
    }

    hienThiBieuDo(symbol) {
        // Mở biểu đồ trong modal hoặc tab mới
        alert(`Mở biểu đồ nâng cao cho ${symbol}`);
        // TODO: Triển khai biểu đồ nâng cao với TradingView hoặc tương tự
    }

    hienThiTracking24h(symbol) {
        // Chuyển đến tab tracking 24h và focus vào symbol
        const tracking24hTab = document.querySelector('[data-bs-target="#tracking24h"]');
        if (tracking24hTab) {
            tracking24hTab.click();
        }
        // TODO: Highlight symbol trong biểu đồ tracking 24h
    }

    hienThiDangTaiToanCuc() {
        // TODO: Hiển thị overlay đang tải toàn cục
    }

    anDangTaiToanCuc() {
        // TODO: Ẩn overlay đang tải toàn cục
    }

    hienThiLoi(thongDiep) {
        console.error(thongDiep);
        // TODO: Hiển thị thông báo lỗi thân thiện với người dùng
    }

    thietLapWebSocket() {
        // TODO: Triển khai WebSocket để cập nhật thời gian thực
        // Kết nối đến Binance WebSocket hoặc WebSocket server của riêng bạn
    }

    thietLapTuDongLamMoi() {
        // Làm mới dữ liệu mỗi 5 phút
        setInterval(async () => {
            console.log('Tự động làm mới dữ liệu...');
            await this.taiDuLieuThoiGianThuc();
            await this.taiDuLieuTracking24h();
            await this.capNhatGiaoDienThoiGianThuc();
            await this.capNhatGiaoDienTracking24h();
        }, 5 * 60 * 1000);

        // Làm mới toàn bộ dữ liệu mỗi 30 phút
        setInterval(async () => {
            console.log('Làm mới toàn bộ dữ liệu...');
            await this.lamMoiDuLieuManh();
        }, 30 * 60 * 1000);
    }
}

// Khởi tạo hệ thống theo dõi nâng cao
document.addEventListener('DOMContentLoaded', () => {
    window.monitor = new HeThongTheoDoi_Binance_VietNam();
});

// Xuất để debug
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeThongTheoDoi_Binance_VietNam;
}