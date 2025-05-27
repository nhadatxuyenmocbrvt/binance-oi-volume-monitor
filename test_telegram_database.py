#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test gửi cảnh báo Telegram từ database
File này dùng để kiểm tra chức năng gửi tất cả cảnh báo chưa thông báo từ database
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

# Import các module cần thiết
try:
    from alerting.telegram_bot import TelegramBot
    from data_storage.database import Database
except ImportError:
    # Nếu đang chạy từ thư mục hiện tại
    import os
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from alerting.telegram_bot import TelegramBot
    from data_storage.database import Database


def create_test_anomalies(db, count=3):
    """Tạo các anomaly giả lập trong database để test"""
    print(f"\n=== Tạo {count} anomaly giả lập trong database ===")
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    data_types = ['OI_Value', 'Volume_USDT', 'Price']
    
    created_count = 0
    
    for i in range(count):
        # Chọn symbol và data_type
        symbol = symbols[i % len(symbols)]
        data_type = data_types[i % len(data_types)]
        
        # Tạo anomaly data
        anomaly_data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'data_type': data_type,
            'value': 1000000 * (i + 1),  # Giá trị khác nhau
            'z_score': 2.5 + (i * 0.5),  # Z-score tăng dần
            'message': f'Test anomaly #{i+1}: {data_type} của {symbol} có biến động bất thường'
        }
        
        # Lưu vào database
        if db.save_anomaly(anomaly_data):
            created_count += 1
            print(f"✅ Đã tạo anomaly #{i+1}: {symbol} - {data_type}")
        else:
            print(f"❌ Không thể tạo anomaly #{i+1}")
    
    print(f"✅ Đã tạo {created_count}/{count} anomaly trong database")
    return created_count


def check_anomalies(db):
    """Kiểm tra các anomaly trong database"""
    print("\n=== Kiểm tra anomalies trong database ===")
    
    # Lấy tất cả anomalies
    all_anomalies = db.get_anomalies(limit=10)
    
    # Lấy anomalies chưa thông báo
    not_notified_anomalies = db.get_anomalies(limit=10, notified=False)
    
    # Lấy anomalies đã thông báo
    notified_anomalies = db.get_anomalies(limit=10, notified=True)
    
    print(f"Tổng số anomalies: {len(all_anomalies)}")
    print(f"Anomalies chưa thông báo: {len(not_notified_anomalies)}")
    print(f"Anomalies đã thông báo: {len(notified_anomalies)}")
    
    # Hiển thị chi tiết anomalies chưa thông báo
    if not not_notified_anomalies.empty:
        print("\nDanh sách anomalies chưa thông báo:")
        for i, anomaly in not_notified_anomalies.iterrows():
            print(f"  {i+1}. ID: {anomaly['id']} - {anomaly['symbol']} - {anomaly['data_type']} - {anomaly['timestamp']}")
    
    return len(not_notified_anomalies)


def test_send_all_anomalies(db):
    """Kiểm tra gửi tất cả anomalies chưa thông báo"""
    print("\n=== Kiểm tra gửi tất cả anomalies chưa thông báo ===")
    
    # Tạo bot Telegram
    bot = TelegramBot()
    
    # Kiểm tra kết nối
    if not bot.test_connection():
        print("❌ Không thể kết nối đến Telegram API!")
        return False
    
    # Đếm số anomalies chưa thông báo
    not_notified_count = check_anomalies(db)
    
    if not_notified_count == 0:
        print("⚠️ Không có anomalies chưa thông báo để gửi!")
        # Tạo thêm anomalies để test
        create_test_anomalies(db, count=3)
        not_notified_count = check_anomalies(db)
    
    # Gửi tất cả anomalies chưa thông báo
    print("\nĐang gửi tất cả anomalies chưa thông báo...")
    result = bot.send_anomalies(db)
    
    # Kiểm tra lại sau khi gửi
    print("\nKiểm tra lại sau khi gửi:")
    remaining_count = check_anomalies(db)
    
    if result and remaining_count < not_notified_count:
        print(f"✅ Đã gửi thành công {not_notified_count - remaining_count}/{not_notified_count} anomalies!")
    else:
        print(f"❌ Gặp vấn đề khi gửi anomalies! Còn lại {remaining_count}/{not_notified_count} chưa gửi.")
    
    return result


def test_mark_as_notified(db):
    """Kiểm tra hàm đánh dấu anomaly đã thông báo"""
    print("\n=== Kiểm tra hàm đánh dấu anomaly đã thông báo ===")
    
    # Lấy anomalies chưa thông báo
    not_notified_anomalies = db.get_anomalies(limit=5, notified=False)
    
    if not_notified_anomalies.empty:
        print("⚠️ Không có anomalies chưa thông báo để test!")
        return False
    
    # Lấy ID của anomaly đầu tiên
    anomaly_id = not_notified_anomalies.iloc[0]['id']
    
    print(f"Đánh dấu anomaly ID {anomaly_id} là đã thông báo...")
    result = db.mark_anomaly_as_notified(anomaly_id)
    
    # Kiểm tra lại
    notified_anomalies = db.get_anomalies(limit=5, notified=True)
    
    if result and not notified_anomalies.empty and anomaly_id in notified_anomalies['id'].values:
        print(f"✅ Đã đánh dấu anomaly ID {anomaly_id} thành công!")
    else:
        print(f"❌ Không thể đánh dấu anomaly ID {anomaly_id}!")
    
    return result


def main():
    """Hàm chính chạy tất cả các test"""
    print("🔍 Bắt đầu kiểm tra gửi cảnh báo từ database...")
    
    # Kết nối database
    db = Database()
    
    # Kiểm tra anomalies hiện có
    check_anomalies(db)
    
    # Test đánh dấu anomaly đã thông báo
    test_mark_as_notified(db)
    
    # Test gửi tất cả anomalies chưa thông báo
    test_send_all_anomalies(db)
    
    # Kiểm tra lại sau khi hoàn tất
    check_anomalies(db)
    
    print("\n✅ Hoàn thành kiểm tra gửi cảnh báo từ database!")
    db.close()
    return True


if __name__ == "__main__":
    main()