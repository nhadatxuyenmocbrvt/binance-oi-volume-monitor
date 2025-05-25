import os
import time
import argparse
import schedule
import subprocess
import random
from datetime import datetime, timedelta
from config.settings import setup_logging, SYMBOLS, UPDATE_INTERVAL
from data_collector.historical_data import HistoricalDataCollector
from data_storage.database import Database
from data_analyzer.anomaly_detector import OptimizedAnomalyDetector
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
        
        # Xuất dữ liệu JSON tối ưu cho web
        db.export_to_json()
        
        logger.info("✅ Hoàn thành thu thập dữ liệu lịch sử")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi thu thập dữ liệu lịch sử: {str(e)}")
        return False
    finally:
        db.close()

def update_hourly_data():
    """Cập nhật dữ liệu mỗi giờ - TRACKING 24H"""
    logger.info("⏰ Bắt đầu cập nhật dữ liệu hàng giờ - Tracking 24h")
    
    try:
        collector = HistoricalDataCollector()
        db = Database()
        
        logger.info("📡 Thu thập dữ liệu realtime cho tracking 24h...")
        realtime_data = collector.collect_realtime_data()
        
        # Lưu dữ liệu realtime với timestamp giờ tròn
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        if realtime_data and 'ticker' in realtime_data and 'open_interest' in realtime_data:
            saved_count = 0
            for symbol in SYMBOLS:
                if symbol in realtime_data['ticker']:
                    # Cập nhật timestamp thành giờ tròn
                    realtime_data['ticker'][symbol]['timestamp'] = current_hour
                    if db.save_ticker(symbol, realtime_data['ticker'][symbol]):
                        saved_count += 1
                
                if symbol in realtime_data['open_interest']:
                    # Cập nhật timestamp thành giờ tròn
                    realtime_data['open_interest'][symbol]['timestamp'] = current_hour
                    db.save_realtime_open_interest(symbol, realtime_data['open_interest'][symbol])
            
            logger.info(f"💾 Đã lưu dữ liệu hàng giờ cho {saved_count}/{len(SYMBOLS)} symbols lúc {current_hour.strftime('%H:00')}")
        
        # Lưu dữ liệu tracking 24h
        success = db.save_hourly_tracking(current_hour)
        if success:
            logger.info(f"📊 Đã cập nhật tracking 24h cho {current_hour.strftime('%H:00')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi cập nhật dữ liệu hàng giờ: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()

def update_realtime_and_generate_reports():
    """Cập nhật dữ liệu realtime, tạo báo cáo và đẩy lên GitHub - chạy 30 phút/lần"""
    logger.info("⚡ Bắt đầu chu kỳ realtime (30 phút/lần): Update → Reports → Push")
    
    try:
        # Bước 1: Cập nhật dữ liệu realtime
        collector = HistoricalDataCollector()
        db = Database()
        
        logger.info("📡 Thu thập dữ liệu realtime...")
        realtime_data = collector.collect_realtime_data()
        
        # Lưu dữ liệu realtime vào database
        if realtime_data and 'ticker' in realtime_data and 'open_interest' in realtime_data:
            saved_count = 0
            for symbol in SYMBOLS:
                if symbol in realtime_data['ticker']:
                    if db.save_ticker(symbol, realtime_data['ticker'][symbol]):
                        saved_count += 1
                
                if symbol in realtime_data['open_interest']:
                    db.save_realtime_open_interest(symbol, realtime_data['open_interest'][symbol])
            
            logger.info(f"💾 Đã lưu dữ liệu realtime cho {saved_count}/{len(SYMBOLS)} symbols")
        
        # Bước 2: Tạo báo cáo tối ưu
        logger.info("📊 Tạo báo cáo tối ưu OI & Volume...")
        try:
            report_gen = ReportGenerator(db)
            
            # Tạo báo cáo tổng hợp
            summary = report_gen.generate_daily_summary()
            if summary:
                logger.info("✅ Đã tạo báo cáo tổng hợp")
            
            # Tạo dữ liệu tracking 24h cho web
            hourly_data = report_gen.generate_24h_data()
            if hourly_data:
                logger.info("📈 Đã tạo dữ liệu tracking 24h")
        
        except Exception as e:
            logger.warning(f"⚠️ Lỗi khi tạo báo cáo: {str(e)} (tiếp tục xử lý)")
        
        # Bước 3: Xuất dữ liệu JSON tối ưu cho web
        logger.info("📁 Xuất dữ liệu JSON tối ưu...")
        export_success = db.export_to_json()
        if export_success:
            logger.info("✅ Đã xuất dữ liệu JSON cho web")
        
        # Bước 4: Push lên GitHub
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
    """Phát hiện bất thường tối ưu OI & Volume - chạy 15 phút/lần"""
    logger.info("🔍 Bắt đầu phát hiện bất thường tối ưu (15 phút/lần)")
    db = Database()
    
    try:
        detector = OptimizedAnomalyDetector(db)
        
        total_anomalies = 0
        anomaly_summary = {}
        
        # Phát hiện bất thường cho từng symbol
        for symbol in SYMBOLS:
            try:
                logger.info(f"🔍 Phân tích {symbol}...")
                anomalies = detector.detect_all_anomalies(symbol)
                total_anomalies += len(anomalies)
                
                if anomalies:
                    anomaly_summary[symbol] = len(anomalies)
                    # Log chi tiết
                    for anomaly in anomalies[-3:]:  # Log 3 anomalies gần nhất
                        logger.info(f"   🚨 {anomaly['data_type']}: {anomaly['severity']} (Z: {anomaly['z_score']:.2f})")
                else:
                    logger.info(f"   ✅ {symbol}: Không phát hiện anomaly")
                    
            except Exception as e:
                logger.error(f"❌ Lỗi khi phát hiện anomalies cho {symbol}: {str(e)}")
        
        # Gửi cảnh báo qua Telegram
        try:
            if total_anomalies > 0:
                bot = TelegramBot()
                bot.send_anomalies(db)
                logger.info("📱 Đã gửi cảnh báo qua Telegram")
        except Exception as e:
            logger.error(f"❌ Lỗi khi gửi cảnh báo Telegram: {str(e)}")
        
        # Log summary
        if anomaly_summary:
            logger.info(f"✅ Hoàn thành phát hiện bất thường: {total_anomalies} anomalies")
            for symbol, count in anomaly_summary.items():
                logger.info(f"   - {symbol}: {count} anomalies")
        else:
            logger.info("✅ Hoàn thành phát hiện bất thường: Không có anomaly nào")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi phát hiện bất thường: {str(e)}")
        return False
    finally:
        db.close()

def generate_optimized_reports():
    """Tạo báo cáo tối ưu cho OI & Volume (không push)"""
    logger.info("📊 Bắt đầu tạo báo cáo tối ưu OI & Volume")
    db = Database()
    
    try:
        report_gen = ReportGenerator(db)
        
        # Tạo báo cáo tổng hợp
        summary = report_gen.generate_daily_summary()
        if summary:
            logger.info("✅ Tạo báo cáo tổng hợp thành công")
        
        # Tạo dữ liệu tracking 24h
        hourly_data = report_gen.generate_24h_data()
        if hourly_data:
            logger.info("✅ Tạo dữ liệu tracking 24h thành công")
        
        # Xuất JSON tối ưu
        export_success = db.export_to_json()
        if export_success:
            logger.info("✅ Xuất dữ liệu JSON thành công")
        
        logger.info("✅ Hoàn thành tạo báo cáo tối ưu")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo báo cáo tối ưu: {str(e)}")
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
            commit_cmd = ["git", "commit", "-m", f"🔄 Auto update OI & Volume data: {timestamp}"]
            
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
        
        # Gửi báo cáo tối ưu cho từng symbol
        for symbol in SYMBOLS:
            try:
                # Lấy dữ liệu OI và Volume
                oi_df = db.get_open_interest(symbol, limit=24)  # 24 điểm gần nhất
                tracking_df = db.get_24h_tracking_data(symbol)
                
                # Tính các thay đổi từ tracking data
                oi_change = 0
                volume_change = 0
                
                if not tracking_df.empty and len(tracking_df) > 1:
                    latest = tracking_df.iloc[-1]
                    previous = tracking_df.iloc[-2]
                    
                    if previous['open_interest'] > 0:
                        oi_change = ((latest['open_interest'] - previous['open_interest']) / previous['open_interest']) * 100
                    
                    if previous['volume'] > 0:
                        volume_change = ((latest['volume'] - previous['volume']) / previous['volume']) * 100
                
                # Lấy sentiment từ summary
                sentiment = None
                if summary and 'symbols' in summary and symbol in summary['symbols']:
                    sentiment = {
                        'sentiment_label': summary['symbols'][symbol].get('sentiment', 'neutral'),
                        'price_change': summary['symbols'][symbol].get('price_change', 0)
                    }
                
                # Lấy đường dẫn chart (nếu có)
                chart_path = f'data/charts/{symbol}_1d_price_oi.png'
                if not os.path.exists(chart_path):
                    chart_path = None
                
                # Gửi báo cáo với format mới
                message = f"📊 **{symbol} Daily Report**\n"
                message += f"🔸 OI Change: {oi_change:+.2f}%\n"
                message += f"🔹 Volume Change: {volume_change:+.2f}%\n"
                
                if sentiment:
                    message += f"📈 Sentiment: {sentiment['sentiment_label']}\n"
                    message += f"💰 Price Change: {sentiment['price_change']:+.2f}%\n"
                
                bot.send_message(message)
                
                # Đợi 1 giây để tránh spam
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Lỗi khi gửi báo cáo cho {symbol}: {str(e)}")
                continue
        
        logger.info("✅ Hoàn thành gửi báo cáo hàng ngày")
        return True
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi gửi báo cáo hàng ngày: {str(e)}")
        return False
    finally:
        db.close()

def schedule_optimized_tasks():
    """Lập lịch các tác vụ tối ưu cho tracking OI & Volume"""
    logger.info("⏰ Thiết lập lịch trình tối ưu OI & Volume Tracking")
    
    # 📊 THU THẬP DỮ LIỆU LỊCH SỬ: 24H/LẦN (mỗi ngày lúc 00:05)
    schedule.every().day.at("00:05").do(collect_historical_data)
    logger.info("✅ Lịch thu thập dữ liệu lịch sử: mỗi ngày lúc 00:05")
    
    # ⏰ CẬP NHẬT TRACKING 24H: MỖI GIỜ ĐÚNG (0 phút)
    schedule.every().hour.at(":00").do(update_hourly_data)
    logger.info("✅ Lịch tracking 24h: mỗi giờ đúng giờ")
    
    # ⚡ CẬP NHẬT REALTIME + TẠO BÁO CÁO + PUSH: 30 PHÚT/LẦN
    schedule.every(30).minutes.do(update_realtime_and_generate_reports)
    logger.info("✅ Lịch realtime + báo cáo + push: mỗi 30 phút")
    
    # 🔍 PHÁT HIỆN BẤT THƯỜNG TỐI ƯU: 15 PHÚT/LẦN
    schedule.every(15).minutes.do(detect_anomalies)
    logger.info("✅ Lịch phát hiện bất thường tối ưu: mỗi 15 phút")
    
    # 📱 GỬI BÁO CÁO TELEGRAM: MỖI NGÀY LÚC 20:00
    schedule.every().day.at("20:00").do(send_daily_report)
    logger.info("✅ Lịch gửi báo cáo Telegram: mỗi ngày lúc 20:00")
    
    logger.info("🎯 Đã thiết lập lịch trình tối ưu:")
    logger.info("   📊 Dữ liệu lịch sử: 24h/lần")
    logger.info("   ⏰ Tracking 24h: mỗi giờ đúng")
    logger.info("   ⚡ Realtime + Reports: 30 phút/lần") 
    logger.info("   🔍 Anomaly detection: 15 phút/lần")
    logger.info("   📱 Daily Telegram: 1 lần/ngày")

def run_scheduled_tasks():
    """Chạy các tác vụ đã lên lịch"""
    logger.info("🚀 Bắt đầu chạy các tác vụ theo lịch trình OI & Volume Tracking")
    
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

def initialize_system():
    """Khởi tạo hệ thống tối ưu"""
    logger.info("🔧 Bắt đầu khởi tạo hệ thống OI & Volume Monitor")
    
    # Tạo các thư mục cần thiết
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
        
        # Khởi tạo dữ liệu tracking 24h từ dữ liệu lịch sử
        logger.info("🔄 Đang khởi tạo dữ liệu tracking 24h từ Binance API...")
        db.initialize_24h_tracking_data()
        
        # Khởi tạo dữ liệu 30 ngày
        logger.info("🔄 Đang khởi tạo dữ liệu 30 ngày từ Binance API...")
        db.initialize_30d_data()
        
        # Xuất dữ liệu JSON
        logger.info("📄 Xuất dữ liệu JSON cho web...")
        db.export_to_json()
        
        db.close()
        logger.info("💾 Đã khởi tạo cơ sở dữ liệu thành công")
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo cơ sở dữ liệu: {str(e)}")
        raise
    
    logger.info("✅ Hoàn thành khởi tạo hệ thống")

def main():
    """Hàm chính của ứng dụng - TƯƠNG THÍCH VỚI GIAO DIỆN MỚI"""
    parser = argparse.ArgumentParser(
        description='Hệ thống theo dõi OI & Volume tối ưu từ Binance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python main.py --schedule          # Chạy theo lịch trình tối ưu (khuyến nghị)
  python main.py --collect           # Thu thập dữ liệu lịch sử
  python main.py --realtime          # Cập nhật realtime + báo cáo + push
  python main.py --hourly            # Cập nhật tracking 24h
  python main.py --detect            # Phát hiện bất thường tối ưu
        """
    )
    
    parser.add_argument('--collect', action='store_true', 
                       help='Thu thập dữ liệu lịch sử (24h/lần)')
    parser.add_argument('--realtime', action='store_true', 
                       help='Cập nhật realtime + tạo báo cáo + push GitHub (30 phút/lần)')
    parser.add_argument('--hourly', action='store_true', 
                       help='Cập nhật tracking 24h (1h/lần)')
    parser.add_argument('--detect', action='store_true', 
                       help='Phát hiện bất thường tối ưu (15 phút/lần)')
    parser.add_argument('--report', action='store_true', 
                       help='Chỉ tạo báo cáo tối ưu (không push GitHub)')
    parser.add_argument('--push', action='store_true', 
                       help='Chỉ đẩy dữ liệu lên GitHub')
    parser.add_argument('--daily', action='store_true', 
                       help='Gửi báo cáo hàng ngày qua Telegram')
    parser.add_argument('--schedule', action='store_true', 
                       help='Chạy tất cả tác vụ theo lịch trình tối ưu (khuyến nghị)')
    
    args = parser.parse_args()
    
    # Hiển thị thông tin khởi động
    logger.info("="*60)
    logger.info("🚀 BINANCE OI & VOLUME MONITOR - OPTIMIZED VERSION")
    logger.info("="*60)
    logger.info(f"⏰ Khởi động lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"📊 Theo dõi {len(SYMBOLS)} symbols: {', '.join(SYMBOLS)}")
    logger.info(f"🎯 Focus: OI & Volume tracking (24h + 30d)")
    
    # Khởi tạo hệ thống
    try:
        initialize_system()
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
            
        elif args.hourly:
            logger.info("⏰ CHẾ ĐỘ: Cập nhật tracking 24h")
            success = update_hourly_data()
            return 0 if success else 1
            
        elif args.detect:
            logger.info("🔍 CHẾ ĐỘ: Phát hiện bất thường tối ưu")
            success = detect_anomalies()
            return 0 if success else 1
            
        elif args.report:
            logger.info("📊 CHẾ ĐỘ: Chỉ tạo báo cáo tối ưu")
            success = generate_optimized_reports()
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
            schedule_optimized_tasks()
            run_scheduled_tasks()
            return 0
            
        else:
            # Chế độ mặc định: setup đầy đủ tối ưu
            logger.info("🎯 CHẾ ĐỘ MẶC ĐỊNH: Setup OI & Volume tracking tối ưu")
            logger.info("📋 Quy trình: Thu thập lịch sử → Realtime + Báo cáo + Push → Tracking tối ưu")
            
            # Bước 1: Thu thập dữ liệu lịch sử
            logger.info("🔄 Bước 1/3: Thu thập dữ liệu lịch sử...")
            if not collect_historical_data():
                logger.error("❌ Không thể thu thập dữ liệu lịch sử")
                return 1
            
            # Bước 2: Cập nhật realtime + tạo báo cáo + push
            logger.info("⚡ Bước 2/3: Cập nhật realtime + tạo báo cáo + push...")
            if not update_realtime_and_generate_reports():
                logger.warning("⚠️ Có lỗi khi cập nhật realtime, nhưng tiếp tục...")
            
            # Bước 3: Chạy theo lịch trình tối ưu
            logger.info("⏰ Bước 3/3: Thiết lập tracking tối ưu...")
            schedule_optimized_tasks()
            
            logger.info("✅ Hoàn thành setup - OI & Volume tracking tối ưu đã được kích hoạt!")
            logger.info("🔄 Hệ thống sẽ theo dõi OI & Volume từng giờ và cập nhật web...")
            
            run_scheduled_tasks()
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