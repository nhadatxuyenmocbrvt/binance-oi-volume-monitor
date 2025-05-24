#!/usr/bin/env python3
"""
Script kiểm tra tính năng tracking 24h
"""

import sys
import os
import json
from pathlib import Path

# Thêm thư mục gốc vào Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from data_storage.database import Database
    from visualization.report_generator import ReportGenerator
    from config.settings import SYMBOLS, setup_logging
    
    logger = setup_logging(__name__, 'test_tracking_24h.log')
    
    def test_tracking_24h():
        """Test chức năng tracking 24h"""
        print("🧪 Bắt đầu test tracking 24h...")
        
        try:
            # 1. Kiểm tra khởi tạo database
            print("📊 Khởi tạo database...")
            db = Database()
            
            # 2. Kiểm tra khởi tạo report generator
            print("📈 Khởi tạo report generator...")
            report_gen = ReportGenerator(db)
            
            # 3. Kiểm tra method generate_24h_data tồn tại
            print("🔍 Kiểm tra method generate_24h_data...")
            if hasattr(report_gen, 'generate_24h_data'):
                print("✅ Method generate_24h_data tồn tại")
            else:
                print("❌ Method generate_24h_data KHÔNG tồn tại")
                return False
            
            # 4. Thử tạo dữ liệu tracking 24h
            print("⚡ Thử tạo dữ liệu tracking 24h...")
            tracking_data = report_gen.generate_24h_data()
            
            if tracking_data:
                print("✅ Tạo dữ liệu tracking 24h thành công!")
                print(f"📋 Có {len(tracking_data.get('symbols', {}))} symbols")
                
                # 5. Kiểm tra file được tạo
                tracking_file = 'docs/assets/data/tracking_24h.json'
                if os.path.exists(tracking_file):
                    print(f"✅ File {tracking_file} đã được tạo")
                    
                    # Kiểm tra nội dung file
                    with open(tracking_file, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    
                    print(f"📊 File chứa {len(file_data.get('symbols', {}))} symbols")
                    print(f"🕒 Timestamp: {file_data.get('timestamp', 'N/A')}")
                    
                    # Hiển thị sample data
                    for symbol in list(file_data.get('symbols', {}).keys())[:2]:
                        symbol_data = file_data['symbols'][symbol]
                        print(f"📈 {symbol}:")
                        print(f"   - Price 24h: {symbol_data.get('price_24h_change', 0):.2f}%")
                        print(f"   - Volatility: {symbol_data.get('price_volatility', 0):.2f}%")
                        print(f"   - Hours data: {len(symbol_data.get('hours_data', []))} points")
                    
                else:
                    print(f"❌ File {tracking_file} CHƯA được tạo")
                    return False
                    
            else:
                print("❌ Không thể tạo dữ liệu tracking 24h")
                return False
            
            # 6. Test tạo daily summary
            print("📊 Test tạo daily summary...")
            summary = report_gen.generate_daily_summary()
            
            if summary:
                print("✅ Tạo daily summary thành công!")
                
                # Kiểm tra daily summary file
                daily_file = 'docs/assets/data/daily_summary.json'
                if os.path.exists(daily_file):
                    print(f"✅ File {daily_file} đã được tạo")
                else:
                    print(f"❌ File {daily_file} CHƯA được tạo")
            else:
                print("❌ Không thể tạo daily summary")
            
            print("\n🎉 TEST HOÀN THÀNH!")
            return True
            
        except Exception as e:
            print(f"❌ LỖI TRONG QUÁ TRÌNH TEST: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # Đóng database
            if 'db' in locals():
                db.close()
    
    def check_files_status():
        """Kiểm tra trạng thái các file cần thiết"""
        print("\n📁 KIỂM TRA TRẠNG THÁI FILES:")
        
        required_files = [
            'docs/assets/data/daily_summary.json',
            'docs/assets/data/tracking_24h.json',
            'docs/assets/data/symbols.json',
            'docs/assets/data/anomalies.json'
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✅ {file_path} ({file_size} bytes)")
            else:
                print(f"❌ {file_path} (THIẾU)")
        
        # Kiểm tra files symbols
        for symbol in SYMBOLS:
            symbol_file = f'docs/assets/data/{symbol}.json'
            if os.path.exists(symbol_file):
                file_size = os.path.getsize(symbol_file)
                print(f"✅ {symbol_file} ({file_size} bytes)")
            else:
                print(f"❌ {symbol_file} (THIẾU)")
    
    def main():
        """Main function"""
        print("=" * 60)
        print("🧪 BINANCE OI MONITOR - TEST TRACKING 24H")
        print("=" * 60)
        
        # Test tracking 24h
        success = test_tracking_24h()
        
        # Kiểm tra files
        check_files_status()
        
        print("\n" + "=" * 60)
        if success:
            print("🎉 TẤT CẢ TESTS ĐỀU PASS!")
            print("🚀 Bây giờ bạn có thể mở trang web:")
            print("   https://nhadatxuyenmocbrvt.github.io/binance-oi-volume-monitor/")
        else:
            print("❌ CÓ LỖI TRONG QUÁ TRÌNH TEST!")
            print("🔧 Vui lòng kiểm tra lại code và log files")
        print("=" * 60)
        
        return success

    if __name__ == "__main__":
        main()
        
except ImportError as e:
    print(f"❌ LỖI IMPORT: {str(e)}")
    print("🔧 Hãy đảm bảo bạn đang chạy script từ thư mục gốc của project")
    print("🔧 Và đã cài đặt tất cả dependencies: pip install -r requirements.txt")