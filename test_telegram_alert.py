#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test gửi cảnh báo qua Telegram
File này dùng để kiểm tra kết nối và chức năng gửi cảnh báo Telegram
"""

import sys
import time
from datetime import datetime
import logging

# Cấu hình logging cơ bản
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import TelegramBot từ module alerting
try:
    from alerting.telegram_bot import TelegramBot
except ImportError:
    # Nếu đang chạy từ thư mục hiện tại
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from alerting.telegram_bot import TelegramBot


def test_telegram_connection():
    """Kiểm tra kết nối đến Telegram API"""
    print("\n=== Kiểm tra kết nối Telegram ===")
    
    bot = TelegramBot()
    
    # Kiểm tra thông tin kết nối và proxy
    connection_info = bot.check_proxy_settings()
    print(f"Thông tin kết nối: {connection_info}")
    
    # Kiểm tra kết nối đến Telegram API
    if bot.test_connection(force=True):
        print("✅ Kết nối Telegram thành công!")
    else:
        print("❌ Không thể kết nối đến Telegram API!")
        print("Vui lòng kiểm tra TOKEN, kết nối internet và proxy (nếu có)")
        return False
    
    return True


def test_send_message():
    """Kiểm tra gửi tin nhắn văn bản đơn giản"""
    print("\n=== Kiểm tra gửi tin nhắn đơn giản ===")
    
    bot = TelegramBot()
    
    # Gửi tin nhắn test
    message = (
        "🧪 <b>Kiểm tra gửi tin nhắn</b>\n\n"
        f"⏰ Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "✅ Đây là tin nhắn test từ hệ thống theo dõi OI & Volume Binance."
    )
    
    result = bot.send_message(message)
    
    if result:
        print("✅ Gửi tin nhắn thành công!")
    else:
        print("❌ Không thể gửi tin nhắn!")
    
    return result


def test_send_anomaly():
    """Kiểm tra gửi cảnh báo bất thường"""
    print("\n=== Kiểm tra gửi cảnh báo bất thường ===")
    
    bot = TelegramBot()
    
    # Tạo dữ liệu anomaly giả lập
    anomaly = {
        'id': 1,
        'symbol': 'BTCUSDT',
        'timestamp': datetime.now(),
        'data_type': 'OI_Value',
        'value': 10000000000,  # 10 tỷ USDT
        'z_score': 3.5,
        'message': 'Open Interest tăng đột biến trong 1 giờ qua, vượt ngưỡng +30%'
    }
    
    # Gửi cảnh báo
    result = bot.send_anomaly_alert(anomaly)
    
    if result:
        print("✅ Gửi cảnh báo thành công!")
    else:
        print("❌ Không thể gửi cảnh báo!")
    
    return result


def test_send_daily_report():
    """Kiểm tra gửi báo cáo hàng ngày"""
    print("\n=== Kiểm tra gửi báo cáo hàng ngày ===")
    
    bot = TelegramBot()
    
    # Tạo dữ liệu báo cáo giả lập
    symbol = 'ETHUSDT'
    sentiment = {
        'sentiment_label': 'bullish',
        'price_change': 0.05  # 5%
    }
    oi_change = 7.5
    volume_change = 12.3
    
    # Gửi báo cáo
    result = bot.send_daily_report(
        symbol=symbol,
        sentiment=sentiment,
        oi_change=oi_change,
        volume_change=volume_change
    )
    
    if result:
        print("✅ Gửi báo cáo thành công!")
    else:
        print("❌ Không thể gửi báo cáo!")
    
    return result


def main():
    """Hàm chính chạy tất cả các test"""
    print("🔍 Bắt đầu kiểm tra Telegram Bot...")
    
    # Kiểm tra kết nối
    if not test_telegram_connection():
        print("\n⚠️ Không thể tiếp tục do lỗi kết nối!")
        return False
    
    # Đợi 1 giây
    time.sleep(1)
    
    # Kiểm tra gửi tin nhắn đơn giản
    if not test_send_message():
        print("\n⚠️ Gặp vấn đề khi gửi tin nhắn đơn giản!")
    
    # Đợi 2 giây để tránh rate limit
    time.sleep(2)
    
    # Kiểm tra gửi cảnh báo bất thường
    if not test_send_anomaly():
        print("\n⚠️ Gặp vấn đề khi gửi cảnh báo bất thường!")
    
    # Đợi 2 giây để tránh rate limit
    time.sleep(2)
    
    # Kiểm tra gửi báo cáo hàng ngày
    if not test_send_daily_report():
        print("\n⚠️ Gặp vấn đề khi gửi báo cáo hàng ngày!")
    
    print("\n✅ Hoàn thành kiểm tra Telegram Bot!")
    return True


def debug_connection_issues():
    """Debug chi tiết vấn đề kết nối"""
    import socket
    import requests
    
    print("\n=== Debug chi tiết vấn đề kết nối ===")
    
    # Kiểm tra kết nối internet cơ bản
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        print("✅ Kết nối internet: OK")
    except:
        print("❌ Kết nối internet: Không thể kết nối đến google.com")
    
    # Kiểm tra kết nối đến Telegram API
    try:
        socket.create_connection(("api.telegram.org", 443), timeout=5)
        print("✅ Kết nối đến api.telegram.org: OK")
    except:
        print("❌ Kết nối đến api.telegram.org: Không thể kết nối")
    
    # Kiểm tra proxy hệ thống
    proxies = requests.utils.getproxies()
    print(f"Proxy hệ thống: {proxies}")
    
    # Kiểm tra IP công khai
    try:
        ip_response = requests.get('https://api.ipify.org', timeout=5)
        public_ip = ip_response.text if ip_response.status_code == 200 else 'Unknown'
        print(f"IP công khai: {public_ip}")
    except:
        print("❌ Không thể xác định IP công khai")
    
    # Thử gửi request đến Telegram API
    try:
        response = requests.get('https://api.telegram.org/bot123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11/getMe', timeout=5)
        print(f"Phản hồi từ Telegram API (token không hợp lệ): {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"❌ Không thể gửi request đến Telegram API: {str(e)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        debug_connection_issues()
    else:
        main()