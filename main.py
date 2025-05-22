import os
import time
import argparse
import schedule
import subprocess
from datetime import datetime, timedelta
from config.settings import setup_logging, SYMBOLS, UPDATE_INTERVAL
from data_collector.historical_data import HistoricalDataCollector
from data_storage.database import Database
from data_analyzer.anomaly_detector import AnomalyDetector
from alerting.telegram_bot import TelegramBot
from visualization.chart_generator import ChartGenerator
from visualization.report_generator import ReportGenerator
from utils.helpers import wait_for_next_minute

logger = setup_logging(__name__, 'main.log')

def collect_historical_data():
    """Thu thập dữ liệu lịch sử - chạy 24h/lần"""
    logger.info("🔄 Bắt đầu thu thập dữ liệu lịch sử (24h/lần)")
    collector = HistoricalDataCollector()
    db = Database()
    
    try:
        # Thu thập dữ liệu
        data = collector.collect_all_historical_data()
        
        # Lưu dữ liệu vào cơ sở dữ liệu
        if data and 'klines' in data and 'open_interest' in data:
            # Lưu dữ liệu klines
            for symbol in data['klines']:
                for timeframe in data['klines'][symbol]:
                    df = data['klines'][symbol][timeframe]
                    db.save_klines(symbol, timeframe, df)
            
            # Lưu dữ liệu Open Interest
            for symbol in data['open_interest']:
                df = data['open_interest'][symbol]
                db.save_open_interest(symbol, df)
        
        # Xuất dữ liệu cho GitHub Pages
        db.export_to_json()
        
        logger.info("✅ Hoàn thành thu thập dữ liệu lịch sử")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi thu thập dữ liệu lịch sử: {str(e)}")
        return False
    finally:
        db.close()

def update_realtime_and_generate_reports():
    """Cập nhật dữ liệu realtime, tạo báo cáo và đẩy lên GitHub - chạy 1h/lần"""
    logger.info("⚡ Bắt đầu chu kỳ realtime (1h/lần): Update → Reports → Push")
    
    try:
        # Bước 1: Cập nhật dữ liệu realtime
        collector = HistoricalDataCollector()
        db = Database()
        
        logger.info("📡 Thu thập dữ liệu realtime...")
        realtime_data = collector.collect_realtime_data()
        
        # Lưu dữ liệu realtime vào database
        if realtime_data and 'ticker' in realtime_data and 'open_interest' in realtime_data:
            saved_count = 0
            for symbol in realtime_data['ticker']:
                if db.save_ticker(symbol, realtime_data['ticker'][symbol]):
                    saved_count += 1
            
            for symbol in realtime_data['open_interest']:
                db.save_realtime_open_interest(symbol, realtime_data['open_interest'][symbol])
            
            logger.info(f"💾 Đã lưu dữ liệu realtime cho {saved_count} symbols")
        
        # Bước 2: Tạo báo cáo
        logger.info("📊 Tạo báo cáo và biểu đồ...")
        report_gen = ReportGenerator(db)
        
        # Tạo báo cáo tổng hợp
        summary = report_gen.generate_daily_summary()
        if summary:
            logger.info("✅ Đã tạo báo cáo tổng hợp")
        
        # Tạo biểu đồ cho từng symbol (tùy chọn - có thể comment nếu không cần)
        try:
            chart_gen = ChartGenerator()
            for symbol in SYMBOLS:
                charts = chart_gen.generate_all_charts(db, symbol, '1d')
            logger.info("📈 Đã tạo biểu đồ cho tất cả symbols")
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi tạo biểu đồ: {str(e)} (tiếp tục xử lý)")
        
        # Xuất dữ liệu cho GitHub Pages
        db.export_to_json()
        logger.info("📁 Đã xuất dữ liệu JSON cho GitHub Pages")
        
        # Bước 3: Push lên GitHub
        logger.info("📤 Đẩy dữ liệu lên GitHub...")
        push_success = push_to_github()
        
        if push_success:
            logger.info("🎉 Hoàn thành chu kỳ realtime: cập nhật → báo cáo → push GitHub")
        else:
            logger.info("ℹ️ Hoàn thành chu kỳ realtime: không có thay đổi để push")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi trong chu kỳ realtime: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def detect_anomalies():
    """Phát hiện bất thường và gửi cảnh báo - chạy 15 phút/lần"""
    logger.info("🔍 Bắt đầu phát hiện bất thường (15 phút/lần)")
    db = Database()
    
    try:
        detector = AnomalyDetector(db)
        bot = TelegramBot()
        
        total_anomalies = 0
        # Phát hiện bất thường cho từng symbol
        for symbol in SYMBOLS:
            anomalies = detector.detect_all_anomalies(symbol)
            total_anomalies += len(anomalies)
        
        # Gửi các cảnh báo chưa được thông báo
        bot.send_anomalies(db)
        
        logger.info(f"✅ Hoàn thành phát hiện bất thường: {total_anomalies} anomalies tổng cộng")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi phát hiện bất thường: {str(e)}")
        return False
    finally:
        db.close()

