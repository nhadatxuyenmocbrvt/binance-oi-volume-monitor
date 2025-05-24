import os
import json
from datetime import datetime, timedelta
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

    def generate_24h_data(self):
        """Tạo dữ liệu tracking 24h cho trang web"""
        try:
            logger.info("📈 Bắt đầu tạo dữ liệu tracking 24h")
            
            tracking_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'symbols': {},
                'summary': {
                    'total_symbols': len(SYMBOLS),
                    'most_volatile': None,
                    'highest_volume_change': None,
                    'highest_oi_change': None
                }
            }
            
            max_volatility = 0
            max_volume_change = 0
            max_oi_change = 0
            
            for symbol in SYMBOLS:
                try:
                    # Lấy dữ liệu 1h cho 24 giờ qua
                    price_df = self.db.get_klines(symbol, '1h', limit=24)
                    oi_df = self.db.get_open_interest(symbol, limit=24)
                    
                    if price_df.empty:
                        logger.warning(f"Không có dữ liệu giá cho {symbol}")
                        continue
                    
                    # Tính toán dữ liệu theo từng giờ
                    hours_data = []
                    
                    for i in range(len(price_df)):
                        hour_data = {
                            'hour_timestamp': price_df.iloc[i]['open_time'].strftime('%Y-%m-%d %H:%M:%S') if i < len(price_df) else None,
                            'hour': i,
                            'price': float(price_df.iloc[i]['close']) if i < len(price_df) else None,
                            'volume': float(price_df.iloc[i]['volume']) if i < len(price_df) else None,
                            'price_change_1h': 0.0,
                            'volume_change_1h': 0.0,
                            'oi': None,
                            'oi_change_1h': 0.0
                        }
                        
                        # Tính thay đổi giá so với giờ trước
                        if i > 0:
                            prev_price = float(price_df.iloc[i-1]['close'])
                            curr_price = float(price_df.iloc[i]['close'])
                            hour_data['price_change_1h'] = ((curr_price - prev_price) / prev_price) * 100
                            
                            prev_volume = float(price_df.iloc[i-1]['volume'])
                            curr_volume = float(price_df.iloc[i]['volume'])
                            if prev_volume > 0:
                                hour_data['volume_change_1h'] = ((curr_volume - prev_volume) / prev_volume) * 100
                        
                        # Thêm dữ liệu OI nếu có
                        if not oi_df.empty and i < len(oi_df):
                            hour_data['oi'] = float(oi_df.iloc[i]['open_interest'])
                            if i > 0 and i < len(oi_df):
                                prev_oi = float(oi_df.iloc[i-1]['open_interest'])
                                curr_oi = float(oi_df.iloc[i]['open_interest'])
                                if prev_oi > 0:
                                    hour_data['oi_change_1h'] = ((curr_oi - prev_oi) / prev_oi) * 100
                        
                        hours_data.append(hour_data)
                    
                    # Tính toán các thống kê tổng hợp
                    if len(price_df) >= 2:
                        # Thay đổi giá 24h
                        price_24h_change = ((float(price_df.iloc[-1]['close']) - float(price_df.iloc[0]['close'])) / float(price_df.iloc[0]['close'])) * 100
                        
                        # Độ biến động (volatility) = standard deviation của thay đổi giá theo giờ
                        price_changes = [h['price_change_1h'] for h in hours_data if h['price_change_1h'] != 0]
                        price_volatility = 0
                        if len(price_changes) > 1:
                            import statistics
                            price_volatility = statistics.stdev(price_changes)
                        
                        # Tìm giờ có thay đổi giá cao nhất
                        max_change_hour = max(hours_data, key=lambda x: abs(x['price_change_1h']))
                        
                        # Thay đổi volume 24h
                        volume_24h_change = 0
                        if len(price_df) >= 2:
                            volume_24h_change = ((float(price_df.iloc[-1]['volume']) - float(price_df.iloc[0]['volume'])) / float(price_df.iloc[0]['volume'])) * 100
                        
                        # Thay đổi OI 24h
                        oi_24h_change = 0
                        if not oi_df.empty and len(oi_df) >= 2:
                            oi_24h_change = ((float(oi_df.iloc[-1]['open_interest']) - float(oi_df.iloc[0]['open_interest'])) / float(oi_df.iloc[0]['open_interest'])) * 100
                        
                        symbol_data = {
                            'hours_data': hours_data,
                            'price_24h_change': price_24h_change,
                            'volume_24h_change': volume_24h_change,
                            'oi_24h_change': oi_24h_change,
                            'price_volatility': price_volatility,
                            'max_price_change_hour': {
                                'hour': max_change_hour['hour'],
                                'change': max_change_hour['price_change_1h'],
                                'timestamp': max_change_hour['hour_timestamp']
                            },
                            'current_price': float(price_df.iloc[-1]['close']),
                            'current_volume': float(price_df.iloc[-1]['volume']),
                            'current_oi': float(oi_df.iloc[-1]['open_interest']) if not oi_df.empty else 0
                        }
                        
                        tracking_data['symbols'][symbol] = symbol_data
                        
                        # Cập nhật summary
                        if price_volatility > max_volatility:
                            max_volatility = price_volatility
                            tracking_data['summary']['most_volatile'] = symbol
                        
                        if abs(volume_24h_change) > max_volume_change:
                            max_volume_change = abs(volume_24h_change)
                            tracking_data['summary']['highest_volume_change'] = symbol
                        
                        if abs(oi_24h_change) > max_oi_change:
                            max_oi_change = abs(oi_24h_change)
                            tracking_data['summary']['highest_oi_change'] = symbol
                    
                    logger.info(f"Đã tạo dữ liệu tracking 24h cho {symbol}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi tạo dữ liệu tracking 24h cho {symbol}: {str(e)}")
                    continue
            
            # Lưu dữ liệu tracking 24h vào file JSON
            tracking_file_path = 'docs/assets/data/tracking_24h.json'
            with open(tracking_file_path, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, ensure_ascii=False, indent=2, default=str)
            
            logger.info(f"✅ Đã tạo dữ liệu tracking 24h thành công với {len(tracking_data['symbols'])} symbols")
            return tracking_data
            
        except Exception as e:
            logger.error(f"Lỗi khi tạo dữ liệu tracking 24h: {str(e)}")
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
            
            # ===== TẠO DỮ LIỆU TRACKING 24H =====
            tracking_24h_data = self.generate_24h_data()
            if tracking_24h_data:
                logger.info("✅ Đã tạo dữ liệu tracking 24h thành công")
            else:
                logger.warning("⚠️ Không thể tạo dữ liệu tracking 24h")
            
            logger.info(f"Đã tạo báo cáo tổng hợp hàng ngày và dữ liệu cho GitHub Pages")
            return summary
        except Exception as e:
            logger.error(f"Lỗi khi tạo báo cáo tổng hợp hàng ngày: {str(e)}")
            return None