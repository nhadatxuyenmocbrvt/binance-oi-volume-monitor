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
    """Thu thập dữ liệu lịch sử"""
    logger.info("Bắt đầu thu thập dữ liệu lịch sử")
    collector = HistoricalDataCollector()
    db = Database()
    
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
    
    db.close()
    logger.info("Hoàn thành thu thập dữ liệu lịch sử")

def update_realtime_data():
    """Cập nhật dữ liệu realtime"""
    logger.info("Bắt đầu cập nhật dữ liệu realtime")
    collector = HistoricalDataCollector()
    db = Database()
    
    # Thu thập dữ liệu realtime
    data = collector.collect_realtime_data()
    
    # Lưu dữ liệu vào cơ sở dữ liệu
    if data and 'ticker' in data and 'open_interest' in data:
        # Lưu dữ liệu ticker
        for symbol in data['ticker']:
            db.save_ticker(symbol, data['ticker'][symbol])
        
        # Lưu dữ liệu Open Interest
        for symbol in data['open_interest']:
            db.save_realtime_open_interest(symbol, data['open_interest'][symbol])
    
    # Xuất dữ liệu cho GitHub Pages
    db.export_to_json()
    
    db.close()
    logger.info("Hoàn thành cập nhật dữ liệu realtime")

def detect_anomalies():
    """Phát hiện bất thường và gửi cảnh báo"""
    logger.info("Bắt đầu phát hiện bất thường")
    db = Database()
    detector = AnomalyDetector(db)
    bot = TelegramBot()
    
    # Phát hiện bất thường cho từng symbol
    for symbol in SYMBOLS:
        anomalies = detector.detect_all_anomalies(symbol)
    
    # Gửi các cảnh báo chưa được thông báo
    bot.send_anomalies(db)
    
    db.close()
    logger.info("Hoàn thành phát hiện bất thường")

def generate_reports():
    """Tạo báo cáo và biểu đồ"""
    logger.info("Bắt đầu tạo báo cáo và biểu đồ")
    db = Database()
    report_gen = ReportGenerator(db)
    chart_gen = ChartGenerator()
    
    # Tạo báo cáo tổng hợp
    summary = report_gen.generate_daily_summary()
    
    # Tạo biểu đồ cho từng symbol
    for symbol in SYMBOLS:
        charts = chart_gen.generate_all_charts(db, symbol, '1d')
    
    db.close()
    logger.info("Hoàn thành tạo báo cáo và biểu đồ")
    
    return True

def push_to_github():
    """Đẩy dữ liệu lên GitHub"""
    try:
        logger.info("Bắt đầu đẩy dữ liệu lên GitHub")
        
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
            commit_cmd = ["git", "commit", "-m", f"Update data: {timestamp}"]
            
            # Thực thi lệnh git commit
            subprocess.run(commit_cmd, check=True)
            
            # Đẩy lên GitHub
            push_cmd = ["git", "push"]
            subprocess.run(push_cmd, check=True)
            
            logger.info(f"Đã đẩy dữ liệu lên GitHub thành công lúc {timestamp}")
            return True
        else:
            logger.info("Không có thay đổi để commit")
            return False
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Lỗi khi đẩy dữ liệu lên GitHub: {e}")
        return False
    except Exception as e:
        logger.error(f"Lỗi không xác định khi đẩy dữ liệu lên GitHub: {str(e)}")
        return False

def generate_reports_and_push():
    """Tạo báo cáo và biểu đồ, sau đó đẩy lên GitHub"""
    success = generate_reports()
    if success:
        return push_to_github()
    return False

def send_daily_report():
    """Gửi báo cáo hàng ngày qua Telegram"""
    logger.info("Bắt đầu gửi báo cáo hàng ngày")
    db = Database()
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
        if symbol in summary['symbols']:
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
    
    db.close()
    logger.info("Hoàn thành gửi báo cáo hàng ngày")

def schedule_tasks():
    """Lập lịch các tác vụ định kỳ"""
    logger.info("Thiết lập lịch trình các tác vụ")
    
    # Thu thập dữ liệu lịch sử mỗi ngày lúc 00:05
    schedule.every().day.at("00:05").do(collect_historical_data)
    
    # Cập nhật dữ liệu realtime mỗi phút
    schedule.every(UPDATE_INTERVAL).seconds.do(update_realtime_data)
    
    # Phát hiện bất thường và gửi cảnh báo mỗi 5 phút
    schedule.every(15).minutes.do(detect_anomalies)
    
    # Tạo báo cáo và biểu đồ, sau đó đẩy lên GitHub mỗi giờ
    schedule.every(60).minutes.do(generate_reports_and_push)
    
    # Gửi báo cáo hàng ngày lúc 20:00
    schedule.every().day.at("20:00").do(send_daily_report)
    
    logger.info("Đã thiết lập lịch trình các tác vụ")

def run_scheduled_tasks():
    """Chạy các tác vụ đã lên lịch"""
    logger.info("Bắt đầu chạy các tác vụ theo lịch")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Lỗi khi chạy tác vụ theo lịch: {str(e)}")
            time.sleep(10)  # Đợi 10 giây trước khi thử lại

def initialize():
    """Khởi tạo hệ thống"""
    logger.info("Bắt đầu khởi tạo hệ thống")
    
    # Đảm bảo các thư mục cần thiết tồn tại
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/charts', exist_ok=True)
    os.makedirs('data/reports', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('docs/assets/data', exist_ok=True)
    
    # Khởi tạo cơ sở dữ liệu
    db = Database()
    db.close()
    
    logger.info("Hoàn thành khởi tạo hệ thống")

def main():
    """Hàm chính của ứng dụng"""
    parser = argparse.ArgumentParser(description='Hệ thống theo dõi Open Interest và Volume từ Binance')
    parser.add_argument('--collect', action='store_true', help='Thu thập dữ liệu lịch sử')
    parser.add_argument('--update', action='store_true', help='Cập nhật dữ liệu realtime')
    parser.add_argument('--detect', action='store_true', help='Phát hiện bất thường')
    parser.add_argument('--report', action='store_true', help='Tạo báo cáo và biểu đồ')
    parser.add_argument('--push', action='store_true', help='Đẩy dữ liệu lên GitHub')
    parser.add_argument('--report-push', action='store_true', help='Tạo báo cáo và đẩy lên GitHub')
    parser.add_argument('--daily', action='store_true', help='Gửi báo cáo hàng ngày')
    parser.add_argument('--schedule', action='store_true', help='Chạy các tác vụ theo lịch')
    args = parser.parse_args()
    
    # Khởi tạo hệ thống
    initialize()
    
    # Thực hiện các tác vụ dựa trên tham số
    if args.collect:
        collect_historical_data()
    elif args.update:
        update_realtime_data()
    elif args.detect:
        detect_anomalies()
    elif args.report:
        generate_reports()
    elif args.push:
        push_to_github()
    elif args.report_push:
        generate_reports_and_push()
    elif args.daily:
        send_daily_report()
    elif args.schedule:
        schedule_tasks()
        run_scheduled_tasks()
    else:
        # Mặc định: thu thập dữ liệu lịch sử và chạy theo lịch
        collect_historical_data()
        schedule_tasks()
        run_scheduled_tasks()

if __name__ == "__main__":
    main()