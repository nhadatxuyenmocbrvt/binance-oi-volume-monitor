import os
import json
from datetime import datetime
from config.settings import SYMBOLS, setup_logging
from data_analyzer.metrics import MarketMetrics

logger = setup_logging(__name__, 'report_generator.log')

class ReportGenerator:
    def __init__(self, db):
        self.db = db
        self.metrics = MarketMetrics()
        # Đảm bảo thư mục reports tồn tại
        os.makedirs('data/reports', exist_ok=True)
        logger.info("Khởi tạo ReportGenerator")
    
    def generate_symbol_report(self, symbol):
        """Tạo báo cáo cho một symbol"""
        try:
            # Lấy dữ liệu
            price_df = self.db.get_klines(symbol, '1d')
            oi_df = self.db.get_open_interest(symbol)
            volume_df = price_df.copy()  # Volume nằm trong price_df
            
            # Tính toán sentiment
            sentiment = self.metrics.calculate_market_sentiment(price_df, oi_df, volume_df)
            
            # Tính toán các thay đổi
            if not price_df.empty and len(price_df) > 1:
                price_change = price_df['close'].pct_change().iloc[-1] * 100
            else:
                price_change = 0
                
            if not oi_df.empty and len(oi_df) > 1:
                oi_change = oi_df['open_interest'].pct_change().iloc[-1] * 100
            else:
                oi_change = 0
                
            if not volume_df.empty and len(volume_df) > 1:
                volume_change = volume_df['volume'].pct_change().iloc[-1] * 100
            else:
                volume_change = 0
            
            # Tính toán tương quan
            correlation = self.metrics.calculate_correlation(price_df, oi_df)
            
            # Tạo báo cáo
            report = {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': {
                    'current': float(price_df['close'].iloc[-1]) if not price_df.empty else None,
                    'change_percent': price_change
                },
                'open_interest': {
                    'current': float(oi_df['open_interest'].iloc[-1]) if not oi_df.empty else None,
                    'change_percent': oi_change
                },
                'volume': {
                    'current': float(volume_df['volume'].iloc[-1]) if not volume_df.empty else None,
                    'change_percent': volume_change
                },
                'correlation': correlation['pearson_correlation'] if correlation else None,
                'sentiment': sentiment
            }
            
            # Lưu báo cáo
            file_path = f'data/reports/{symbol}_report.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Đã tạo báo cáo cho {symbol} tại {file_path}")
            return report
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo cho {symbol}: {str(e)}")
            return None
    
    def generate_daily_summary(self):
        """Tạo báo cáo tổng hợp hàng ngày"""
        try:
            # Thông tin tổng hợp
            summary = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbols': {}
            }
            
            # Tạo báo cáo cho từng symbol
            for symbol in SYMBOLS:
                report = self.generate_symbol_report(symbol)
                if report:
                    summary['symbols'][symbol] = {
                        'price_change': report['price']['change_percent'],
                        'oi_change': report['open_interest']['change_percent'],
                        'volume_change': report['volume']['change_percent'],
                        'sentiment': report['sentiment']['sentiment_label'] if report['sentiment'] else None
                    }
            
            # Lấy danh sách các bất thường gần đây
            anomalies_df = self.db.get_anomalies(limit=20)
            anomalies = []
            for _, row in anomalies_df.iterrows():
                anomalies.append({
                    'symbol': row['symbol'],
                    'timestamp': row['timestamp'],
                    'data_type': row['data_type'],
                    'message': row['message']
                })
            
            summary['anomalies'] = anomalies
            
            # Lưu báo cáo tổng hợp
            file_path = f'data/reports/daily_summary_{datetime.now().strftime("%Y%m%d")}.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            
            # Lưu phiên bản hiện tại cho trang web
            web_file_path = 'docs/assets/data/daily_summary.json'
            os.makedirs(os.path.dirname(web_file_path), exist_ok=True)
            with open(web_file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Đã tạo báo cáo tổng hợp hàng ngày tại {file_path}")
            return summary
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp hàng ngày: {str(e)}")
            return None