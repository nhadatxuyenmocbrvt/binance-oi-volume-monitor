import os
import logging
from logging.handlers import RotatingFileHandler
import dotenv

# Tải biến môi trường từ file .env
dotenv.load_dotenv()

# Cấu hình logging hỗ trợ Unicode
def setup_logging(name, log_file='app.log'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Tạo thư mục logs nếu chưa tồn tại
    os.makedirs('logs', exist_ok=True)
    
    # Định dạng log với hỗ trợ Unicode
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler ghi log ra file
    file_handler = RotatingFileHandler(f'logs/{log_file}', maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Handler hiển thị log trên console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Thêm handlers vào logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Cấu hình Binance API
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Cấu hình Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Cấu hình cơ sở dữ liệu
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
DB_PATH = os.getenv('DB_PATH', './data/market_data.db')

# Cấu hình cho web tối ưu
WEB_OUTPUT_DIR = './docs/assets/data'
ENABLE_24H_TRACKING = True

# Cấu hình cho phân tích dữ liệu
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT", "DOTUSDT", "AVAXUSDT", "PNUTUSDT",
    "LTCUSDT", "LINKUSDT", "UNIUSDT", "TRXUSDT", "ETCUSDT", "XLMUSDT", "1000PEPEUSDT", "SUIUSDT", "TRUMPUSDT", "AAVEUSDT",
    "WIFUSDT", "LDOUSDT", "WLDUSDT", "1000SHIBUSDT", "GALAUSDT", "1000BONKUSDT", "NEARUSDT", "BCHUSDT", "OPUSDT", "DOTUSDT",
    "INJUSDT", "APTUSDT", "FARTCOINUSDT", "HBARUSDT", "FILUSDT", "ONDOUSDT", "TAOUSDT", "CAKEUSDT", "FETUSDT", "1000FLOKIUSDT",
    "ATHUSDT", "NEIROUSDT", "POLUSDT", "ORDIUSDT", "RENDERUSDT", "PENDLEUSDT", "ALGOUSDT", "LPTUSDT", "TONUSDT", "ENAUSDT",
    "ETHFIUSDT", "EIGENUSDT", "AIXBTUSDT", "CGPTUSDT", "ENSUSDT", "BOMEUSDT",
    # Thêm các cặp tiền khác...
]
TIMEFRAMES = ['1h', '4h', '1d']
LOOKBACK_DAYS = 29
ANOMALY_THRESHOLD = 4  # Số lần độ lệch chuẩn để xác định bất thường

# Cấu hình cho cập nhật dữ liệu
UPDATE_INTERVAL = 60  # Cập nhật mỗi 60 giây cho dữ liệu realtime

# Thêm vào cuối file settings.py

# Cấu hình proxy cho Telegram (tùy chọn)
# Để trống nếu không sử dụng proxy
PROXY_SETTINGS = {
    'http': 'http://mitchellcryptogroup:mcg396879@45.252.58.93:6722',
    'https': 'http://mitchellcryptogroup:mcg396879@45.252.58.93:6722'  # Thêm thông tin xác thực
}

# Tùy chọn xác thực cho proxy
PROXY_USERNAME = 'mitchellcryptogroup'
PROXY_PASSWORD = 'mcg396879'

# Timeout và retry cho Telegram
TELEGRAM_TIMEOUT = 15  # Thời gian chờ request (giây)
TELEGRAM_MAX_RETRIES = 3  # Số lần thử lại tối đa
TELEGRAM_BACKOFF_FACTOR = 0.5  # Hệ số cho exponential backoff

# Tắt báo cáo hàng ngày
ENABLE_DAILY_REPORTS = False