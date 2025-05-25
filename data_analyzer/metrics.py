import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from config.settings import setup_logging

logger = setup_logging(__name__, 'metrics.log')

class OptimizedOIVolumeMetrics:
    """
    Lớp tối ưu cho việc tính toán metrics tập trung vào OI & Volume
    Focus: 24h tracking (hourly) + 30d tracking (daily)
    """
    
    def __init__(self):
        logger.info("🔧 Khởi tạo OptimizedOIVolumeMetrics - Focus OI & Volume")
    
    # Hàm tính toán metrics cho OI (hourly)
    def calculate_hourly_oi_metrics(self, df):
        """Tính toán các metrics OI theo giờ"""
        try:
            if df.empty:
                return self._get_empty_oi_metrics()
            
            # Lấy dữ liệu OI hiện tại và 24h trước
            current_oi = float(df['open_interest'].iloc[-1])
            previous_oi = float(df['open_interest'].iloc[0]) if len(df) > 1 else current_oi
            
            # Tính thay đổi
            oi_change_24h = ((current_oi - previous_oi) / previous_oi * 100) if previous_oi != 0 else 0
            
            # Tính các metrics khác
            max_oi = float(df['open_interest'].max())
            min_oi = float(df['open_interest'].min())
            avg_oi = float(df['open_interest'].mean())
            
            # Tính volatility (độ biến động)
            if len(df) > 1:
                std_oi = float(df['open_interest'].std())
                volatility = (std_oi / avg_oi * 100) if avg_oi != 0 else 0
            else:
                volatility = 0
            
            # Thêm log để debug
            logger.info(f"OI Data: current={current_oi:,.2f}, previous={previous_oi:,.2f}, change={oi_change_24h:.2f}%")
            
            return {
                'current_oi': current_oi,
                'previous_oi': previous_oi,
                'oi_change_24h': oi_change_24h,
                'max_oi': max_oi,
                'min_oi': min_oi,
                'avg_oi': avg_oi,
                'volatility': volatility,
                'data_points': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating OI metrics: {e}")
            return self._get_empty_oi_metrics()

    # Hàm tính toán metrics cho Volume (hourly)
    def calculate_hourly_volume_metrics(self, df):
        """Tính toán các metrics Volume theo giờ"""
        try:
            if df.empty:
                return self._get_empty_volume_metrics()
            
            # Lấy dữ liệu Volume hiện tại và 24h trước
            current_volume = float(df['volume'].iloc[-1])
            previous_volume = float(df['volume'].iloc[0]) if len(df) > 1 else current_volume
            
            # Tính thay đổi
            volume_change_24h = ((current_volume - previous_volume) / previous_volume * 100) if previous_volume != 0 else 0
            
            # Tính các metrics khác
            max_volume = float(df['volume'].max())
            min_volume = float(df['volume'].min())
            avg_volume = float(df['volume'].mean())
            
            # Tính volatility (độ biến động)
            if len(df) > 1:
                std_volume = float(df['volume'].std())
                volatility = (std_volume / avg_volume * 100) if avg_volume != 0 else 0
            else:
                volatility = 0
                
            # Thêm log để debug
            logger.info(f"Volume Data: current={current_volume:,.2f}, previous={previous_volume:,.2f}, change={volume_change_24h:.2f}%")
            
            return {
                'current_volume': current_volume,
                'previous_volume': previous_volume,
                'volume_change_24h': volume_change_24h,
                'max_volume': max_volume,
                'min_volume': min_volume,
                'avg_volume': avg_volume,
                'volatility': volatility,
                'data_points': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error calculating Volume metrics: {e}")
            return self._get_empty_volume_metrics()
    
    # ĐÃ SỬA: Cải thiện hàm tính metrics OI theo ngày
    def calculate_daily_oi_metrics(self, df, days=30):
        """
        Tính toán metrics OI theo ngày (30d focus) - ĐÃ SỬA
        """
        try:
            if df.empty or len(df) < 2:
                logger.warning("Không đủ dữ liệu để tính OI metrics hàng ngày")
                return self._get_empty_oi_metrics_30d()
            
            # Lấy dữ liệu gần nhất
            recent_df = df.tail(days) if len(df) > days else df
            recent_df = recent_df.copy()
            
            # ĐÃ SỬA: Kiểm tra cấu trúc dữ liệu
            # Sử dụng trường open_interest_value thay vì open_interest (trường có giá trị USDT)
            if 'open_interest_value' in recent_df.columns:
                oi_column = 'open_interest_value'
                avg_oi_column = 'avg_open_interest_value' if 'avg_open_interest_value' in recent_df.columns else 'open_interest_value'
            else:
                # Fallback cho cấu trúc cũ
                oi_column = 'sumOpenInterestValue' if 'sumOpenInterestValue' in recent_df.columns else 'open_interest'
                avg_oi_column = 'avgOpenInterestValue' if 'avgOpenInterestValue' in recent_df.columns else oi_column
            
            # Log cấu trúc dữ liệu
            logger.info(f"🔍 Cấu trúc dữ liệu OI: sử dụng cột {oi_column} và {avg_oi_column}")
            
            # Lấy giá trị hiện tại và trước đó
            current_oi = recent_df[oi_column].iloc[-1]
            first_oi = recent_df[oi_column].iloc[0]
            
            # Thay đổi 30d
            oi_change_30d = ((current_oi - first_oi) / first_oi) * 100 if first_oi > 0 else 0
            
            # Thay đổi 7d (nếu có đủ dữ liệu)
            if len(recent_df) >= 7:
                oi_7d_ago = recent_df[oi_column].iloc[-7] if len(recent_df) >= 7 else first_oi
                oi_change_7d = ((current_oi - oi_7d_ago) / oi_7d_ago) * 100 if oi_7d_ago > 0 else 0
            else:
                oi_change_7d = 0
            
            # Daily changes
            recent_df['oi_daily_change'] = recent_df[oi_column].pct_change() * 100
            
            # Volatility và trend
            oi_daily_volatility = recent_df['oi_daily_change'].std()
            positive_days = (recent_df['oi_daily_change'] > 0).sum()
            negative_days = (recent_df['oi_daily_change'] < 0).sum()
            total_days = len(recent_df) - 1
            
            trend_direction = 'bullish' if positive_days > negative_days else ('bearish' if negative_days > positive_days else 'neutral')
            
            # Moving averages
            if len(recent_df) >= 7:
                recent_df['oi_ma7d'] = recent_df[oi_column].rolling(window=7).mean()
                oi_above_ma7d = current_oi > recent_df['oi_ma7d'].iloc[-1]
            else:
                oi_above_ma7d = None
            
            if len(recent_df) >= 14:
                recent_df['oi_ma14d'] = recent_df[oi_column].rolling(window=14).mean()
                oi_above_ma14d = current_oi > recent_df['oi_ma14d'].iloc[-1]
            else:
                oi_above_ma14d = None
            
            # Extremes
            max_oi = recent_df[oi_column].max()
            min_oi = recent_df[oi_column].min()
            avg_oi_30d = recent_df[avg_oi_column].mean()
            
            metrics = {
                'current_oi': current_oi,
                'avg_oi_30d': round(avg_oi_30d, 2),
                'oi_change_30d': round(oi_change_30d, 4),
                'oi_change_7d': round(oi_change_7d, 4),
                'oi_daily_volatility': round(oi_daily_volatility, 4),
                'trend_direction': trend_direction,
                'positive_days': int(positive_days),
                'negative_days': int(negative_days),
                'oi_above_ma7d': oi_above_ma7d,
                'oi_above_ma14d': oi_above_ma14d,
                'max_oi_30d': max_oi,
                'min_oi_30d': min_oi,
                'oi_range_30d_pct': round(((max_oi - min_oi) / min_oi) * 100, 2) if min_oi > 0 else 0,
                'total_data_points': len(recent_df)
            }
            
            # Log kết quả
            logger.info(f"✅ Tính toán OI metrics 30d: {trend_direction} {oi_change_30d:.2f}%, giá trị hiện tại = {current_oi:,.2f} USDT")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính OI metrics hàng ngày: {str(e)}")
            return self._get_empty_oi_metrics_30d()
    
    # ĐÃ SỬA: Cải thiện hàm tính metrics Volume theo ngày
    def calculate_daily_volume_metrics(self, df, days=30):
        """
        Tính toán metrics Volume theo ngày (30d focus) - ĐÃ SỬA
        """
        try:
            if df.empty or len(df) < 2:
                logger.warning("Không đủ dữ liệu để tính Volume metrics hàng ngày")
                return self._get_empty_volume_metrics_30d()
            
            # Lấy dữ liệu gần nhất
            recent_df = df.tail(days) if len(df) > days else df
            recent_df = recent_df.copy()
            
            # ĐÃ SỬA: Kiểm tra cấu trúc dữ liệu
            # Sử dụng trường quote_volume thay vì volume để đảm bảo lấy giá trị theo USDT
            if 'quote_volume' in recent_df.columns:
                volume_column = 'quote_volume'
            else:
                # Fallback cho cấu trúc cũ
                volume_column = 'volume'
            
            # Log cấu trúc dữ liệu
            logger.info(f"🔍 Cấu trúc dữ liệu Volume: sử dụng cột {volume_column}")
            
            current_volume = recent_df[volume_column].iloc[-1]
            first_volume = recent_df[volume_column].iloc[0]
            
            # Thay đổi 30d
            volume_change_30d = ((current_volume - first_volume) / first_volume) * 100 if first_volume > 0 else 0
            
            # Thay đổi 7d
            if len(recent_df) >= 7:
                volume_7d_ago = recent_df[volume_column].iloc[-7]
                volume_change_7d = ((current_volume - volume_7d_ago) / volume_7d_ago) * 100 if volume_7d_ago > 0 else 0
            else:
                volume_change_7d = 0
            
            # Daily changes
            recent_df['volume_daily_change'] = recent_df[volume_column].pct_change() * 100
            
            # Volume metrics đặc biệt cho 30d
            total_volume_30d = recent_df[volume_column].sum()
            avg_volume_30d = recent_df[volume_column].mean()
            volume_daily_volatility = recent_df['volume_daily_change'].std()
            
            # Trend analysis
            positive_days = (recent_df['volume_daily_change'] > 0).sum()
            negative_days = (recent_df['volume_daily_change'] < 0).sum()
            total_days = len(recent_df) - 1
            
            trend_direction = 'increasing' if positive_days > negative_days else ('decreasing' if negative_days > positive_days else 'stable')
            
            # Volume distribution
            volume_std = recent_df[volume_column].std()
            volume_cv = (volume_std / avg_volume_30d) if avg_volume_30d > 0 else 0  # Coefficient of variation
            
            # High volume days
            high_volume_threshold = avg_volume_30d + volume_std
            high_volume_days = (recent_df[volume_column] > high_volume_threshold).sum()
            
            # Moving averages
            if len(recent_df) >= 7:
                recent_df['volume_ma7d'] = recent_df[volume_column].rolling(window=7).mean()
                volume_above_ma7d = current_volume > recent_df['volume_ma7d'].iloc[-1]
            else:
                volume_above_ma7d = None
            
            metrics = {
                'current_volume': current_volume,
                'avg_volume_30d': round(avg_volume_30d, 2),
                'total_volume_30d': total_volume_30d,
                'volume_change_30d': round(volume_change_30d, 4),
                'volume_change_7d': round(volume_change_7d, 4),
                'volume_daily_volatility': round(volume_daily_volatility, 4),
                'trend_direction': trend_direction,
                'positive_days': int(positive_days),
                'negative_days': int(negative_days),
                'volume_above_ma7d': volume_above_ma7d,
                'high_volume_days': int(high_volume_days),
                'volume_cv': round(volume_cv, 4),
                'max_volume_30d': recent_df[volume_column].max(),
                'min_volume_30d': recent_df[volume_column].min(),
                'total_data_points': len(recent_df)
            }
            
            # Log kết quả
            logger.info(f"✅ Tính toán Volume metrics 30d: {trend_direction} {volume_change_30d:.2f}%, giá trị hiện tại = {current_volume:,.2f} USDT")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính Volume metrics hàng ngày: {str(e)}")
            return self._get_empty_volume_metrics_30d()
    
    # ĐÃ SỬA: Cải thiện hàm tính tương quan OI-Volume
    def calculate_oi_volume_correlation(self, df, period='24h'):
        """
        Tính toán tương quan giữa OI và Volume - ĐÃ SỬA
        """
        try:
            if df.empty or len(df) < 3:
                return {
                    'correlation': 0,
                    'correlation_strength': 'no_data',
                    'sample_size': 0
                }
            
            # ĐÃ SỬA: Chọn cột phù hợp dựa trên cấu trúc dữ liệu thực tế
            if period == '24h':
                # Dữ liệu 24h
                if 'open_interest' in df.columns and 'volume' in df.columns:
                    oi_col = 'open_interest'
                    vol_col = 'volume'
                else:
                    logger.error("Không tìm thấy cấu trúc dữ liệu OI-Volume 24h phù hợp")
                    return {
                        'correlation': 0,
                        'correlation_strength': 'error',
                        'sample_size': 0
                    }
            else:
                # Dữ liệu 30d - ĐÃ SỬA để phù hợp với cấu trúc mới
                oi_col = None
                vol_col = None
                
                # Kiểm tra các trường OI
                for possible_oi in ['open_interest_value', 'avg_open_interest_value', 'sumOpenInterestValue']:
                    if possible_oi in df.columns:
                        oi_col = possible_oi
                        break
                
                # Kiểm tra các trường Volume
                for possible_vol in ['quote_volume', 'total_volume', 'volume']:
                    if possible_vol in df.columns:
                        vol_col = possible_vol
                        break
                
                if oi_col is None or vol_col is None:
                    logger.error("Không tìm thấy cấu trúc dữ liệu OI-Volume 30d phù hợp")
                    return {
                        'correlation': 0,
                        'correlation_strength': 'error',
                        'sample_size': 0
                    }
            
            # Log để debug
            logger.info(f"📊 Tính correlation giữa {oi_col} và {vol_col} cho period {period}")
            
            # Tính correlation
            correlation = df[oi_col].corr(df[vol_col])
            
            if pd.isna(correlation):
                correlation = 0
            
            # Phân loại mức độ tương quan
            if abs(correlation) >= 0.7:
                strength = 'strong'
            elif abs(correlation) >= 0.4:
                strength = 'moderate'
            elif abs(correlation) >= 0.2:
                strength = 'weak'
            else:
                strength = 'negligible'
            
            # Thêm hướng
            if correlation > 0:
                direction = 'positive'
            elif correlation < 0:
                direction = 'negative'
            else:
                direction = 'neutral'
            
            result = {
                'correlation': round(correlation, 4),
                'correlation_strength': f"{strength}_{direction}",
                'sample_size': len(df),
                'interpretation': self._interpret_correlation(correlation)
            }
            
            logger.info(f"📊 OI-Volume correlation ({period}): {correlation:.3f} ({strength})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính correlation OI-Volume: {str(e)}")
            return {
                'correlation': 0,
                'correlation_strength': 'error',
                'sample_size': 0,
                'interpretation': 'Không thể tính toán'
            }
    
    # ĐÃ SỬA: Cải thiện hàm phát hiện bất thường
    def detect_oi_volume_anomalies(self, df, threshold=2.5):
        """
        Phát hiện bất thường cho OI và Volume - ĐÃ SỬA
        """
        try:
            anomalies = []
            
            if df.empty or len(df) < 10:
                return anomalies
            
            # ĐÃ SỬA: Tự động xác định cấu trúc dữ liệu
            # Liệt kê các cột cần kiểm tra theo độ ưu tiên
            oi_columns = [
                ('open_interest_value', 'OI_Value'),
                ('open_interest', 'OI'),
                ('sumOpenInterestValue', 'OI_Value'),
                ('sumOpenInterest', 'OI'),
                ('avg_open_interest_value', 'Avg_OI_Value')
            ]
            
            volume_columns = [
                ('quote_volume', 'Volume_USDT'),
                ('volume', 'Volume'),
                ('total_volume', 'Total_Volume')
            ]
            
            # Xác định cột OI khả dụng
            available_oi_cols = []
            for col, name in oi_columns:
                if col in df.columns:
                    available_oi_cols.append((col, name))
            
            # Xác định cột Volume khả dụng
            available_vol_cols = []
            for col, name in volume_columns:
                if col in df.columns:
                    available_vol_cols.append((col, name))
            
            # Kết hợp cả hai danh sách
            columns_to_check = available_oi_cols + available_vol_cols
            
            if not columns_to_check:
                logger.warning("Không tìm thấy cột OI hoặc Volume phù hợp để phát hiện bất thường")
                return anomalies
            
            # Log cấu trúc dữ liệu
            col_names = [name for _, name in columns_to_check]
            logger.info(f"🔍 Kiểm tra bất thường cho các chỉ số: {', '.join(col_names)}")
            
            for col, name in columns_to_check:
                # Tính Z-score
                mean_val = df[col].mean()
                std_val = df[col].std()
                
                if std_val > 0:
                    z_scores = np.abs((df[col] - mean_val) / std_val)
                    anomaly_mask = z_scores > threshold
                    
                    if anomaly_mask.any():
                        anomaly_indices = df[anomaly_mask].index
                        for idx in anomaly_indices:
                            # Xác định trường timestamp phù hợp
                            timestamp_field = None
                            for possible_field in ['timestamp', 'hour_timestamp', 'date_timestamp', 'date']:
                                if possible_field in df.columns:
                                    timestamp_field = possible_field
                                    break
                            
                            if timestamp_field is None:
                                timestamp = idx
                            else:
                                timestamp = df.loc[idx, timestamp_field]
                            
                            anomalies.append({
                                'timestamp': timestamp,
                                'metric': name,
                                'value': df.loc[idx, col],
                                'z_score': z_scores.loc[idx],
                                'threshold': threshold,
                                'severity': 'high' if z_scores.loc[idx] > threshold + 1 else 'moderate'
                            })
            
            logger.info(f"🚨 Phát hiện {len(anomalies)} anomalies với threshold {threshold}")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện anomalies: {str(e)}")
            return []
    
    def generate_summary_metrics(self, oi_metrics_24h, volume_metrics_24h, oi_metrics_30d, volume_metrics_30d):
        """
        Tạo metrics tổng hợp
        """
        try:
            summary = {
                'timestamp': datetime.now().isoformat(),
                '24h_summary': {
                    'oi_trend': oi_metrics_24h.get('trend_direction', 'neutral'),
                    'oi_change': oi_metrics_24h.get('oi_change_24h', 0),
                    'volume_trend': volume_metrics_24h.get('trend_direction', 'stable'),
                    'volume_change': volume_metrics_24h.get('volume_change_24h', 0),
                    'overall_sentiment': self._determine_sentiment_24h(oi_metrics_24h, volume_metrics_24h)
                },
                '30d_summary': {
                    'oi_trend': oi_metrics_30d.get('trend_direction', 'neutral'),
                    'oi_change': oi_metrics_30d.get('oi_change_30d', 0),
                    'volume_trend': volume_metrics_30d.get('trend_direction', 'stable'),
                    'volume_change': volume_metrics_30d.get('volume_change_30d', 0),
                    'overall_sentiment': self._determine_sentiment_30d(oi_metrics_30d, volume_metrics_30d)
                },
                'data_quality': {
                    'oi_24h_points': oi_metrics_24h.get('total_data_points', 0),
                    'volume_24h_points': volume_metrics_24h.get('total_data_points', 0),
                    'oi_30d_points': oi_metrics_30d.get('total_data_points', 0),
                    'volume_30d_points': volume_metrics_30d.get('total_data_points', 0)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tạo summary metrics: {str(e)}")
            return {}
    
    # Helper methods
    def _get_empty_oi_metrics(self):
        return {
            'current_oi': 0,
            'oi_change_24h': 0,
            'oi_volatility': 0,
            'trend_direction': 'neutral',
            'trend_strength': 0,
            'positive_hours': 0,
            'negative_hours': 0,
            'oi_above_ma6h': None,
            'oi_range_24h_pct': 0,
            'support_level': 0,
            'resistance_level': 0,
            'max_oi_24h': 0,
            'min_oi_24h': 0,
            'total_data_points': 0
        }
    
    def _get_empty_volume_metrics(self):
        return {
            'current_volume': 0,
            'volume_change_24h': 0,
            'total_volume_24h': 0,
            'avg_volume_24h': 0,
            'volume_volatility': 0,
            'trend_direction': 'stable',
            'volume_spikes': 0,
            'volume_concentration': 0,
            'volume_above_ma6h': None,
            'max_volume_24h': 0,
            'min_volume_24h': 0,
            'positive_hours': 0,
            'negative_hours': 0,
            'total_data_points': 0
        }
    
    def _get_empty_oi_metrics_30d(self):
        return {
            'current_oi': 0,
            'avg_oi_30d': 0,
            'oi_change_30d': 0,
            'oi_change_7d': 0,
            'oi_daily_volatility': 0,
            'trend_direction': 'neutral',
            'positive_days': 0,
            'negative_days': 0,
            'oi_above_ma7d': None,
            'oi_above_ma14d': None,
            'max_oi_30d': 0,
            'min_oi_30d': 0,
            'oi_range_30d_pct': 0,
            'total_data_points': 0
        }
    
    def _get_empty_volume_metrics_30d(self):
        return {
            'current_volume': 0,
            'avg_volume_30d': 0,
            'total_volume_30d': 0,
            'volume_change_30d': 0,
            'volume_change_7d': 0,
            'volume_daily_volatility': 0,
            'trend_direction': 'stable',
            'positive_days': 0,
            'negative_days': 0,
            'volume_above_ma7d': None,
            'high_volume_days': 0,
            'volume_cv': 0,
            'max_volume_30d': 0,
            'min_volume_30d': 0,
            'total_data_points': 0
        }
    
    def _interpret_correlation(self, correlation):
        if abs(correlation) >= 0.7:
            return "Tương quan mạnh - OI và Volume di chuyển cùng hướng rõ rệt"
        elif abs(correlation) >= 0.4:
            return "Tương quan trung bình - Có mối liên hệ đáng chú ý"
        elif abs(correlation) >= 0.2:
            return "Tương quan yếu - Mối liên hệ không rõ ràng"
        else:
            return "Không có tương quan - OI và Volume di chuyển độc lập"
    
    def _determine_sentiment_24h(self, oi_metrics, volume_metrics):
        oi_change = oi_metrics.get('oi_change_24h', 0)
        volume_change = volume_metrics.get('volume_change_24h', 0)
        
        if oi_change > 5 and volume_change > 20:
            return 'strong_bullish'
        elif oi_change > 1 and volume_change > 5:
            return 'bullish'
        elif oi_change < -5 and volume_change < -20:
            return 'strong_bearish'
        elif oi_change < -1 and volume_change < -5:
            return 'bearish'
        else:
            return 'neutral'
    
    def _determine_sentiment_30d(self, oi_metrics, volume_metrics):
        oi_change = oi_metrics.get('oi_change_30d', 0)
        volume_change = volume_metrics.get('volume_change_30d', 0)
        
        if oi_change > 20 and volume_change > 50:
            return 'strong_bullish'
        elif oi_change > 5 and volume_change > 15:
            return 'bullish'
        elif oi_change < -20 and volume_change < -50:
            return 'strong_bearish'
        elif oi_change < -5 and volume_change < -15:
            return 'bearish'
        else:
            return 'neutral'