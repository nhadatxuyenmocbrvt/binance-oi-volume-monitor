import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import ANOMALY_THRESHOLD, setup_logging
from data_analyzer.metrics import OptimizedOIVolumeMetrics

logger = setup_logging(__name__, 'anomaly_detector.log')

class OptimizedAnomalyDetector:
    """
    Detector bất thường tối ưu cho OI & Volume
    Focus: Phát hiện anomalies trong tracking 24h và 30d
    """
    
    def __init__(self, db):
        self.db = db
        self.metrics = OptimizedOIVolumeMetrics()
        self.threshold = ANOMALY_THRESHOLD
        logger.info(f"🔧 Khởi tạo OptimizedAnomalyDetector với ngưỡng {self.threshold}")
    
    def detect_24h_anomalies(self, symbol):
        """
        Phát hiện bất thường trong dữ liệu 24h (hourly tracking)
        """
        try:
            logger.info(f"🔍 Phát hiện anomalies 24h cho {symbol}")
            
            # Lấy dữ liệu tracking 24h
            tracking_df = self.db.get_24h_tracking_data(symbol)
            if tracking_df.empty:
                logger.warning(f"Không có dữ liệu tracking 24h cho {symbol}")
                return []
            
            # Phát hiện anomalies
            anomalies = self.metrics.detect_oi_volume_anomalies(tracking_df, self.threshold)
            
            # Xử lý và format anomalies
            formatted_anomalies = []
            for anomaly in anomalies:
                if self._is_recent_anomaly(anomaly['timestamp'], hours=24):
                    formatted_anomaly = {
                        'symbol': symbol,
                        'timestamp': anomaly['timestamp'],
                        'data_type': f"24h_{anomaly['metric']}",
                        'value': anomaly['value'],
                        'z_score': anomaly['z_score'],
                        'severity': anomaly['severity'],
                        'message': f"Bất thường {anomaly['metric']} 24h cho {symbol}: {anomaly['value']:.2f} (Z-score: {anomaly['z_score']:.2f})"
                    }
                    formatted_anomalies.append(formatted_anomaly)
            
            logger.info(f"✅ Phát hiện {len(formatted_anomalies)} anomalies 24h cho {symbol}")
            return formatted_anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện anomalies 24h cho {symbol}: {str(e)}")
            return []
    
    def detect_30d_anomalies(self, symbol):
        """
        Phát hiện bất thường trong dữ liệu 30d (daily tracking)
        """
        try:
            logger.info(f"🔍 Phát hiện anomalies 30d cho {symbol}")
            
            # Lấy dữ liệu OI và Volume 30 ngày
            oi_df = self.db.get_open_interest(symbol, limit=30)
            klines_df = self.db.get_klines(symbol, '1d', limit=30)
            
            anomalies = []
            
            # Phát hiện anomalies cho OI
            if not oi_df.empty:
                oi_anomalies = self.metrics.detect_oi_volume_anomalies(oi_df, self.threshold)
                for anomaly in oi_anomalies:
                    if self._is_recent_anomaly(anomaly['timestamp'], days=30):
                        formatted_anomaly = {
                            'symbol': symbol,
                            'timestamp': anomaly['timestamp'],
                            'data_type': f"30d_{anomaly['metric']}",
                            'value': anomaly['value'],
                            'z_score': anomaly['z_score'],
                            'severity': anomaly['severity'],
                            'message': f"Bất thường {anomaly['metric']} 30d cho {symbol}: {anomaly['value']:.2f} (Z-score: {anomaly['z_score']:.2f})"
                        }
                        anomalies.append(formatted_anomaly)
            
            # Phát hiện anomalies cho Volume
            if not klines_df.empty:
                volume_anomalies = self.metrics.detect_oi_volume_anomalies(klines_df, self.threshold)
                for anomaly in volume_anomalies:
                    if self._is_recent_anomaly(anomaly['timestamp'], days=30):
                        formatted_anomaly = {
                            'symbol': symbol,
                            'timestamp': anomaly['timestamp'],
                            'data_type': f"30d_{anomaly['metric']}",
                            'value': anomaly['value'],
                            'z_score': anomaly['z_score'],
                            'severity': anomaly['severity'],
                            'message': f"Bất thường {anomaly['metric']} 30d cho {symbol}: {anomaly['value']:.2f} (Z-score: {anomaly['z_score']:.2f})"
                        }
                        anomalies.append(formatted_anomaly)
            
            logger.info(f"✅ Phát hiện {len(anomalies)} anomalies 30d cho {symbol}")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện anomalies 30d cho {symbol}: {str(e)}")
            return []
    
    def detect_oi_volume_correlation_anomalies(self, symbol, period='24h'):
        """
        Phát hiện bất thường trong tương quan OI-Volume
        """
        try:
            logger.info(f"🔍 Phát hiện anomalies correlation {period} cho {symbol}")
            
            anomalies = []
            
            if period == '24h':
                # Lấy dữ liệu tracking 24h
                df = self.db.get_24h_tracking_data(symbol)
                threshold_correlation = -0.7  # Tương quan âm mạnh bất thường
            else:
                # Lấy dữ liệu 30d
                oi_df = self.db.get_open_interest(symbol, limit=30)
                klines_df = self.db.get_klines(symbol, '1d', limit=30)
                
                if oi_df.empty or klines_df.empty:
                    return []
                
                # Merge dữ liệu theo timestamp
                df = self._merge_oi_volume_data(oi_df, klines_df)
                threshold_correlation = -0.6  # Threshold thấp hơn cho daily
            
            if df.empty or len(df) < 5:
                return []
            
            # Tính correlation
            correlation_result = self.metrics.calculate_oi_volume_correlation(df, period)
            correlation = correlation_result.get('correlation', 0)
            
            # Kiểm tra anomaly correlation
            if correlation < threshold_correlation:
                anomaly = {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'data_type': f'correlation_{period}',
                    'value': correlation,
                    'z_score': abs(correlation) * 3,  # Pseudo Z-score
                    'severity': 'high' if correlation < threshold_correlation - 0.1 else 'moderate',
                    'message': f"Tương quan âm bất thường OI-Volume {period} cho {symbol}: {correlation:.3f} ({correlation_result.get('correlation_strength', 'unknown')})"
                }
                anomalies.append(anomaly)
            
            logger.info(f"✅ Correlation {period} {symbol}: {correlation:.3f}")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện correlation anomalies: {str(e)}")
            return []
    
    def detect_volume_spike_anomalies(self, symbol, spike_multiplier=3.0):
        """
        Phát hiện đột biến volume bất thường
        """
        try:
            logger.info(f"🔍 Phát hiện volume spikes cho {symbol}")
            
            anomalies = []
            
            # Kiểm tra 24h tracking
            tracking_df = self.db.get_24h_tracking_data(symbol)
            if not tracking_df.empty and len(tracking_df) > 6:
                # Tính toán metrics volume 24h
                volume_metrics = self.metrics.calculate_hourly_volume_metrics(tracking_df)
                volume_spikes = volume_metrics.get('volume_spikes', 0)
                
                if volume_spikes > 0:
                    # Lấy giờ có volume spike
                    recent_volume = tracking_df['volume'].iloc[-1]
                    avg_volume = volume_metrics.get('avg_volume_24h', 0)
                    
                    if avg_volume > 0 and recent_volume > avg_volume * spike_multiplier:
                        anomaly = {
                            'symbol': symbol,
                            'timestamp': tracking_df['hour_timestamp'].iloc[-1],
                            'data_type': 'volume_spike_24h',
                            'value': recent_volume,
                            'z_score': recent_volume / avg_volume,
                            'severity': 'high' if recent_volume > avg_volume * (spike_multiplier + 1) else 'moderate',
                            'message': f"Volume spike 24h cho {symbol}: {recent_volume:.0f} (gấp {recent_volume/avg_volume:.1f}x trung bình)"
                        }
                        anomalies.append(anomaly)
            
            # Kiểm tra daily volume
            klines_df = self.db.get_klines(symbol, '1d', limit=7)
            if not klines_df.empty and len(klines_df) > 2:
                daily_volume_metrics = self.metrics.calculate_daily_volume_metrics(klines_df, days=7)
                current_volume = daily_volume_metrics.get('current_volume', 0)
                avg_volume = daily_volume_metrics.get('avg_volume_30d', 0)  # Sử dụng giá trị có sẵn
                
                if avg_volume > 0 and current_volume > avg_volume * spike_multiplier:
                    anomaly = {
                        'symbol': symbol,
                        'timestamp': klines_df['open_time'].iloc[-1],
                        'data_type': 'volume_spike_daily',
                        'value': current_volume,
                        'z_score': current_volume / avg_volume,
                        'severity': 'high' if current_volume > avg_volume * (spike_multiplier + 1) else 'moderate',
                        'message': f"Volume spike daily cho {symbol}: {current_volume:.0f} (gấp {current_volume/avg_volume:.1f}x trung bình)"
                    }
                    anomalies.append(anomaly)
            
            logger.info(f"✅ Phát hiện {len(anomalies)} volume spikes cho {symbol}")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện volume spikes: {str(e)}")
            return []
    
    def detect_oi_divergence_anomalies(self, symbol):
        """
        Phát hiện bất thường khi OI và giá di chuyển ngược chiều
        """
        try:
            logger.info(f"🔍 Phát hiện OI-Price divergence cho {symbol}")
            
            anomalies = []
            
            # Kiểm tra 24h tracking
            tracking_df = self.db.get_24h_tracking_data(symbol)
            if not tracking_df.empty and len(tracking_df) >= 6:
                # Tính các metrics
                oi_metrics = self.metrics.calculate_hourly_oi_metrics(tracking_df)
                
                # Tính thay đổi giá
                price_change = 0
                if 'price' in tracking_df.columns and len(tracking_df) > 1:
                    current_price = tracking_df['price'].iloc[-1]
                    first_price = tracking_df['price'].iloc[0]
                    if first_price > 0:
                        price_change = ((current_price - first_price) / first_price) * 100
                
                oi_change = oi_metrics.get('oi_change_24h', 0)
                
                # Phát hiện divergence: OI tăng mạnh nhưng giá giảm (hoặc ngược lại)
                if abs(oi_change) > 5 and abs(price_change) > 2:
                    if (oi_change > 5 and price_change < -2) or (oi_change < -5 and price_change > 2):
                        severity = 'high' if abs(oi_change) > 10 or abs(price_change) > 5 else 'moderate'
                        anomaly = {
                            'symbol': symbol,
                            'timestamp': tracking_df['hour_timestamp'].iloc[-1],
                            'data_type': 'oi_price_divergence_24h',
                            'value': oi_change,
                            'z_score': abs(oi_change) / 5,  # Normalized score
                            'severity': severity,
                            'message': f"OI-Price divergence 24h cho {symbol}: OI {oi_change:+.2f}%, Price {price_change:+.2f}%"
                        }
                        anomalies.append(anomaly)
            
            logger.info(f"✅ Kiểm tra OI divergence cho {symbol}: {len(anomalies)} anomalies")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện OI divergence: {str(e)}")
            return []
    
    def detect_all_anomalies(self, symbol):
        """
        Phát hiện tất cả các loại bất thường cho một symbol - TỐI ƯU
        """
        try:
            logger.info(f"🔍 Phát hiện tất cả anomalies cho {symbol}")
            
            all_anomalies = []
            
            # 1. Anomalies 24h (ưu tiên cao)
            anomalies_24h = self.detect_24h_anomalies(symbol)
            all_anomalies.extend(anomalies_24h)
            
            # 2. Volume spikes (quan trọng)
            volume_spikes = self.detect_volume_spike_anomalies(symbol)
            all_anomalies.extend(volume_spikes)
            
            # 3. OI-Price divergence (quan trọng)
            oi_divergence = self.detect_oi_divergence_anomalies(symbol)
            all_anomalies.extend(oi_divergence)
            
            # 4. Correlation anomalies 24h
            correlation_24h = self.detect_oi_volume_correlation_anomalies(symbol, '24h')
            all_anomalies.extend(correlation_24h)
            
            # 5. Anomalies 30d (ưu tiên thấp hơn)
            anomalies_30d = self.detect_30d_anomalies(symbol)
            all_anomalies.extend(anomalies_30d)
            
            # 6. Correlation anomalies 30d
            correlation_30d = self.detect_oi_volume_correlation_anomalies(symbol, '30d')
            all_anomalies.extend(correlation_30d)
            
            # Lưu các anomalies vào database
            for anomaly in all_anomalies:
                self.db.save_anomaly(anomaly)
            
            # Log kết quả theo loại
            anomaly_types = {}
            for anomaly in all_anomalies:
                data_type = anomaly['data_type']
                if data_type not in anomaly_types:
                    anomaly_types[data_type] = 0
                anomaly_types[data_type] += 1
            
            logger.info(f"✅ Phát hiện {len(all_anomalies)} anomalies cho {symbol}")
            if anomaly_types:
                for data_type, count in anomaly_types.items():
                    logger.info(f"   - {data_type}: {count}")
            
            return all_anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện tất cả anomalies cho {symbol}: {str(e)}")
            return []
    
    def get_anomaly_summary(self, symbol=None, hours=24):
        """
        Lấy tóm tắt các anomalies gần đây
        """
        try:
            # Lấy anomalies từ database
            anomalies_df = self.db.get_anomalies(limit=100)
            
            if anomalies_df.empty:
                return {
                    'total_anomalies': 0,
                    'by_symbol': {},
                    'by_type': {},
                    'by_severity': {},
                    'recent_hours': hours
                }
            
            # Lọc theo thời gian
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_anomalies = anomalies_df[anomalies_df['timestamp'] >= cutoff_time]
            
            if symbol:
                recent_anomalies = recent_anomalies[recent_anomalies['symbol'] == symbol]
            
            # Tạo summary
            summary = {
                'total_anomalies': len(recent_anomalies),
                'by_symbol': recent_anomalies['symbol'].value_counts().to_dict(),
                'by_type': recent_anomalies['data_type'].value_counts().to_dict(),
                'by_severity': {},
                'recent_hours': hours,
                'timestamp': datetime.now().isoformat()
            }
            
            # Phân loại theo severity (nếu có)
            if 'severity' in recent_anomalies.columns:
                summary['by_severity'] = recent_anomalies['severity'].value_counts().to_dict()
            else:
                # Tạo severity dựa trên z_score
                if not recent_anomalies.empty:
                    high_severity = (recent_anomalies['z_score'] > self.threshold + 1).sum()
                    moderate_severity = len(recent_anomalies) - high_severity
                    summary['by_severity'] = {
                        'high': int(high_severity),
                        'moderate': int(moderate_severity)
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo anomaly summary: {str(e)}")
            return {
                'total_anomalies': 0,
                'by_symbol': {},
                'by_type': {},
                'by_severity': {},
                'recent_hours': hours,
                'error': str(e)
            }
    
    # Helper methods
    def _is_recent_anomaly(self, timestamp, hours=None, days=None):
        """
        Kiểm tra xem anomaly có trong khoảng thời gian gần đây không
        """
        try:
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            now = datetime.now()
            
            if hours:
                cutoff = now - timedelta(hours=hours)
            elif days:
                cutoff = now - timedelta(days=days)
            else:
                cutoff = now - timedelta(hours=24)  # Default 24h
            
            return timestamp >= cutoff
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra recent anomaly: {str(e)}")
            return True  # Default to include if uncertain
    
    def _merge_oi_volume_data(self, oi_df, klines_df):
        """
        Merge dữ liệu OI và Volume theo timestamp
        """
        try:
            # Chuẩn bị dữ liệu OI
            oi_data = oi_df[['timestamp', 'open_interest']].copy()
            oi_data['date'] = pd.to_datetime(oi_data['timestamp']).dt.date
            
            # Chuẩn bị dữ liệu Volume
            volume_data = klines_df[['open_time', 'volume']].copy()
            volume_data['date'] = pd.to_datetime(volume_data['open_time']).dt.date
            
            # Group by date và lấy giá trị trung bình
            oi_daily = oi_data.groupby('date')['open_interest'].mean().reset_index()
            volume_daily = volume_data.groupby('date')['volume'].sum().reset_index()  # Sum for volume
            
            # Merge
            merged = pd.merge(oi_daily, volume_daily, on='date', how='inner')
            merged['timestamp'] = pd.to_datetime(merged['date'])
            
            return merged
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi merge OI-Volume data: {str(e)}")
            return pd.DataFrame()

# Backward compatibility alias
AnomalyDetector = OptimizedAnomalyDetector