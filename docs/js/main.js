/**
 * Hệ Thống Theo Dõi OI & Volume Binance - Phiên Bản Việt Hóa với 24H Tracking
 * Tác giả: AI Assistant
 * Mô tả: Theo dõi Open Interest và Volume của các coin trên Binance theo giờ
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
            capNhatLanCuoi: null,
            hourly24h: null  // THÊM MỚI - Dữ liệu 24h theo giờ
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
                    await this.taiDuLieu24hTheoGio(); // THÊM MỚI
                }
            });
        });
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
                this.taiDuLieu24hTheoGio()  // THÊM MỚI
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
            capNhatLanCuoi: null,
            hourly24h: null
        };
        await this.taiDuLieuBanDau();
    }

    async taiDuLieu24hTheoGio() {
        /**
         * Tải dữ liệu 24h theo giờ - THÊM MỚI
         */
        try {
            const phanHoi = await fetch('assets/data/hourly_24h_summary.json?' + Date.now());
            if (!phanHoi.ok) {
                console.warn('Không thể tải dữ liệu 24h theo giờ');
                return null;
            }
            
            const duLieu = await phanHoi.json();
            this.khoLuuTru.hourly24h = duLieu;
            
            console.log('✅ Đã tải dữ liệu 24h theo giờ:', duLieu);
            return duLieu;
        } catch (loi) {
            console.error('Lỗi khi tải dữ liệu 24h theo giờ:', loi);
            return null;
        }
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

    async capNhatTatCaGiaoDien() {
        await Promise.all([
            this.capNhatGiaoDienThoiGianThuc(),
            this.capNhatGiaoDienBatThuong(),
            this.capNhatBieuDo24hTheoGio()  // THÊM MỚI
        ]);
    }

    async taiGiaoDienThoiGianThuc() {
        await this.capNhatGiaoDienThoiGianThuc();
        await this.capNhatBieuDo24hTheoGio();  // THÊM MỚI
    }

    async taiGiaoDienLichSu() {
        await this.capNhatGiaoDienLichSu();
    }

    async taiGiaoDienBatThuong() {
        await this.capNhatGiaoDienBatThuong();
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

    async capNhatBieuDo24hTheoGio() {
        /**
         * Cập nhật biểu đồ 24h theo giờ - THÊM MỚI
         */
        try {
            if (!this.khoLuuTru.hourly24h) {
                console.warn('Chưa có dữ liệu 24h theo giờ');
                return;
            }

            const duLieu24h = this.khoLuuTru.hourly24h;
            
            // Tạo hoặc cập nhật biểu đồ 24h
            this.taoBieuDo24hChoCacSymbol(duLieu24h);
            
            // Cập nhật bảng với xu hướng 24h
            this.capNhatBangVoiXuHuong24h(duLieu24h);
            
            console.log('✅ Đã cập nhật biểu đồ 24h theo giờ');
        } catch (loi) {
            console.error('❌ Lỗi khi cập nhật biểu đồ 24h:', loi);
        }
    }

    taoBieuDo24hChoCacSymbol(duLieu24h) {
        /**
         * Tạo biểu đồ mini 24h cho từng symbol - THÊM MỚI
         */
        try {
            if (!duLieu24h.symbols) return;

            // Lấy nhãn thời gian (24 giờ)
            const nhanThoiGian = this.taoNhanThoiGian24h();

            Object.entries(duLieu24h.symbols).forEach(([symbol, data]) => {
                // Tìm hoặc tạo container cho biểu đồ mini
                let chartContainer = document.getElementById(`mini-chart-${symbol}`);
                if (!chartContainer) {
                    // Tạo container mới nếu chưa có
                    chartContainer = this.taoContainerBieuDoMini(symbol);
                }

                if (chartContainer) {
                    this.taoBieuDoMini24h(symbol, data, nhanThoiGian);
                }
            });
        } catch (loi) {
            console.error('Lỗi khi tạo biểu đồ 24h:', loi);
        }
    }

    taoContainerBieuDoMini(symbol) {
        /**
         * Tạo container cho biểu đồ mini trong bảng - THÊM MỚI
         */
        try {
            // Tìm hàng của symbol trong bảng
            const symbolRow = document.querySelector(`tr[data-symbol="${symbol}"]`);
            if (!symbolRow) return null;

            // Tìm cột thao tác hoặc tạo cột mới cho biểu đồ
            let chartCell = symbolRow.querySelector('.chart-cell');
            if (!chartCell) {
                chartCell = document.createElement('td');
                chartCell.className = 'chart-cell';
                chartCell.innerHTML = `
                    <div class="mini-chart-container">
                        <canvas id="mini-chart-${symbol}" width="100" height="30"></canvas>
                        <small class="chart-label">24h Trend</small>
                    </div>
                `;
                
                // Thêm vào cuối hàng
                symbolRow.appendChild(chartCell);
            }

            return document.getElementById(`mini-chart-${symbol}`);
        } catch (loi) {
            console.error(`Lỗi khi tạo container biểu đồ cho ${symbol}:`, loi);
            return null;
        }
    }

    taoBieuDoMini24h(symbol, data, labels) {
        /**
         * Tạo biểu đồ mini 24h cho một symbol - THÊM MỚI
         */
        try {
            const canvas = document.getElementById(`mini-chart-${symbol}`);
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            
            // Xóa biểu đồ cũ nếu có
            if (this.cacBieuDo[`mini-${symbol}`]) {
                this.cacBieuDo[`mini-${symbol}`].destroy();
            }

            // Chuẩn bị dữ liệu
            const priceChanges = data.hourly_price_changes || [];
            const volumeChanges = data.hourly_volume_changes || [];

            // Tạo biểu đồ đường đơn giản
            this.cacBieuDo[`mini-${symbol}`] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Thay đổi giá',
                        data: priceChanges,
                        borderColor: this.layMauChoSymbol(symbol),
                        backgroundColor: 'transparent',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        pointHoverRadius: 3,
                        tension: 0.2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: (context) => `${context[0].label}`,
                                label: (context) => `${context.parsed.y.toFixed(2)}%`
                            }
                        }
                    },
                    scales: {
                        x: { display: false },
                        y: { display: false }
                    },
                    elements: {
                        point: { radius: 0 }
                    }
                }
            });

        } catch (loi) {
            console.error(`Lỗi khi tạo biểu đồ mini cho ${symbol}:`, loi);
        }
    }

    capNhatBangVoiXuHuong24h(duLieu24h) {
        /**
         * Cập nhật bảng với thông tin xu hướng 24h - THÊM MỚI
         */
        try {
            if (!duLieu24h.symbols) return;

            Object.entries(duLieu24h.symbols).forEach(([symbol, data]) => {
                const row = document.querySelector(`tr[data-symbol="${symbol}"]`);
                if (!row) return;

                // Cập nhật các ô với dữ liệu 24h
                this.capNhatCacODuLieu24h(row, symbol, data);
            });

        } catch (loi) {
            console.error('Lỗi khi cập nhật bảng với xu hướng 24h:', loi);
        }
    }

    capNhatCacODuLieu24h(row, symbol, data24h) {
        /**
         * Cập nhật các ô dữ liệu với thông tin 24h - THÊM MỚI
         */
        try {
            // Tìm và cập nhật ô thay đổi giá
            const priceCell = row.querySelector('td:nth-child(2)');
            if (priceCell) {
                const priceChange24h = data24h.price_change_24h || 0;
                const trend24h = this.tinhXuHuong24h(data24h.hourly_price_changes || []);
                
                priceCell.innerHTML = `
                    <div class="${this.layLopThayDoi(priceChange24h)}">
                        <strong>${this.dinhDangPhanTram(priceChange24h)}</strong>
                        <i class="bi bi-${priceChange24h >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                    </div>
                    <small class="text-muted d-block">
                        24h: ${trend24h.label} 
                        <span class="badge badge-sm bg-${trend24h.color}">${trend24h.strength}</span>
                    </small>
                `;
            }

            // Tương tự cho volume và OI...
            this.capNhatOVolume24h(row, data24h);
            this.capNhatOOI24h(row, data24h);

        } catch (loi) {
            console.error(`Lỗi khi cập nhật ô dữ liệu 24h cho ${symbol}:`, loi);
        }
    }

    capNhatOVolume24h(row, data24h) {
        /**
         * Cập nhật ô Volume với dữ liệu 24h - THÊM MỚI
         */
        const volumeCell = row.querySelector('td:nth-child(3)');
        if (volumeCell) {
            const volumeChange24h = data24h.volume_change_24h || 0;
            const volatility = this.tinhDoBoiDong(data24h.hourly_volume_changes || []);
            
            volumeCell.innerHTML = `
                <div class="${this.layLopThayDoi(volumeChange24h)}">
                    <strong>${this.dinhDangPhanTram(volumeChange24h)}</strong>
                    <i class="bi bi-${volumeChange24h >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">
                    Biến động: ${volatility}
                </small>
            `;
        }
    }

    capNhatOOI24h(row, data24h) {
        /**
         * Cập nhật ô Open Interest với dữ liệu 24h - THÊM MỚI
         */
        const oiCell = row.querySelector('td:nth-child(4)');
        if (oiCell) {
            const oiChange24h = data24h.oi_change_24h || 0;
            const stability = this.tinhDoOnDinh(data24h.hourly_oi_changes || []);
            
            oiCell.innerHTML = `
                <div class="${this.layLopThayDoi(oiChange24h)}">
                    <strong>${this.dinhDangPhanTram(oiChange24h)}</strong>
                    <i class="bi bi-${oiChange24h >= 0 ? 'arrow-up' : 'arrow-down'} ms-1"></i>
                </div>
                <small class="text-muted d-block">
                    Ổn định: ${stability}
                </small>
            `;
        }
    }

    tinhXuHuong24h(hourlyChanges) {
        /**
         * Tính toán xu hướng 24h từ dữ liệu theo giờ - THÊM MỚI
         */
        if (!hourlyChanges || hourlyChanges.length === 0) {
            return { label: 'Không rõ', color: 'secondary', strength: 'N/A' };
        }

        const positiveHours = hourlyChanges.filter(change => change > 0).length;
        const negativeHours = hourlyChanges.filter(change => change < 0).length;
        const totalHours = hourlyChanges.length;

        const positiveRatio = positiveHours / totalHours;
        
        if (positiveRatio > 0.7) {
            return { label: 'Tăng mạnh', color: 'success', strength: 'Mạnh' };
        } else if (positiveRatio > 0.6) {
            return { label: 'Tăng', color: 'success', strength: 'Vừa' };
        } else if (positiveRatio > 0.4) {
            return { label: 'Sideway', color: 'warning', strength: 'Yếu' };
        } else if (positiveRatio > 0.3) {
            return { label: 'Giảm', color: 'danger', strength: 'Vừa' };
        } else {
            return { label: 'Giảm mạnh', color: 'danger', strength: 'Mạnh' };
        }
    }

    tinhDoBoiDong(hourlyChanges) {
        /**
         * Tính độ biến động từ dữ liệu theo giờ - THÊM MỚI
         */
        if (!hourlyChanges || hourlyChanges.length === 0) return 'N/A';

        const variance = this.tinhPhuongSai(hourlyChanges);
        const stdDev = Math.sqrt(variance);

        if (stdDev > 50) return 'Rất cao';
        if (stdDev > 30) return 'Cao';
        if (stdDev > 15) return 'Trung bình';
        if (stdDev > 5) return 'Thấp';
        return 'Rất thấp';
    }

    tinhDoOnDinh(hourlyChanges) {
        /**
         * Tính độ ổn định từ dữ liệu OI theo giờ - THÊM MỚI
         */
        if (!hourlyChanges || hourlyChanges.length === 0) return 'N/A';

        const avgChange = hourlyChanges.reduce((sum, change) => sum + Math.abs(change), 0) / hourlyChanges.length;

        if (avgChange < 0.5) return 'Rất ổn định';
        if (avgChange < 1) return 'Ổn định';
        if (avgChange < 2) return 'Trung bình';
        if (avgChange < 5) return 'Không ổn định';
        return 'Rất biến động';
    }

    tinhPhuongSai(arr) {
        /**
         * Tính phương sai của mảng số - THÊM MỚI
         */
        const mean = arr.reduce((sum, val) => sum + val, 0) / arr.length;
        return arr.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / arr.length;
    }

    taoNhanThoiGian24h() {
        /**
         * Tạo nhãn thời gian cho 24 giờ - THÊM MỚI
         */
        const labels = [];
        for (let i = 23; i >= 0; i--) {
            const hour = new Date();
            hour.setHours(hour.getHours() - i);
            labels.push(hour.getHours().toString().padStart(2, '0') + ':00');
        }
        return labels;
    }

    layMauChoSymbol(symbol) {
        /**
         * Lấy màu đặc trưng cho từng symbol - THÊM MỚI
         */
        const mauSymbol = {
            'BTCUSDT': '#f7931e',
            'ETHUSDT': '#627eea',
            'BNBUSDT': '#f0b90b',
            'SOLUSDT': '#9945ff',
            'DOGEUSDT': '#c2a633'
        };
        return mauSymbol[symbol] || '#6c757d';
    }

    capNhatThoiGianCapNhatCuoi(thoiGian) {
        const phanTuCapNhat = document.getElementById('lastUpdateTime');
        if (phanTuCapNhat) {
            const ngay = new Date(thoiGian);
            phanTuCapNhat.innerHTML = `
                <i class="bi bi-clock"></i>
                Cập nhật lần cuối: ${ngay.toLocaleString('vi-VN')}
                <span class="badge bg-success ms-2">Trực Tuyến 24H</span>
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

        // Sau khi tạo bảng, cập nhật với dữ liệu 24h nếu có
        if (this.khoLuuTru.hourly24h) {
            this.capNhatBangVoiXuHuong24h(this.khoLuuTru.hourly24h);
        }
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
        alert(`Hiển thị phân tích chi tiết cho ${symbol} với dữ liệu 24h theo giờ`);
        // TODO: Triển khai view chi tiết với biểu đồ 24h, chỉ báo, v.v.
    }

    hienThiBieuDo(symbol) {
        // Mở biểu đồ trong modal hoặc tab mới
        alert(`Mở biểu đồ nâng cao cho ${symbol} với tracking 24h`);
        // TODO: Triển khai biểu đồ nâng cao với TradingView hoặc tương tự
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
            console.log('🔄 Tự động làm mới dữ liệu...');
            await this.taiDuLieuThoiGianThuc();
            await this.taiDuLieu24hTheoGio(); // Cập nhật dữ liệu 24h
            await this.capNhatGiaoDienThoiGianThuc();
        }, 5 * 60 * 1000);

        // Làm mới toàn bộ dữ liệu mỗi 30 phút
        setInterval(async () => {
            console.log('🔄 Làm mới toàn bộ dữ liệu...');
            await this.lamMoiDuLieuManh();
        }, 30 * 60 * 1000);

        // Làm mới dữ liệu 24h theo giờ mỗi giờ - THÊM MỚI
        setInterval(async () => {
            console.log('🕒 Làm mới dữ liệu 24h theo giờ...');
            await this.taiDuLieu24hTheoGio();
            await this.capNhatBieuDo24hTheoGio();
        }, 60 * 60 * 1000); // Mỗi giờ
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