def generate_reports():
    """Tạo báo cáo và biểu đồ (không push)"""
    logger.info("📊 Bắt đầu tạo báo cáo và biểu đồ")
    db = Database()
    
    try:
        report_gen = ReportGenerator(db)
        chart_gen = ChartGenerator()
        
        # Tạo báo cáo tổng hợp
        summary = report_gen.generate_daily_summary()
        
        # Tạo biểu đồ cho từng symbol
        for symbol in SYMBOLS:
            charts = chart_gen.generate_all_charts(db, symbol, '1d')
        
        logger.info("✅ Hoàn thành tạo báo cáo và biểu đồ")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo báo cáo: {str(e)}")
        return False
    finally:
        db.close()

def push_to_github():
    """Đẩy dữ liệu lên GitHub"""
    try:
        logger.info("📤 Bắt đầu đẩy dữ liệu lên GitHub")
        
        # Thêm thay đổi
        add_data_cmd = ["git", "add", "data/"]
        add_docs_cmd = ["git", "add", "docs/"]
        
        # Thực thi lệnh git add
        subprocess.run(add_data_cmd, check=True)
        subprocess.run(add_docs_cmd, check=True)
        
        # Kiểm tra xem có thay đổi để commit không
        status_cmd = ["git", "diff", "--staged", "--quiet"]
        status_result = subprocess.run(status_cmd)
        
        # Nếu có thay đổi (exit code khác 0)
        if status_result.returncode != 0:
            # Tạo commit message với timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_cmd = ["git", "commit", "-m", f"Auto update data and reports: {timestamp}"]
            
            # Thực thi lệnh git commit
            subprocess.run(commit_cmd, check=True)
            
            # Đẩy lên GitHub
            push_cmd = ["git", "push"]
            subprocess.run(push_cmd, check=True)
            
            logger.info(f"✅ Đã đẩy dữ liệu lên GitHub thành công lúc {timestamp}")
            return True
        else:
            logger.info("ℹ️ Không có thay đổi để commit")
            return False
    
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Lỗi khi đẩy dữ liệu lên GitHub: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Lỗi không xác định khi đẩy dữ liệu lên GitHub: {str(e)}")
        return False

def send_daily_report():
    """Gửi báo cáo hàng ngày qua Telegram - chạy 1 lần/ngày lúc 20:00"""
    logger.info("📱 Bắt đầu gửi báo cáo hàng ngày qua Telegram")
    db = Database()
    
    try:
        bot = TelegramBot()
        report_gen = ReportGenerator(db)
        
        # Tạo báo cáo tổng hợp
        summary = report_gen.generate_daily_summary()
        
        # Gửi báo cáo cho từng symbol
        for symbol in SYMBOLS:
            # Lấy dữ liệu
            oi_df = db.get_open_interest(symbol)
            price_df = db.get_klines(symbol, '1d')
            
            # Tính các thay đổi
            if not oi_df.empty and len(oi_df) > 1:
                oi_change = oi_df['open_interest'].pct_change().iloc[-1] * 100
            else:
                oi_change = 0
                
            if not price_df.empty and len(price_df) > 1:
                volume_change = price_df['volume'].pct_change().iloc[-1] * 100
            else:
                volume_change = 0
            
            # Lấy sentiment
            sentiment = None
            if summary and 'symbols' in summary and symbol in summary['symbols']:
                sentiment = {
                    'sentiment_label': summary['symbols'][symbol]['sentiment'],
                    'price_change': summary['symbols'][symbol]['price_change']
                }
            
            # Lấy đường dẫn chart
            chart_path = f'data/charts/{symbol}_1d_price_oi.png'
            if not os.path.exists(chart_path):
                chart_path = None
            
            # Gửi báo cáo
            bot.send_daily_report(symbol, sentiment, oi_change, volume_change, chart_path)
            
            # Đợi 1 giây để tránh gửi quá nhiều tin nhắn cùng lúc
            time.sleep(1)
        
        logger.info("✅ Hoàn thành gửi báo cáo hàng ngày")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi gửi báo cáo hàng ngày: {str(e)}")
        return False
    finally:
        db.close()

