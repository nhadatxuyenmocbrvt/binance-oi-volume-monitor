import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import setup_logging, SYMBOLS
from data_analyzer.metrics import OptimizedOIVolumeMetrics

logger = setup_logging(__name__, 'report_generator.log')

# Thêm NumpyEncoder để xử lý các kiểu dữ liệu NumPy
class NumpyEncoder(json.JSONEncoder):
    """JSON Encoder tùy chỉnh để xử lý các kiểu dữ liệu NumPy"""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super(NumpyEncoder, self).default(obj)

# Hàm tiện ích để chuyển đổi dữ liệu NumPy
def convert_numpy_types(obj):
    """Chuyển đổi các kiểu dữ liệu NumPy thành kiểu Python tiêu chuẩn"""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif pd.isna(obj):  # Xử lý giá trị NaN, NaT
        return None
    else:
        return obj

class OptimizedReportGenerator:
    """
    Tạo báo cáo tối ưu cho OI & Volume
    Focus: Tracking 24h (hourly) + 30d (daily)
    """
    
    def __init__(self, db):
        self.db = db
        self.metrics = OptimizedOIVolumeMetrics()
        logger.info("🔧 Khởi tạo OptimizedReportGenerator - Focus OI & Volume")
    
    def generate_daily_summary(self):
        """
        Tạo báo cáo tổng hợp hàng ngày tối ưu
        """
        try:
            logger.info("📊 Tạo báo cáo tổng hợp hàng ngày")
            
            summary = {
                'timestamp': datetime.now().isoformat(),
                'report_type': 'daily_oi_volume_summary',
                'symbols': {},
                'overall_metrics': {
                    'total_symbols': len(SYMBOLS),
                    'bullish_count': 0,
                    'bearish_count': 0,
                    'neutral_count': 0
                },
                'anomalies_summary': {},
                'data_quality': {}
            }
            
            # Tạo báo cáo cho từng symbol
            for symbol in SYMBOLS:
                try:
                    symbol_report = self._generate_symbol_report(symbol)
                    summary['symbols'][symbol] = symbol_report
                    
                    # Cập nhật overall metrics
                    sentiment = symbol_report.get('overall_sentiment', 'neutral')
                    if 'bullish' in sentiment:
                        summary['overall_metrics']['bullish_count'] += 1
                    elif 'bearish' in sentiment:
                        summary['overall_metrics']['bearish_count'] += 1
                    else:
                        summary['overall_metrics']['neutral_count'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Lỗi khi tạo báo cáo cho {symbol}: {str(e)}")
                    summary['symbols'][symbol] = self._get_empty_symbol_report()
            
            # Tạo anomalies summary
            summary['anomalies_summary'] = self._generate_anomalies_summary()
            
            # Lưu báo cáo
            self._save_report(summary, 'daily_summary.json')
            
            logger.info("✅ Hoàn thành báo cáo tổng hợp hàng ngày")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo báo cáo tổng hợp: {str(e)}")
            return {}
    
    def generate_24h_data(self):
        """
        Tạo dữ liệu tracking 24h cho web interface
        """
        try:
            logger.info("📈 Tạo dữ liệu tracking 24h")
            
            tracking_data = {
                'timestamp': datetime.now().isoformat(),
                'data_type': '24h_hourly_tracking',
                'symbols': {}
            }
            
            for symbol in SYMBOLS:
                try:
                    # Lấy dữ liệu tracking 24h
                    tracking_df = self.db.get_24h_tracking_data(symbol)
                    
                    if not tracking_df.empty:
                        # Tính toán metrics
                        oi_metrics = self.metrics.calculate_hourly_oi_metrics(tracking_df)
                        volume_metrics = self.metrics.calculate_hourly_volume_metrics(tracking_df)
                        correlation = self.metrics.calculate_oi_volume_correlation(tracking_df, '24h')
                        
                        # Chuẩn bị dữ liệu cho chart
                        chart_data = []
                        for _, row in tracking_df.iterrows():
                            chart_data.append({
                                'timestamp': row['hour_timestamp'].isoformat() if hasattr(row['hour_timestamp'], 'isoformat') else str(row['hour_timestamp']),
                                'hour': row['hour_timestamp'].strftime('%H:00') if hasattr(row['hour_timestamp'], 'strftime') else str(row['hour_timestamp']),
                                'oi': float(row['open_interest']),
                                'volume': float(row['volume']),
                                'price': float(row['price']),
                                'oi_change_1h': float(row.get('oi_change_1h', 0)),
                                'volume_change_1h': float(row.get('volume_change_1h', 0)),
                                'price_change_1h': float(row.get('price_change_1h', 0))
                            })
                        
                        # Tạo dữ liệu symbol
                        tracking_data['symbols'][symbol] = {
                            'oi_metrics': oi_metrics,
                            'volume_metrics': volume_metrics,
                            'correlation': correlation,
                            'chart_data': chart_data,
                            'data_points': len(chart_data),
                            'last_update': tracking_df['hour_timestamp'].iloc[-1].isoformat() if not tracking_df.empty else None
                        }
                        
                    else:
                        tracking_data['symbols'][symbol] = self._get_empty_24h_data()
                        
                except Exception as e:
                    logger.error(f"❌ Lỗi khi tạo tracking 24h cho {symbol}: {str(e)}")
                    tracking_data['symbols'][symbol] = self._get_empty_24h_data()
            
            # Lưu dữ liệu tracking 24h
            self._save_report(tracking_data, '24h_tracking.json')
            
            logger.info("✅ Hoàn thành tạo dữ liệu tracking 24h")
            return tracking_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo dữ liệu tracking 24h: {str(e)}")
            return {}
    
    def generate_30d_data(self):
        """
        Tạo dữ liệu tracking 30d cho web interface
        """
        try:
            logger.info("📊 Tạo dữ liệu tracking 30d")
            
            tracking_data = {
                'timestamp': datetime.now().isoformat(),
                'data_type': '30d_daily_tracking',
                'symbols': {}
            }
            
            for symbol in SYMBOLS:
                try:
                    # Lấy dữ liệu OI và klines 30 ngày
                    oi_df = self.db.get_open_interest(symbol, limit=720)  # 30 days * 24 hours
                    klines_df = self.db.get_klines(symbol, '1d', limit=30)
                    
                    if not oi_df.empty and not klines_df.empty:
                        # Tính toán metrics
                        oi_metrics = self.metrics.calculate_daily_oi_metrics(oi_df)
                        volume_metrics = self.metrics.calculate_daily_volume_metrics(klines_df)
                        
                        # Merge dữ liệu cho correlation
                        merged_df = self._merge_daily_data(oi_df, klines_df)
                        correlation = self.metrics.calculate_oi_volume_correlation(merged_df, '30d')
                        
                        # Chuẩn bị dữ liệu chart (daily aggregated)
                        chart_data = self._prepare_30d_chart_data(oi_df, klines_df)
                        
                        tracking_data['symbols'][symbol] = {
                            'oi_metrics': oi_metrics,
                            'volume_metrics': volume_metrics,
                            'correlation': correlation,
                            'chart_data': chart_data,
                            'data_points': len(chart_data),
                            'last_update': datetime.now().isoformat()
                        }
                        
                    else:
                        tracking_data['symbols'][symbol] = self._get_empty_30d_data()
                        
                except Exception as e:
                    logger.error(f"❌ Lỗi khi tạo tracking 30d cho {symbol}: {str(e)}")
                    tracking_data['symbols'][symbol] = self._get_empty_30d_data()
            
            # Lưu dữ liệu tracking 30d
            self._save_report(tracking_data, '30d_tracking.json')
            
            logger.info("✅ Hoàn thành tạo dữ liệu tracking 30d")
            return tracking_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo dữ liệu tracking 30d: {str(e)}")
            return {}
    
    def generate_web_data(self):
        """
        Tạo tất cả dữ liệu cần thiết cho web interface
        """
        try:
            logger.info("🌐 Tạo dữ liệu cho web interface")
            
            # Tạo dữ liệu 24h và 30d
            data_24h = self.generate_24h_data()
            data_30d = self.generate_30d_data()
            daily_summary = self.generate_daily_summary()
            
            # Tạo index data cho web
            web_data = {
                'last_update': datetime.now().isoformat(),
                'symbols': SYMBOLS,
                'data_24h': data_24h,
                'data_30d': data_30d,
                'summary': daily_summary,
                'status': 'active'
            }
            
            # Lưu index data
            self._save_report(web_data, 'web_index.json')
            
            logger.info("✅ Hoàn thành tạo dữ liệu cho web")
            return web_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo dữ liệu web: {str(e)}")
            return {}
    
    def _generate_symbol_report(self, symbol):
        """
        Tạo báo cáo chi tiết cho một symbol
        """
        try:
            report = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat()
            }
            
            # Lấy dữ liệu tracking 24h
            tracking_df = self.db.get_24h_tracking_data(symbol)
            if not tracking_df.empty:
                oi_metrics_24h = self.metrics.calculate_hourly_oi_metrics(tracking_df)
                volume_metrics_24h = self.metrics.calculate_hourly_volume_metrics(tracking_df)
                
                report['24h_metrics'] = {
                    'oi': oi_metrics_24h,
                    'volume': volume_metrics_24h
                }
            else:
                report['24h_metrics'] = {
                    'oi': self.metrics._get_empty_oi_metrics(),
                    'volume': self.metrics._get_empty_volume_metrics()
                }
            
            # Lấy dữ liệu 30d
            oi_df = self.db.get_open_interest(symbol, limit=720)
            klines_df = self.db.get_klines(symbol, '1d', limit=30)
            
            if not oi_df.empty and not klines_df.empty:
                oi_metrics_30d = self.metrics.calculate_daily_oi_metrics(oi_df)
                volume_metrics_30d = self.metrics.calculate_daily_volume_metrics(klines_df)
                
                report['30d_metrics'] = {
                    'oi': oi_metrics_30d,
                    'volume': volume_metrics_30d
                }
            else:
                report['30d_metrics'] = {
                    'oi': self.metrics._get_empty_oi_metrics_30d(),
                    'volume': self.metrics._get_empty_volume_metrics_30d()
                }
            
            # Tính overall sentiment
            report['overall_sentiment'] = self._determine_overall_sentiment(
                report['24h_metrics'],
                report['30d_metrics']
            )
            
            # Thêm summary metrics
            report['price_change'] = report['24h_metrics']['oi'].get('oi_change_24h', 0)  # Tạm thời dùng OI change
            report['sentiment'] = report['overall_sentiment']
            
            return report
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo báo cáo symbol {symbol}: {str(e)}")
            return self._get_empty_symbol_report()
    
    def _generate_anomalies_summary(self):
        """
        Tạo tóm tắt anomalies gần đây
        """
        try:
            # Lấy anomalies 24h gần nhất
            anomalies_df = self.db.get_anomalies(limit=100)
            
            if anomalies_df.empty:
                return {
                    'total': 0,
                    'by_symbol': {},
                    'by_type': {},
                    'recent_24h': 0
                }
            
            # Lọc anomalies 24h gần nhất
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_anomalies = anomalies_df[anomalies_df['timestamp'] >= cutoff_time]
            
            summary = {
                'total': len(anomalies_df),
                'recent_24h': len(recent_anomalies),
                'by_symbol': recent_anomalies['symbol'].value_counts().to_dict() if not recent_anomalies.empty else {},
                'by_type': recent_anomalies['data_type'].value_counts().to_dict() if not recent_anomalies.empty else {},
                'timestamp': datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo anomalies summary: {str(e)}")
            return {
                'total': 0,
                'by_symbol': {},
                'by_type': {},
                'recent_24h': 0
            }
    
    # Sửa trong hàm _merge_daily_data để sử dụng open_interest_value và quote_volume
    def _merge_daily_data(self, oi_df, klines_df):
        """
        Merge dữ liệu OI và klines theo ngày
        """
        try:
            # Group OI data by date
            oi_df['date'] = pd.to_datetime(oi_df['timestamp']).dt.date
            
            # FIX: Sử dụng open_interest_value thay vì open_interest nếu có
            if 'open_interest_value' in oi_df.columns:
                oi_daily = oi_df.groupby('date')['open_interest_value'].mean().reset_index()
                oi_daily.rename(columns={'open_interest_value': 'open_interest_value'}, inplace=True)
            else:
                oi_daily = oi_df.groupby('date')['open_interest'].mean().reset_index()
                oi_daily.rename(columns={'open_interest': 'open_interest_value'}, inplace=True)
            
            # Group klines data by date
            klines_df['date'] = pd.to_datetime(klines_df['open_time']).dt.date
            
            # FIX: Sử dụng quote_volume thay vì volume nếu có
            agg_dict = {'close': 'last'}
            if 'quote_volume' in klines_df.columns:
                agg_dict['quote_volume'] = 'sum'
                volume_daily = klines_df.groupby('date').agg(agg_dict).reset_index()
                volume_daily.rename(columns={'quote_volume': 'quote_volume'}, inplace=True)
            else:
                agg_dict['volume'] = 'sum'
                volume_daily = klines_df.groupby('date').agg(agg_dict).reset_index()
                volume_daily.rename(columns={'volume': 'quote_volume'}, inplace=True)
            
            # Merge
            merged = pd.merge(oi_daily, volume_daily, on='date', how='inner')
            merged['timestamp'] = pd.to_datetime(merged['date'])
            
            return merged
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi merge daily data: {str(e)}")
            return pd.DataFrame()

    # Sửa trong hàm _prepare_30d_chart_data để sử dụng trường đúng
    def _prepare_30d_chart_data(self, oi_df, klines_df):
        """
        Chuẩn bị dữ liệu chart cho 30 ngày
        """
        try:
            merged_df = self._merge_daily_data(oi_df, klines_df)
            
            if merged_df.empty:
                return []
            
            # Lấy 30 ngày gần nhất
            merged_df = merged_df.sort_values('date').tail(30)
            
            chart_data = []
            for _, row in merged_df.iterrows():
                chart_data.append({
                    'date': row['date'].isoformat(),
                    'date_timestamp': row['timestamp'].isoformat(),
                    # FIX: Sử dụng các trường đúng
                    'oi': float(row['open_interest_value']),
                    'volume': float(row['quote_volume']),
                    'open_interest_value': float(row['open_interest_value']),
                    'quote_volume': float(row['quote_volume']),
                    'price': float(row['close'])
                })
            
            return chart_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi chuẩn bị 30d chart data: {str(e)}")
            return []
    
    def _determine_overall_sentiment(self, metrics_24h, metrics_30d):
        """
        Xác định sentiment tổng thể
        """
        try:
            # Lấy thay đổi từ metrics
            oi_change_24h = metrics_24h['oi'].get('oi_change_24h', 0)
            volume_change_24h = metrics_24h['volume'].get('volume_change_24h', 0)
            oi_change_30d = metrics_30d['oi'].get('oi_change_30d', 0)
            volume_change_30d = metrics_30d['volume'].get('volume_change_30d', 0)
            
            # Logic sentiment đơn giản
            if oi_change_24h > 5 and volume_change_24h > 10:
                return 'strong_bullish'
            elif oi_change_24h > 1 and volume_change_24h > 5:
                return 'bullish'
            elif oi_change_24h < -5 and volume_change_24h < -10:
                return 'strong_bearish'
            elif oi_change_24h < -1 and volume_change_24h < -5:
                return 'bearish'
            elif abs(oi_change_30d) > 20 or abs(volume_change_30d) > 30:
                return 'volatile'
            else:
                return 'neutral'
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi xác định sentiment: {str(e)}")
            return 'neutral'
    
    def _save_report(self, data, filename):
        """
        Lưu báo cáo vào file JSON
        """
        try:
            # Đảm bảo thư mục tồn tại
            os.makedirs('data/reports', exist_ok=True)
            os.makedirs('data/json', exist_ok=True)
            os.makedirs('docs/assets/data', exist_ok=True)  # Thêm thư mục cho GitHub Pages
            
            # Chuyển đổi dữ liệu NumPy trước khi lưu
            converted_data = convert_numpy_types(data)
            
            # Lưu vào thư mục reports
            reports_path = f'data/reports/{filename}'
            with open(reports_path, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
            
            # Lưu vào thư mục json cho web
            json_path = f'data/json/{filename}'
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
                
            # Lưu vào thư mục GitHub Pages
            github_pages_path = f'docs/assets/data/{filename}'
            with open(github_pages_path, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
            
            logger.info(f"💾 Đã lưu báo cáo: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lưu báo cáo {filename}: {str(e)}")
    
    # Helper methods để trả về dữ liệu trống
    def _get_empty_symbol_report(self):
        return {
            'symbol': '',
            'timestamp': datetime.now().isoformat(),
            '24h_metrics': {
                'oi': self.metrics._get_empty_oi_metrics(),
                'volume': self.metrics._get_empty_volume_metrics()
            },
            '30d_metrics': {
                'oi': self.metrics._get_empty_oi_metrics_30d(),
                'volume': self.metrics._get_empty_volume_metrics_30d()
            },
            'overall_sentiment': 'neutral',
            'price_change': 0,
            'sentiment': 'neutral'
        }
    
    def _get_empty_24h_data(self):
        return {
            'oi_metrics': self.metrics._get_empty_oi_metrics(),
            'volume_metrics': self.metrics._get_empty_volume_metrics(),
            'correlation': {'correlation': 0, 'correlation_strength': 'no_data'},
            'chart_data': [],
            'data_points': 0,
            'last_update': None
        }
    
    def _get_empty_30d_data(self):
        return {
            'oi_metrics': self.metrics._get_empty_oi_metrics_30d(),
            'volume_metrics': self.metrics._get_empty_volume_metrics_30d(),
            'correlation': {'correlation': 0, 'correlation_strength': 'no_data'},
            'chart_data': [],
            'data_points': 0,
            'last_update': None
        }

# Backward compatibility alias
ReportGenerator = OptimizedReportGenerator