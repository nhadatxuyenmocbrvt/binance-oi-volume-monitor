import requests
import time
import socket
from requests.adapters import HTTPAdapter
# Sửa đường dẫn import cho Retry
try:
    # Cách import mới (khuyên dùng)
    from urllib3.util.retry import Retry
except ImportError:
    # Fallback cho các phiên bản cũ
    # pyright: ignore
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

from datetime import datetime, timedelta
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, setup_logging

# Thử import các cài đặt proxy nếu có
try:
    from config.settings import PROXY_SETTINGS, TELEGRAM_TIMEOUT, TELEGRAM_MAX_RETRIES, TELEGRAM_BACKOFF_FACTOR
except ImportError:
    # Cài đặt mặc định nếu không tìm thấy
    PROXY_SETTINGS = {'http': '', 'https': ''}
    TELEGRAM_TIMEOUT = 15
    TELEGRAM_MAX_RETRIES = 3
    TELEGRAM_BACKOFF_FACTOR = 0.5

logger = setup_logging(__name__, 'telegram_bot.log')

class TelegramBot:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID, 
                 max_retries=TELEGRAM_MAX_RETRIES, backoff_factor=TELEGRAM_BACKOFF_FACTOR):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = self._create_session()
        self.connection_status = None
        self.last_connection_test = None
        logger.info("Khởi tạo Telegram Bot")
        
        # Kiểm tra kết nối khi khởi tạo
        self.test_connection()
    
    def _create_session(self):
        """Tạo session với retry logic"""
        session = requests.Session()
        
        # Áp dụng cài đặt proxy nếu có
        if PROXY_SETTINGS.get('http') or PROXY_SETTINGS.get('https'):
            session.proxies.update(PROXY_SETTINGS)
            logger.info(f"🔌 Đã cấu hình proxy: {PROXY_SETTINGS}")
        
        # Cấu hình retry
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def test_connection(self, force=False):
        """Kiểm tra kết nối đến Telegram API"""
        # Nếu đã kiểm tra trong 5 phút qua và không bắt buộc kiểm tra lại
        if not force and self.last_connection_test and \
           datetime.now() - self.last_connection_test < timedelta(minutes=5):
            return self.connection_status
        
        try:
            # Sử dụng getMe để kiểm tra token và kết nối
            url = f"{self.base_url}/getMe"
            response = self.session.get(url, timeout=TELEGRAM_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    bot_name = data['result']['username']
                    logger.info(f"✅ Kết nối Telegram thành công. Bot: @{bot_name}")
                    self.connection_status = True
                else:
                    logger.error(f"❌ Token bot không hợp lệ: {data['description']}")
                    self.connection_status = False
            else:
                logger.error(f"❌ Không thể kết nối đến Telegram API: {response.status_code}")
                self.connection_status = False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Lỗi kết nối mạng: {str(e)}")
            if "certificate verify failed" in str(e):
                logger.error("🔒 Có vấn đề với chứng chỉ SSL. Hãy kiểm tra kết nối mạng và cấu hình.")
            elif "getaddrinfo failed" in str(e) or "Name or service not known" in str(e):
                logger.error("🌐 Không thể phân giải tên miền api.telegram.org. Kiểm tra DNS và kết nối internet.")
            elif "Connection refused" in str(e):
                logger.error("🔌 Kết nối bị từ chối. Kiểm tra tường lửa và proxy.")
            self.connection_status = False
        except requests.exceptions.Timeout:
            logger.error("⏱️ Kết nối đến Telegram API bị timeout")
            self.connection_status = False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi kiểm tra kết nối: {str(e)}")
            self.connection_status = False
        
        self.last_connection_test = datetime.now()
        return self.connection_status
    
    def send_message(self, message, retry_count=0):
        """Gửi tin nhắn văn bản đến Telegram với xử lý lỗi tốt hơn"""
        # Kiểm tra kết nối trước khi gửi
        if not self.test_connection():
            logger.warning("⚠️ Không thể gửi tin nhắn do kết nối Telegram không khả dụng")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            # Đặt timeout để tránh chờ quá lâu
            response = self.session.post(url, data=data, timeout=TELEGRAM_TIMEOUT)
            
            if response.status_code == 200:
                logger.info("📤 Đã gửi tin nhắn đến Telegram thành công")
                return True
            elif response.status_code == 429:
                # Rate limiting - lấy thời gian chờ và thử lại
                retry_after = response.json().get('parameters', {}).get('retry_after', 30)
                logger.warning(f"⏳ Bị rate limit, chờ {retry_after}s và thử lại")
                if retry_count < self.max_retries:
                    time.sleep(retry_after)
                    return self.send_message(message, retry_count + 1)
                else:
                    logger.error("❌ Đã vượt quá số lần thử lại do rate limit")
                    return False
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('description', 'Unknown error')
                    logger.error(f"❌ Lỗi API Telegram: {response.status_code} - {error_message}")
                except:
                    logger.error(f"❌ Lỗi không xác định từ API Telegram: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Lỗi kết nối khi gửi tin nhắn: {str(e)}")
            
            # Thử lại sau khi chờ với backoff
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * self.backoff_factor
                logger.info(f"⏳ Đang chờ {wait_time}s trước khi thử lại...")
                time.sleep(wait_time)
                return self.send_message(message, retry_count + 1)
            
            return False
        except requests.exceptions.Timeout:
            logger.error("⏱️ Hết thời gian chờ khi gửi tin nhắn")
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * self.backoff_factor
                logger.info(f"⏳ Đang chờ {wait_time}s trước khi thử lại...")
                time.sleep(wait_time)
                return self.send_message(message, retry_count + 1)
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi gửi tin nhắn: {str(e)}")
            return False
    
    def send_photo(self, photo_path, caption=None, retry_count=0):
        """Gửi ảnh đến Telegram với xử lý lỗi tốt hơn"""
        # Kiểm tra kết nối trước khi gửi
        if not self.test_connection():
            logger.warning("⚠️ Không thể gửi ảnh do kết nối Telegram không khả dụng")
            return False
            
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {"chat_id": self.chat_id}
            
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
            
            # Kiểm tra file tồn tại
            try:
                with open(photo_path, "rb") as photo_file:
                    files = {"photo": photo_file}
                    # Đặt timeout để tránh chờ quá lâu
                    response = self.session.post(url, data=data, files=files, timeout=TELEGRAM_TIMEOUT * 2)
            except FileNotFoundError:
                logger.error(f"❌ Không tìm thấy file ảnh: {photo_path}")
                return False
            
            if response.status_code == 200:
                logger.info("📤 Đã gửi ảnh đến Telegram thành công")
                return True
            elif response.status_code == 429:
                # Rate limiting - lấy thời gian chờ và thử lại
                retry_after = response.json().get('parameters', {}).get('retry_after', 30)
                logger.warning(f"⏳ Bị rate limit, chờ {retry_after}s và thử lại")
                if retry_count < self.max_retries:
                    time.sleep(retry_after)
                    return self.send_photo(photo_path, caption, retry_count + 1)
                else:
                    logger.error("❌ Đã vượt quá số lần thử lại do rate limit")
                    return False
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('description', 'Unknown error')
                    logger.error(f"❌ Lỗi API Telegram: {response.status_code} - {error_message}")
                except:
                    logger.error(f"❌ Lỗi không xác định từ API Telegram: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🔌 Lỗi kết nối khi gửi ảnh: {str(e)}")
            
            # Thử lại sau khi chờ với backoff
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * self.backoff_factor
                logger.info(f"⏳ Đang chờ {wait_time}s trước khi thử lại...")
                time.sleep(wait_time)
                return self.send_photo(photo_path, caption, retry_count + 1)
            
            return False
        except requests.exceptions.Timeout:
            logger.error("⏱️ Hết thời gian chờ khi gửi ảnh")
            if retry_count < self.max_retries:
                wait_time = (2 ** retry_count) * self.backoff_factor
                logger.info(f"⏳ Đang chờ {wait_time}s trước khi thử lại...")
                time.sleep(wait_time)
                return self.send_photo(photo_path, caption, retry_count + 1)
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi không xác định khi gửi ảnh: {str(e)}")
            return False
    
    def send_anomaly_alert(self, anomaly):
        """Gửi cảnh báo về bất thường đến Telegram với xử lý lỗi tốt hơn"""
        try:
            # Định dạng thời gian
            if isinstance(anomaly['timestamp'], datetime):
                timestamp_str = anomaly['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = str(anomaly['timestamp'])
            
            # Tạo URL TradingView cho coin tương ứng
            symbol = anomaly['symbol']
            tradingview_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}PERP"
            
            # Tạo tin nhắn cảnh báo
            message = f"🚨 <b>CẢNH BÁO BẤT THƯỜNG</b> 🚨\n\n"
            message += f"🪙 <b>Symbol:</b> {anomaly['symbol']}\n"
            message += f"📊 <b>Loại dữ liệu:</b> {anomaly['data_type']}\n"
            message += f"⏰ <b>Thời gian:</b> {timestamp_str}\n"
            message += f"📈 <b>Giá trị:</b> {anomaly['value']:.2f}\n"
            message += f"📏 <b>Z-score:</b> {anomaly['z_score']:.2f}\n\n"
            message += f"📝 <b>Thông tin:</b> {anomaly['message']}\n\n"
            message += f"🔗 <a href='{tradingview_url}'>Xem chi tiết trên TradingView</a>"
            
            return self.send_message(message)
        except Exception as e:
            logger.error(f"❌ Lỗi khi gửi cảnh báo bất thường: {str(e)}")
            return False
    
    def send_daily_report(self, symbol, sentiment, oi_change, volume_change, chart_path=None):
        """Gửi báo cáo hàng ngày đến Telegram với xử lý lỗi tốt hơn"""
        try:
            # Tạo URL TradingView cho coin tương ứng
            tradingview_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}PERP"
            
            # Tạo tin nhắn báo cáo
            message = f"📊 <b>BÁO CÁO HÀNG NGÀY - {symbol}</b> 📊\n\n"
            message += f"⏰ <b>Thời gian:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Thông tin sentiment
            if sentiment:
                message += f"🧠 <b>Sentiment:</b> {sentiment['sentiment_label']}\n"
                message += f"📈 <b>Thay đổi giá:</b> {sentiment['price_change']*100:.2f}%\n"
            
            # Thông tin OI và Volume
            message += f"📊 <b>Thay đổi OI:</b> {oi_change:.2f}%\n"
            message += f"📊 <b>Thay đổi Volume:</b> {volume_change:.2f}%\n\n"
            
            message += f"🔗 <a href='{tradingview_url}'>Xem chi tiết trên TradingView</a>"
            
            # Nếu có đường dẫn biểu đồ, gửi ảnh kèm caption
            if chart_path:
                return self.send_photo(chart_path, message)
            else:
                return self.send_message(message)
        except Exception as e:
            logger.error(f"❌ Lỗi khi gửi báo cáo hàng ngày: {str(e)}")
            return False
    
    def send_anomalies(self, db):
        """Gửi tất cả các cảnh báo bất thường chưa được thông báo với xử lý lỗi tốt hơn"""
        try:
            # Kiểm tra kết nối trước khi thử
            if not self.test_connection():
                logger.warning("⚠️ Không thể gửi cảnh báo do kết nối Telegram không khả dụng")
                return False
                
            # Lấy danh sách các bất thường chưa thông báo
            anomalies_df = db.get_anomalies(notified=False)
            
            if anomalies_df.empty:
                logger.info("ℹ️ Không có bất thường nào cần thông báo")
                return True
            
            logger.info(f"🔔 Tìm thấy {len(anomalies_df)} cảnh báo cần gửi")
            
            sent_count = 0
            failed_count = 0
            for _, anomaly in anomalies_df.iterrows():
                # Tạo đối tượng anomaly để gửi
                anomaly_obj = {
                    'id': anomaly['id'],
                    'symbol': anomaly['symbol'],
                    'timestamp': anomaly['timestamp'],
                    'data_type': anomaly['data_type'],
                    'value': anomaly['value'],
                    'z_score': anomaly['z_score'],
                    'message': anomaly['message']
                }
                
                # Gửi cảnh báo
                logger.info(f"🔔 Đang gửi cảnh báo cho {anomaly['symbol']} - {anomaly['data_type']}")
                if self.send_anomaly_alert(anomaly_obj):
                    # Đánh dấu là đã thông báo
                    db.mark_anomaly_as_notified(anomaly['id'])
                    sent_count += 1
                    
                    # Đợi một chút để tránh gửi quá nhiều tin nhắn cùng lúc
                    time.sleep(1.5)
                else:
                    failed_count += 1
                    logger.error(f"❌ Không thể gửi cảnh báo cho anomaly ID {anomaly['id']}")
                    
                    # Nếu đã có 3 lỗi liên tiếp, tạm dừng để tránh bị chặn
                    if failed_count >= 3:
                        logger.warning("⚠️ Đã có 3 lỗi liên tiếp, tạm dừng gửi cảnh báo")
                        break
            
            logger.info(f"📊 Kết quả: Đã gửi {sent_count}/{len(anomalies_df)} cảnh báo bất thường, {failed_count} thất bại")
            return sent_count > 0
        except Exception as e:
            logger.error(f"❌ Lỗi khi gửi các cảnh báo bất thường: {str(e)}")
            return False
    
    def check_proxy_settings(self):
        """Kiểm tra cài đặt proxy và đề xuất cấu hình"""
        try:
            # Kiểm tra proxy của hệ thống
            proxy_settings = {
                'http': requests.utils.getproxies().get('http', 'Not set'),
                'https': requests.utils.getproxies().get('https', 'Not set')
            }
            
            # Thử kiểm tra IP công khai
            try:
                ip_response = requests.get('https://api.ipify.org', timeout=5)
                public_ip = ip_response.text if ip_response.status_code == 200 else 'Unknown'
            except:
                public_ip = 'Could not determine'
            
            # Kiểm tra kết nối internet cơ bản
            try:
                socket.create_connection(("www.google.com", 80), timeout=5)
                internet_connection = "OK"
            except:
                internet_connection = "Failed"
            
            # Kiểm tra kết nối đến API Telegram
            try:
                socket.create_connection(("api.telegram.org", 443), timeout=5)
                telegram_connection = "OK"
            except:
                telegram_connection = "Failed"
            
            result = {
                'proxy_settings': proxy_settings,
                'public_ip': public_ip,
                'internet_connection': internet_connection,
                'telegram_connection': telegram_connection,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"📡 Thông tin kết nối: {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra cài đặt proxy: {str(e)}")
            return None
            
    def send_test_message(self):
        """Gửi tin nhắn kiểm tra để xác minh kết nối Telegram"""
        test_message = (
            "🧪 <b>Kiểm tra kết nối Telegram</b>\n\n"
            f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "✅ Kết nối thành công!\n\n"
            "Bot đã sẵn sàng gửi cảnh báo và báo cáo."
        )
        return self.send_message(test_message)