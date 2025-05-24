#!/usr/bin/env python3
"""
Quick fix cho lỗi tracking 24h
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta

# Thêm thư mục gốc vào Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

def create_sample_tracking_data():
    """Tạo dữ liệu tracking 24h mẫu để test"""
    print("📊 Tạo dữ liệu tracking 24h mẫu...")
    
    # Đảm bảo thư mục tồn tại
    os.makedirs('docs/assets/data', exist_ok=True)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    tracking_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbols': {},
        'summary': {
            'total_symbols': len(symbols),
            'most_volatile': 'BTCUSDT',
            'highest_volume_change': 'ETHUSDT',
            'highest_oi_change': 'SOLUSDT'
        }
    }
    
    # Tạo dữ liệu cho từng symbol
    for i, symbol in enumerate(symbols):
        hours_data = []
        
        # Tạo dữ liệu cho 24 giờ
        for hour in range(24):
            hour_timestamp = datetime.now() - timedelta(hours=23-hour)
            price_change = (i + 1) * (hour % 7 - 3) * 0.5  # Mô phỏng thay đổi giá
            
            hours_data.append({
                'hour_timestamp': hour_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'hour': hour,
                'price': 50000 + i * 1000 + hour * 10,  # Giá mô phỏng
                'volume': 1000000 + hour * 50000,  # Volume mô phỏng
                'price_change_1h': price_change,
                'volume_change_1h': (hour % 5 - 2) * 10,
                'oi': 500000 + hour * 20000,
                'oi_change_1h': (hour % 4 - 2) * 5
            })
        
        # Tính toán thống kê
        price_changes = [h['price_change_1h'] for h in hours_data]
        volatility = max(price_changes) - min(price_changes)
        
        max_change_hour = max(hours_data, key=lambda x: abs(x['price_change_1h']))
        
        symbol_data = {
            'hours_data': hours_data,
            'price_24h_change': sum(price_changes),
            'volume_24h_change': (i + 1) * 15 - 30,  # -15% to +60%
            'oi_24h_change': (i + 1) * 8 - 20,  # -12% to +20%
            'price_volatility': volatility,
            'max_price_change_hour': {
                'hour': max_change_hour['hour'],
                'change': max_change_hour['price_change_1h'],
                'timestamp': max_change_hour['hour_timestamp']
            },
            'current_price': hours_data[-1]['price'],
            'current_volume': hours_data[-1]['volume'],
            'current_oi': hours_data[-1]['oi']
        }
        
        tracking_data['symbols'][symbol] = symbol_data
    
    # Lưu file
    tracking_file = 'docs/assets/data/tracking_24h.json'
    with open(tracking_file, 'w', encoding='utf-8') as f:
        json.dump(tracking_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã tạo file {tracking_file}")
    return tracking_data

def create_sample_daily_summary():
    """Tạo daily summary mẫu"""
    print("📊 Tạo daily summary mẫu...")
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    summary = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'symbols': {},
        'anomalies': []
    }
    
    # Tạo dữ liệu cho từng symbol
    for i, symbol in enumerate(symbols):
        summary['symbols'][symbol] = {
            'price_change': (i + 1) * 2 - 5,  # -3% to +5%
            'oi_change': (i + 1) * 1.5 - 3,  # -1.5% to +4.5%
            'volume_change': (i + 1) * 10 - 25,  # -15% to +25%
            'sentiment': ['Bearish', 'Neutral', 'Bullish', 'Strong Bullish', 'Neutral'][i]
        }
    
    # Thêm một số anomalies mẫu
    for i in range(3):
        summary['anomalies'].append({
            'symbol': symbols[i % len(symbols)],
            'timestamp': (datetime.now() - timedelta(hours=i*2)).strftime('%Y-%m-%d %H:%M:%S'),
            'data_type': ['volume', 'open_interest', 'price'][i],
            'message': f'Bất thường {["volume", "open interest", "price"][i]} phát hiện - Z-score: {3.5 + i*0.5}'
        })
    
    # Lưu file
    daily_file = 'docs/assets/data/daily_summary.json'
    with open(daily_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã tạo file {daily_file}")
    return summary

def create_sample_symbols_file():
    """Tạo file symbols.json"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    symbols_file = 'docs/assets/data/symbols.json'
    with open(symbols_file, 'w') as f:
        json.dump(symbols, f)
    
    print(f"✅ Đã tạo file {symbols_file}")

