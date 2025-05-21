import pandas as pd
import numpy as np
from scipy import stats
from config.settings import setup_logging

logger = setup_logging(__name__, 'metrics.log')

class MarketMetrics:
    def __init__(self):
        logger.info("Khởi tạo MarketMetrics")
    
    def calculate_volume_metrics(self, df):
        """Tính toán các metrics cho Volume"""
        try:
            if df.empty:
                logger.warning("DataFrame rỗng, không thể tính toán metrics cho Volume")
                return None
            
            # Tính giá trị trung bình và độ lệch chuẩn của volume
            volume_mean = df['volume'].mean()
            volume_std = df['volume'].std()
            
            # Tính Z-score cho mỗi điểm dữ liệu
            df['volume_z_score'] = (df['volume'] - volume_mean) / volume_std if volume_std > 0 else 0
            
            # Tính giá trị phần trăm thay đổi
            df['volume_pct_change'] = df['volume'].pct_change() * 100
            
            # Tính giá trị moving average cho 5 và 20 kỳ
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            
            # Tính tỷ lệ volume hiện tại so với trung bình 20 kỳ
            df['volume_ratio_ma20'] = df['volume'] / df['volume_ma20']
            
            logger.info("Đã tính toán metrics cho Volume")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính toán metrics cho Volume: {str(e)}")
            return None
    
    def calculate_oi_metrics(self, df):
        """Tính toán các metrics cho Open Interest"""
        try:
            if df.empty:
                logger.warning("DataFrame rỗng, không thể tính toán metrics cho Open Interest")
                return None
            
            # Sắp xếp dữ liệu theo thời gian
            df = df.sort_values('timestamp')
            
            # Tính giá trị trung bình và độ lệch chuẩn của open interest
            oi_mean = df['open_interest'].mean()
            oi_std = df['open_interest'].std()
            
            # Tính Z-score cho mỗi điểm dữ liệu
            df['oi_z_score'] = (df['open_interest'] - oi_mean) / oi_std if oi_std > 0 else 0
            
            # Tính giá trị phần trăm thay đổi
            df['oi_pct_change'] = df['open_interest'].pct_change() * 100
            
            # Tính giá trị moving average cho 5 và 20 kỳ
            df['oi_ma5'] = df['open_interest'].rolling(window=5).mean()
            df['oi_ma20'] = df['open_interest'].rolling(window=20).mean()
            
            # Tính tỷ lệ OI hiện tại so với trung bình 20 kỳ
            df['oi_ratio_ma20'] = df['open_interest'] / df['oi_ma20']
            
            logger.info("Đã tính toán metrics cho Open Interest")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi tính toán metrics cho Open Interest: {str(e)}")
            return None
    
    def calculate_correlation(self, price_df, oi_df):
        """Tính toán tương quan giữa giá và Open Interest"""
        try:
            if price_df.empty or oi_df.empty:
                logger.warning("DataFrame rỗng, không thể tính toán tương quan")
                return None
            
            # Chuẩn bị dữ liệu
            price_data = price_df[['open_time', 'close']].copy()
            price_data.rename(columns={'open_time': 'timestamp'}, inplace=True)
            
            oi_data = oi_df[['timestamp', 'open_interest']].copy()
            
            # Hợp nhất dữ liệu dựa trên timestamp
            merged_data = pd.merge_asof(
                price_data.sort_values('timestamp'),
                oi_data.sort_values('timestamp'),
                on='timestamp',
                direction='nearest'
            )
            
            # Tính hệ số tương quan Pearson
            correlation = merged_data['close'].corr(merged_data['open_interest'])
            
            # Tính hệ số tương quan Spearman (thứ bậc)
            spearman_corr = merged_data['close'].corr(merged_data['open_interest'], method='spearman')
            
            result = {
                'pearson_correlation': correlation,
                'spearman_correlation': spearman_corr,
                'sample_size': len(merged_data)
            }
            
            logger.info(f"Đã tính toán tương quan: Pearson={correlation:.4f}, Spearman={spearman_corr:.4f}")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tính toán tương quan: {str(e)}")
            return None
    
    def detect_outliers(self, df, column, threshold=2.5):
        """Phát hiện các giá trị bất thường (outliers) trong một cột dữ liệu"""
        try:
            if df.empty:
                logger.warning(f"DataFrame rỗng, không thể phát hiện outliers cho cột {column}")
                return []
            
            # Tính Z-score cho cột dữ liệu
            z_scores = np.abs(stats.zscore(df[column].fillna(df[column].mean())))
            
            # Xác định các outliers dựa trên ngưỡng
            outliers_idx = np.where(z_scores > threshold)[0]
            
            # Lấy thông tin về các outliers
            outliers = df.iloc[outliers_idx].copy()
            outliers['z_score'] = z_scores[outliers_idx]
            
            logger.info(f"Đã phát hiện {len(outliers)} outliers cho cột {column}")
            return outliers
        except Exception as e:
            logger.error(f"Lỗi khi phát hiện outliers: {str(e)}")
            return []
    
    def calculate_market_sentiment(self, price_df, oi_df, volume_df):
        """Tính toán chỉ số sentiment dựa trên giá, OI và volume"""
        try:
            if price_df.empty or oi_df.empty or volume_df.empty:
                logger.warning("DataFrame rỗng, không thể tính toán sentiment")
                return None
            
            # Tính các chỉ số thay đổi
            price_change = price_df['close'].pct_change().iloc[-1] if len(price_df) > 1 else 0
            oi_change = oi_df['open_interest'].pct_change().iloc[-1] if len(oi_df) > 1 else 0
            volume_change = volume_df['volume'].pct_change().iloc[-1] if len(volume_df) > 1 else 0
            
            # Tính chỉ số sentiment (ví dụ đơn giản)
            # 1. Giá tăng + OI tăng + Volume tăng = Bullish mạnh
            # 2. Giá tăng + OI tăng + Volume giảm = Bullish trung bình
            # 3. Giá tăng + OI giảm = Bearish tiềm ẩn
            # 4. Giá giảm + OI tăng = Bearish mạnh
            # 5. Giá giảm + OI giảm = Thị trường không rõ ràng
            
            sentiment = 0  # Trung tính
            sentiment_label = "Neutral"
            
            if price_change > 0 and oi_change > 0:
                if volume_change > 0:
                    sentiment = 2  # Bullish mạnh
                    sentiment_label = "Strong Bullish"
                else:
                    sentiment = 1  # Bullish trung bình
                    sentiment_label = "Moderate Bullish"
            elif price_change > 0 and oi_change < 0:
                sentiment = -0.5  # Bearish tiềm ẩn
                sentiment_label = "Potential Bearish"
            elif price_change < 0 and oi_change > 0:
                sentiment = -2  # Bearish mạnh
                sentiment_label = "Strong Bearish"
            elif price_change < 0 and oi_change < 0:
                sentiment = -0.2  # Không rõ ràng, hơi nghiêng về bearish
                sentiment_label = "Unclear (Slight Bearish)"
            
            result = {
                'sentiment_score': sentiment,
                'sentiment_label': sentiment_label,
                'price_change': price_change,
                'oi_change': oi_change,
                'volume_change': volume_change
            }
            
            logger.info(f"Đã tính toán sentiment: {sentiment_label} ({sentiment:.2f})")
            return result
        except Exception as e:
            logger.error(f"Lỗi khi tính toán sentiment: {str(e)}")
            return None