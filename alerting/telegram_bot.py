import requests
import time
from datetime import datetime
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, setup_logging

logger = setup_logging(__name__, 'telegram_bot.log')

class TelegramBot:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        logger.info("Khởi tạo Telegram Bot")
    
    def send_message(self, message):
        """Gửi tin nhắn văn bản đến Telegram"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, data=data)
            
            if response.status_code == 200:
                logger.info("Đã gửi tin nhắn đến Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi tin nhắn đến Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi tin nhắn đến Telegram: {str(e)}")
            return False
    
    def send_photo(self, photo_path, caption=None):
        """Gửi ảnh đến Telegram"""
        try:
            url = f"{self.base_url}/sendPhoto"
            data = {"chat_id": self.chat_id}
            
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
            
            files = {"photo": open(photo_path, "rb")}
            response = requests.post(url, data=data, files=files)
            
            if response.status_code == 200:
                logger.info("Đã gửi ảnh đến Telegram thành công")
                return True
            else:
                logger.error(f"Lỗi khi gửi ảnh đến Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Lỗi khi gửi ảnh đến Telegram: {str(e)}")
            return False
    
    def send_anomaly_alert(self, anomaly):
        """Gửi cảnh báo về bất thường đến Telegram"""
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
            logger.error(f"Lỗi khi gửi cảnh báo bất thường: {str(e)}")
            return False
    
    def send_daily_report(self, symbol, sentiment, oi_change, volume_change, chart_path=None):
        """Gửi báo cáo hàng ngày đến Telegram"""
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
            logger.error(f"Lỗi khi gửi báo cáo hàng ngày: {str(e)}")
            return False
    
    def send_anomalies(self, db):
        """Gửi tất cả các cảnh báo bất thường chưa được thông báo"""
        try:
            # Lấy danh sách các bất thường chưa thông báo
            anomalies_df = db.get_anomalies(notified=False)
            
            if anomalies_df.empty:
                logger.info("Không có bất thường nào cần thông báo")
                return True
            
            sent_count = 0
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
                if self.send_anomaly_alert(anomaly_obj):
                    # Đánh dấu là đã thông báo
                    db.mark_anomaly_as_notified(anomaly['id'])
                    sent_count += 1
                    
                    # Đợi một chút để tránh gửi quá nhiều tin nhắn cùng lúc
                    time.sleep(1)
            
            logger.info(f"Đã gửi {sent_count}/{len(anomalies_df)} cảnh báo bất thường")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi gửi các cảnh báo bất thường: {str(e)}")
            return False