def schedule_tasks():
    """Lập lịch các tác vụ định kỳ - PHIÊN BẢN TỐI ƯU"""
    logger.info("⏰ Thiết lập lịch trình các tác vụ tối ưu")
    
    # 📊 THU THẬP DỮ LIỆU LỊCH SỬ: 24H/LẦN (mỗi ngày lúc 00:05)
    schedule.every().day.at("00:05").do(collect_historical_data)
    logger.info("✅ Lịch thu thập dữ liệu lịch sử: mỗi ngày lúc 00:05")
    
    # ⚡ CẬP NHẬT REALTIME + TẠO BÁO CÁO + PUSH: 1H/LẦN 
    schedule.every(60).minutes.do(update_realtime_and_generate_reports)
    logger.info("✅ Lịch cập nhật realtime + báo cáo + push: mỗi 60 phút")
    
    # 🔍 PHÁT HIỆN BẤT THƯỜNG: 15 PHÚT/LẦN
    schedule.every(15).minutes.do(detect_anomalies)
    logger.info("✅ Lịch phát hiện bất thường: mỗi 15 phút")
    
    # 📱 GỬI BÁO CÁO TELEGRAM: MỖI NGÀY LÚC 20:00
    schedule.every().day.at("20:00").do(send_daily_report)
    logger.info("✅ Lịch gửi báo cáo Telegram: mỗi ngày lúc 20:00")
    
    logger.info("🎯 Đã thiết lập lịch trình tối ưu:")
    logger.info("   📊 Dữ liệu lịch sử: 24h/lần")
    logger.info("   ⚡ Realtime + Reports: 1h/lần") 
    logger.info("   🔍 Anomaly detection: 15 phút/lần")
    logger.info("   📱 Daily Telegram: 1 lần/ngày")

def run_scheduled_tasks():
    """Chạy các tác vụ đã lên lịch"""
    logger.info("🚀 Bắt đầu chạy các tác vụ theo lịch trình tối ưu")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("⏹️ Dừng hệ thống theo yêu cầu người dùng")
            break
        except Exception as e:
            logger.error(f"❌ Lỗi khi chạy tác vụ theo lịch: {str(e)}")
            time.sleep(10)  # Đợi 10 giây trước khi thử lại

def initialize():
    """Khởi tạo hệ thống"""
    logger.info("🔧 Bắt đầu khởi tạo hệ thống")
    
    # Đảm bảo các thư mục cần thiết tồn tại
    directories = [
        'data',
        'data/charts', 
        'data/reports',
        'data/json',
        'logs',
        'docs/assets/data'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"📁 Đã tạo/kiểm tra thư mục: {directory}")
    
    # Khởi tạo cơ sở dữ liệu
    try:
        db = Database()
        db.close()
        logger.info("💾 Đã khởi tạo cơ sở dữ liệu thành công")
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")
        raise
    
    logger.info("✅ Hoàn thành khởi tạo hệ thống")

