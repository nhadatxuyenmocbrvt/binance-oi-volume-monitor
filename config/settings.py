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
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
TIMEFRAMES = ['1h', '4h', '1d']
LOOKBACK_DAYS = 29
ANOMALY_THRESHOLD = 2.5  # Số lần độ lệch chuẩn để xác định bất thường

# Cấu hình cho cập nhật dữ liệu
UPDATE_INTERVAL = 60  # Cập nhật mỗi 60 giây cho dữ liệu realtime