binance-oi-monitor/
│
├── config/                     # Cấu hình hệ thống
│   └── settings.py
│
├── data_collector/            # Thu thập dữ liệu từ Binance
│   ├── __init__.py
│   ├── binance_api.py
│   └── historical_data.py
│
├── data_storage/              # Lưu trữ dữ liệu
│   ├── __init__.py
│   └── database.py
│
├── data_analyzer/             # Phân tích dữ liệu
│   ├── __init__.py
│   ├── metrics.py
│   └── anomaly_detector.py
│
├── alerting/                  # Gửi cảnh báo
│   ├── __init__.py
│   └── telegram_bot.py
│
├── visualization/             # Tạo biểu đồ và báo cáo
│   ├── __init__.py
│   ├── chart_generator.py
│   └── report_generator.py
│
├── utils/                     # Các tiện ích
│   └── helpers.py
│
├── docs/                       # Trang web GitHub Pages
│   ├── index.html
│   ├── css/
│   └── js/
│
├── .github/workflows/         # GitHub Actions
│   └── update_data.yml
│
├── data/                      # Thư mục dữ liệu
│   ├── charts/                # Biểu đồ được tạo
│   ├── json/                  # Dữ liệu JSON cho web
│   └── reports/               # Báo cáo
│
├── logs/                      # Log hệ thống
├── .env                       # Biến môi trường
├── .gitignore
├── main.py                    # Script chính
├── README.md
└── requirements.txt

# Hệ thống theo dõi Open Interest (OI) và Volume từ Binance

Một hệ thống toàn diện để theo dõi, phân tích và cảnh báo về biến động Open Interest và Volume của các cặp giao dịch trên Binance Futures.

## Tính năng

- **Thu thập dữ liệu**: Lấy dữ liệu OI và Volume từ Binance API
- **Phân tích**: Phát hiện bất thường và tính toán các chỉ số thị trường
- **Cảnh báo**: Gửi thông báo qua Telegram khi phát hiện bất thường
- **Hiển thị**: Trực quan hóa dữ liệu thông qua GitHub Pages
- **Lưu trữ**: Lưu trữ dữ liệu lịch sử trong cơ sở dữ liệu SQLite
- **Tự động hóa**: Cập nhật dữ liệu tự động thông qua GitHub Actions

## Cài đặt

### Yêu cầu

- Python 3.8+
- Tài khoản Binance với API key
- Tài khoản GitHub
- Bot Telegram (để nhận cảnh báo)

### Cài đặt thư viện

```bash
pip install -r requirements.txt

# Thu thập dữ liệu lịch sử
python main.py --collect
# Cập nhật dữ liệu realtime
python main.py --update
# Phát hiện bất thường
python main.py --detect
# Tạo báo cáo và biểu đồ
python main.py --report
# Gửi báo cáo hàng ngày
python main.py --daily
# Chạy tất cả các tác vụ theo lịch
python main.py --schedule
# Chạy tất cả (mặc định)
python main.py