def main():
    """Hàm chính của ứng dụng - PHIÊN BẢN TỐI ƯU HOÀN CHỈNH"""
    parser = argparse.ArgumentParser(
        description='Hệ thống theo dõi Open Interest và Volume từ Binance - Phiên bản tối ưu',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python main.py --schedule          # Chạy theo lịch trình tối ưu (khuyến nghị)
  python main.py --collect           # Thu thập dữ liệu lịch sử (24h/lần)
  python main.py --realtime          # Cập nhật realtime + báo cáo + push (1h/lần)
  python main.py --detect            # Phát hiện bất thường
  python main.py --daily             # Gửi báo cáo Telegram
        """
    )
    
    parser.add_argument('--collect', action='store_true', 
                       help='Thu thập dữ liệu lịch sử (24h/lần)')
    parser.add_argument('--realtime', action='store_true', 
                       help='Cập nhật realtime + tạo báo cáo + push GitHub (1h/lần)')
    parser.add_argument('--detect', action='store_true', 
                       help='Phát hiện bất thường (15 phút/lần)')
    parser.add_argument('--report', action='store_true', 
                       help='Chỉ tạo báo cáo (không push GitHub)')
    parser.add_argument('--push', action='store_true', 
                       help='Chỉ đẩy dữ liệu lên GitHub')
    parser.add_argument('--daily', action='store_true', 
                       help='Gửi báo cáo hàng ngày qua Telegram')
    parser.add_argument('--schedule', action='store_true', 
                       help='Chạy tất cả tác vụ theo lịch trình tối ưu (khuyến nghị)')
    
    args = parser.parse_args()
    
    # Hiển thị thông tin khởi động
    logger.info("="*60)
    logger.info("🚀 BINANCE OI & VOLUME MONITOR - PHIÊN BẢN TỐI ƯU")
    logger.info("="*60)
    logger.info(f"⏰ Khởi động lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📊 Theo dõi {len(SYMBOLS)} symbols: {', '.join(SYMBOLS)}")
    
    # Khởi tạo hệ thống
    try:
        initialize()
    except Exception as e:
        logger.error(f"❌ Không thể khởi tạo hệ thống: {str(e)}")
        return 1
    
    # Thực hiện các tác vụ dựa trên tham số
    try:
        if args.collect:
            logger.info("🔄 CHẾ ĐỘ: Thu thập dữ liệu lịch sử")
            success = collect_historical_data()
            return 0 if success else 1
            
        elif args.realtime:
            logger.info("⚡ CHẾ ĐỘ: Cập nhật realtime + báo cáo + push")
            success = update_realtime_and_generate_reports()
            return 0 if success else 1
            
        elif args.detect:
            logger.info("🔍 CHẾ ĐỘ: Phát hiện bất thường")
            success = detect_anomalies()
            return 0 if success else 1
            
        elif args.report:
            logger.info("📊 CHẾ ĐỘ: Chỉ tạo báo cáo")
            success = generate_reports()
            return 0 if success else 1
            
        elif args.push:
            logger.info("📤 CHẾ ĐỘ: Chỉ push lên GitHub")
            success = push_to_github()
            return 0 if success else 1
            
        elif args.daily:
            logger.info("📱 CHẾ ĐỘ: Gửi báo cáo Telegram")
            success = send_daily_report()
            return 0 if success else 1
            
        elif args.schedule:
            logger.info("⏰ CHẾ ĐỘ: Chạy theo lịch trình tối ưu")
            schedule_tasks()
            run_scheduled_tasks()
            return 0
            
        else:
            # Chế độ mặc định: thu thập dữ liệu lịch sử và chạy theo lịch
            logger.info("🎯 CHẾ ĐỘ MẶC ĐỊNH: Thu thập lịch sử + chạy lịch trình")
            logger.info("💡 Gợi ý: Sử dụng --schedule để chạy chế độ tối ưu")
            
            # Thu thập dữ liệu lịch sử trước
            if collect_historical_data():
                # Sau đó chạy theo lịch
                schedule_tasks()
                run_scheduled_tasks()
            else:
                logger.error("❌ Không thể thu thập dữ liệu lịch sử ban đầu")
                return 1
            return 0
            
    except KeyboardInterrupt:
        logger.info("⏹️ Dừng hệ thống theo yêu cầu người dùng")
        return 0
    except Exception as e:
        logger.error(f"❌ Lỗi không xác định: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    logger.info(f"🏁 Kết thúc với mã: {exit_code}")
    exit(exit_code)