def create_sample_anomalies_file():
    """Tạo file anomalies.json"""
    anomalies = []
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    for i in range(5):
        anomalies.append({
            'symbol': symbols[i % len(symbols)],
            'timestamp': (datetime.now() - timedelta(hours=i*2)).strftime('%Y-%m-%d %H:%M:%S'),
            'data_type': ['volume', 'open_interest', 'price'][i % 3],
            'message': f'Bất thường {["volume cao", "OI tăng đột biến", "giá biến động"][i % 3]} - Z-score: {3.0 + i*0.3}'
        })
    
    anomalies_file = 'docs/assets/data/anomalies.json'
    with open(anomalies_file, 'w', encoding='utf-8') as f:
        json.dump(anomalies, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Đã tạo file {anomalies_file}")

def create_sample_symbol_data():
    """Tạo dữ liệu cho từng symbol"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
    
    for symbol in symbols:
        symbol_data = {
            'klines': {
                '1h': [],
                '4h': [],
                '1d': []
            },
            'open_interest': []
        }
        
        # Tạo dữ liệu klines mẫu
        for timeframe in ['1h', '4h', '1d']:
            periods = {'1h': 24, '4h': 6, '1d': 7}
            period_count = periods[timeframe]
            
            for i in range(period_count):
                if timeframe == '1h':
                    time_delta = timedelta(hours=i)
                elif timeframe == '4h':
                    time_delta = timedelta(hours=i*4)
                else:
                    time_delta = timedelta(days=i)
                
                timestamp = datetime.now() - time_delta
                
                symbol_data['klines'][timeframe].append({
                    'open_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'close_time': (timestamp + time_delta).strftime('%Y-%m-%d %H:%M:%S'),
                    'open': 50000 + i * 100,
                    'high': 51000 + i * 100,
                    'low': 49000 + i * 100,
                    'close': 50500 + i * 100,
                    'volume': 1000000 + i * 10000
                })
        
        # Tạo dữ liệu open interest
        for i in range(24):
            timestamp = datetime.now() - timedelta(hours=i)
            symbol_data['open_interest'].append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'open_interest': 500000 + i * 5000,
                'open_interest_value': 25000000000 + i * 250000000
            })
        
        # Lưu file
        symbol_file = f'docs/assets/data/{symbol}.json'
        with open(symbol_file, 'w', encoding='utf-8') as f:
            json.dump(symbol_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Đã tạo file {symbol_file}")

def main():
    """Main function"""
    print("=" * 60)
    print("🔧 QUICK FIX - TẠO DỮ LIỆU MẪU CHO TRACKING 24H")
    print("=" * 60)
    
    try:
        # Đảm bảo thư mục tồn tại
        os.makedirs('docs/assets/data', exist_ok=True)
        
        # Tạo tất cả files cần thiết
        create_sample_tracking_data()
        create_sample_daily_summary()
        create_sample_symbols_file()
        create_sample_anomalies_file()
        create_sample_symbol_data()
        
        print("\n" + "=" * 60)
        print("🎉 HOÀN THÀNH TẠO DỮ LIỆU MẪU!")
        print("🚀 Bây giờ bạn có thể:")
        print("   1. Mở trang web: https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/")
        print("   2. Kiểm tra tab 'Tracking 24h' hoạt động bình thường")
        print("   3. Chạy lại main.py để cập nhật với dữ liệu thực")
        print("=" * 60)
        
        # Kiểm tra files đã tạo
        print("\n📁 FILES ĐÃ TẠO:")
        required_files = [
            'docs/assets/data/daily_summary.json',
            'docs/assets/data/tracking_24h.json',
            'docs/assets/data/symbols.json',
            'docs/assets/data/anomalies.json'
        ]
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']
        for symbol in symbols:
            required_files.append(f'docs/assets/data/{symbol}.json')
        
        for file_path in required_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ {file_path} ({file_size} bytes)")
            else:
                print(f"❌ {file_path} (THIẾU)")
        
        return True
        
    except Exception as e:
        print(f"❌ LỖI: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()