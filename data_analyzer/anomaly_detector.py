import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import ANOMALY_THRESHOLD, setup_logging
from data_analyzer.metrics import MarketMetrics

logger = setup_logging(__name__, 'anomaly_detector.log')

class AnomalyDetector:
    def __init__(self, db):
        self.db = db
        self.metrics = MarketMetrics()
        self.threshold = ANOMALY_THRESHOLD
        logger.info(f"Khởi tạo AnomalyDetector với ngưỡng {self.threshold}")
    
    def detect_volume_anomalies(self, symbol, timeframe='1h'):
        """Phát hiện bất thường trong dữ liệu volume"""
        try:
            # Lấy dữ liệu klines từ cơ sở dữ liệu
            df = self.db.get_klines(symbol, timeframe)
            if df.empty:
                logger.warning(f"Không có dữ liệu để phát hiện bất thường volume cho {symbol}")
                return []
            
            # Đảm bảo open_time là kiểu datetime
            if not pd.api.types.is_datetime64_any_dtype(df['open_time']):
                df['open_time'] = pd.to_datetime(df['open_time'])
                
            # Tính toán các metrics
            df = self.metrics.calculate_volume_metrics(df)
            if df is None:
                return []
            
            # Phát hiện các outliers
            outliers = self.metrics.detect_outliers(df, 'volume', threshold=self.threshold)
            
            # Chuyển đổi thành danh sách anomalies
            anomalies = []
            for _, row in outliers.iterrows():
                # Chỉ quan tâm đến các bất thường gần đây (trong vòng 24 giờ)
                if datetime.now() - pd.to_datetime(row['open_time']) <= timedelta(hours=24):
                    anomaly = {
                        'symbol': symbol,
                        'timestamp': row['open_time'],
                        'data_type': 'volume',
                        'value': row['volume'],
                        'z_score': row['z_score'],
                        'message': f"Phát hiện bất thường về Volume cho {symbol}: {row['volume']:.2f} (Z-score: {row['z_score']:.2f})"
                    }
                    anomalies.append(anomaly)
            
            logger.info(f"Đã phát hiện {len(anomalies)} bất thường Volume cho {symbol}")
            return anomalies
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện bất thường Volume: {str(e)}")
            return []
    
    def detect_oi_anomalies(self, symbol):
        """Phát hiện bất thường trong dữ liệu Open Interest"""
        try:
            # Lấy dữ liệu OI từ cơ sở dữ liệu
            df = self.db.get_open_interest(symbol)
            if df.empty:
                logger.warning(f"Không có dữ liệu để phát hiện bất thường OI cho {symbol}")
                return []
            
            # Đảm bảo timestamp là kiểu datetime
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
            # Tính toán các metrics
            df = self.metrics.calculate_oi_metrics(df)
            if df is None:
                return []
            
            # Phát hiện các outliers
            outliers = self.metrics.detect_outliers(df, 'open_interest', threshold=self.threshold)
            
            # Chuyển đổi thành danh sách anomalies
            anomalies = []
            for _, row in outliers.iterrows():
                # Chỉ quan tâm đến các bất thường gần đây (trong vòng 24 giờ)
                row_timestamp = pd.to_datetime(row['timestamp'])
                if datetime.now() - row_timestamp <= timedelta(hours=24):
                    anomaly = {
                        'symbol': symbol,
                        'timestamp': row_timestamp,
                        'data_type': 'open_interest',
                        'value': row['open_interest'],
                        'z_score': row['z_score'],
                        'message': f"Phát hiện bất thường về Open Interest cho {symbol}: {row['open_interest']:.2f} (Z-score: {row['z_score']:.2f})"
                    }
                    anomalies.append(anomaly)
            
            logger.info(f"Đã phát hiện {len(anomalies)} bất thường Open Interest cho {symbol}")
            return anomalies
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện bất thường Open Interest: {str(e)}")
            return []
    
    def detect_oi_volume_correlation_anomalies(self, symbol, timeframe='1h'):
        """Phát hiện bất thường trong tương quan giữa OI và price/volume"""
        try:
            # Lấy dữ liệu từ cơ sở dữ liệu
            price_df = self.db.get_klines(symbol, timeframe)
            oi_df = self.db.get_open_interest(symbol)
            
            if price_df.empty or oi_df.empty:
                logger.warning(f"Không có đủ dữ liệu để phát hiện bất thường tương quan cho {symbol}")
                return []
            
            # Đảm bảo kiểu dữ liệu datetime cho các cột thời gian
            if not pd.api.types.is_datetime64_any_dtype(price_df['open_time']):
                price_df['open_time'] = pd.to_datetime(price_df['open_time'])
                
            if not pd.api.types.is_datetime64_any_dtype(oi_df['timestamp']):
                oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'])
            
            # Tính toán tương quan
            correlation = self.metrics.calculate_correlation(price_df, oi_df)
            if correlation is None:
                return []
            
            # Chỉ phát hiện bất thường nếu tương quan âm mạnh
            anomalies = []
            if correlation['pearson_correlation'] < -0.7:
                anomaly = {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'data_type': 'correlation',
                    'value': correlation['pearson_correlation'],
                    'z_score': abs(correlation['pearson_correlation']) * 2,  # Giả lập Z-score
                    'message': f"Phát hiện tương quan âm mạnh giữa giá và Open Interest cho {symbol}: {correlation['pearson_correlation']:.2f}"
                }
                anomalies.append(anomaly)
                logger.info(f"Đã phát hiện bất thường tương quan cho {symbol}")
            
            return anomalies
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện bất thường tương quan: {str(e)}")
            return []
    
    def detect_all_anomalies(self, symbol):
        """Phát hiện tất cả các loại bất thường cho một symbol"""
        anomalies = []
        
        # Phát hiện bất thường volume
        volume_anomalies = self.detect_volume_anomalies(symbol)
        anomalies.extend(volume_anomalies)
        
        # Phát hiện bất thường Open Interest
        oi_anomalies = self.detect_oi_anomalies(symbol)
        anomalies.extend(oi_anomalies)
        
        # Phát hiện bất thường tương quan
        corr_anomalies = self.detect_oi_volume_correlation_anomalies(symbol)
        anomalies.extend(corr_anomalies)
        
        # Lưu các bất thường đã phát hiện vào cơ sở dữ liệu
        for anomaly in anomalies:
            self.db.save_anomaly(anomaly)
        
        logger.info(f"Tổng số bất thường đã phát hiện cho {symbol}: {len(anomalies)}")
        return anomalies