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
        # Đảm bảo các thư mục tồn tại
        os.makedirs('data/reports', exist_ok=True)
        os.makedirs('docs/assets/data', exist_ok=True)
        logger.info("Khởi tạo ReportGenerator")
    
# Các methods phụ trợ đã được chuyển vào metrics.py
    
    def generate_symbol_report(self, symbol):
        """Tạo báo cáo cho một symbol - ĐÃ SỬA ĐỂ SỬ DỤNG DỮ LIỆU THỰC"""
        try:
            # Lấy dữ liệu thực tế từ database
            price_df = self.db.get_klines(symbol, '1h', limit=48)  # 48h để có đủ dữ liệu
            oi_df = self.db.get_open_interest(symbol, limit=48)
            
            # Tính toán thông tin giá
            price_info = {'current': None, 'change_percent': 0.0}
            if not price_df.empty:
                price_info['current'] = float(price_df['close'].iloc[-1])
                price_info['change_percent'] = self.metrics.calculate_24h_percentage_change(price_df, 'close', '1h')
            
            # Tính toán thông tin volume  
            volume_info = {'current': None, 'change_percent': 0.0}
            if not price_df.empty:
                volume_info['current'] = float(price_df['volume'].iloc[-1])
                volume_info['change_percent'] = self.metrics.calculate_24h_percentage_change(price_df, 'volume', '1h')
            
            # Tính toán thông tin Open Interest
            oi_info = {'current': None, 'change_percent': 0.0}
            if not oi_df.empty:
                oi_info['current'] = float(oi_df['open_interest'].iloc[-1])
                oi_info['change_percent'] = self.metrics.calculate_safe_percentage_change(oi_df, 'open_interest')
            
            # Tính toán sentiment với dữ liệu thực tế
            sentiment = self.metrics.calculate_market_sentiment(price_df, oi_df, price_df)
            
            # Tính toán tương quan
            correlation = self.metrics.calculate_correlation(price_df, oi_df)
            
            # Tạo báo cáo
            report = {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price': price_info,
                'open_interest': oi_info,
                'volume': volume_info,
                'correlation': correlation['pearson_correlation'] if correlation else None,
                'sentiment': sentiment
            }
            
            # Lưu báo cáo
            file_path = f'data/reports/{symbol}_report.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"Đã tạo báo cáo cho {symbol}: Price {price_info['change_percent']:.2f}%, OI {oi_info['change_percent']:.2f}%, Volume {volume_info['change_percent']:.2f}%")
            return report
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo cho {symbol}: {str(e)}")
            return None
    
    def prepare_symbol_data_for_web(self, symbol):
        """Chuẩn bị dữ liệu JSON cho từng symbol để hiển thị trên web"""
        try:
            klines_data = {}
            for timeframe in ['1d', '4h', '1h']:
                df = self.db.get_klines(symbol, timeframe)
                if not df.empty:
                    # Chuyển đổi datetime thành string để JSON có thể serialize
                    df_copy = df.copy()
                    if 'open_time' in df_copy.columns:
                        df_copy['open_time'] = df_copy['open_time'].astype(str)
                    if 'close_time' in df_copy.columns:
                        df_copy['close_time'] = df_copy['close_time'].astype(str)
                    
                    klines_data[timeframe] = df_copy.to_dict('records')
            
            oi_data = self.db.get_open_interest(symbol)
            if not oi_data.empty:
                # Chuyển đổi datetime thành string
                oi_data_copy = oi_data.copy()
                if 'timestamp' in oi_data_copy.columns:
                    oi_data_copy['timestamp'] = oi_data_copy['timestamp'].astype(str)
                
                oi_list = oi_data_copy.to_dict('records')
            else:
                oi_list = []
            
            return {
                'klines': klines_data,
                'open_interest': oi_list
            }
        except Exception as e:
            logger.error(f"Lỗi khi chuẩn bị dữ liệu web cho {symbol}: {str(e)}")
            return {'klines': {}, 'open_interest': []}
    
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
                        'sentiment': report['sentiment']['sentiment_label'] if report['sentiment'] else 'Neutral'
                    }
                else:
                    # Nếu không tạo được báo cáo, đặt giá trị mặc định
                    summary['symbols'][symbol] = {
                        'price_change': 0.0,
                        'oi_change': 0.0,
                        'volume_change': 0.0,
                        'sentiment': 'Neutral'
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
            
            # Lưu báo cáo tổng hợp vào thư mục reports
            file_path = f'data/reports/daily_summary_{datetime.now().strftime("%Y%m%d")}.json'
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            
            # ===== PHẦN THÊM MỚI: TẠO DỮ LIỆU CHO GITHUB PAGES =====
            
            # Đảm bảo thư mục assets/data tồn tại
            os.makedirs('docs/assets/data', exist_ok=True)
            
            # Lưu daily_summary cho trang web
            web_summary_path = 'docs/assets/data/daily_summary.json'
            with open(web_summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            
            # Lưu danh sách symbols cho trang web
            symbols_web_path = 'docs/assets/data/symbols.json'
            with open(symbols_web_path, 'w') as f:
                json.dump(SYMBOLS, f)
            
            # Lưu anomalies cho trang web
            anomalies_web_path = 'docs/assets/data/anomalies.json'
            with open(anomalies_web_path, 'w') as f:
                json.dump(anomalies, f, default=str)
            
            # Lưu dữ liệu cho từng symbol
            for symbol in SYMBOLS:
                # Tạo dữ liệu JSON cho từng symbol
                symbol_data = self.prepare_symbol_data_for_web(symbol)
                
                # Lưu vào thư mục web
                symbol_web_path = f'docs/assets/data/{symbol}.json'
                with open(symbol_web_path, 'w') as f:
                    json.dump(symbol_data, f, default=str)
            
            logger.info(f"Đã tạo báo cáo tổng hợp hàng ngày và dữ liệu cho GitHub Pages")
            return summary
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp hàng ngày: {str(e)}")
            return None