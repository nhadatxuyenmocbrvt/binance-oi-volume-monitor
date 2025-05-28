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
        """Tính toán các metrics OI theo giờ - LUÔN DÙNG GIÁ TRỊ USDT"""
        try:
            if df.empty:
                return self._get_empty_oi_metrics()

            # Xác định cột OI value (USDT) phù hợp
            oi_column = None
            for col in ['open_interest_value', 'openInterestValue', 'open_interest']:
                if col in df.columns:
                    oi_column = col
                    break

            if not oi_column:
                logger.warning("Không tìm thấy cột Open Interest Value phù hợp")
                return self._get_empty_oi_metrics()
                
            # Kiểm tra nếu cột không phải là giá trị USDT
            if oi_column == 'open_interest' and 'price' in df.columns:
                logger.warning("Phải chuyển đổi open_interest sang giá trị USDT")
                df = df.copy()
                df['open_interest_value'] = df['open_interest'] * df['price']
                oi_column = 'open_interest_value'
            
            logger.info(f"Tính OI metrics dùng cột: {oi_column}")
            
            # Lấy dữ liệu OI hiện tại và 24h trước
            current_oi = float(df[oi_column].iloc[-1])
            previous_oi = float(df[oi_column].iloc[0]) if len(df) > 1 else current_oi
            
            # Tính thay đổi
            oi_change_24h = ((current_oi - previous_oi) / previous_oi * 100) if previous_oi != 0 else 0
            
            # Tính các metrics khác
            max_oi = float(df[oi_column].max())
            min_oi = float(df[oi_column].min())
            avg_oi = float(df[oi_column].mean())
            
            # Tính volatility (độ biến động)
            if len(df) > 1:
                std_oi = float(df[oi_column].std())
                volatility = (std_oi / avg_oi * 100) if avg_oi != 0 else 0
            else:
                volatility = 0
            
            # Thêm log để debug
            logger.info(f"OI Value Data (USDT): current={current_oi:,.2f}, previous={previous_oi:,.2f}, change={oi_change_24h:.2f}%")
            
            return {
                'current_oi': current_oi,
                'previous_oi': previous_oi,
                'oi_change_24h': oi_change_24h,
                'max_oi': max_oi,
                'min_oi': min_oi,
                'avg_oi': avg_oi,
                'volatility': volatility,
                'data_points': len(df),
                'unit': 'USDT'  # Đánh dấu rõ đơn vị
            }
            
        except Exception as e:
            logger.error(f"Error calculating OI metrics: {e}")
            return self._get_empty_oi_metrics()

    def calculate_hourly_volume_metrics(self, df):
        """Tính toán các metrics Volume theo giờ - LUÔN DÙNG QUOTE_VOLUME (USDT)"""
        try:
            if df.empty:
                return self._get_empty_volume_metrics()
            
            # Xác định cột Volume value (USDT) phù hợp
            volume_column = None
            for col in ['quote_volume', 'quoteVolume', 'volume']:
                if col in df.columns:
                    volume_column = col
                    break
                    
            if not volume_column:
                logger.warning("Không tìm thấy cột Volume phù hợp")
                return self._get_empty_volume_metrics()
            
            # Kiểm tra nếu cột không phải là giá trị USDT
            if volume_column == 'volume' and 'price' in df.columns:
                logger.warning("Phải chuyển đổi volume sang giá trị USDT")
                df = df.copy()
                df['quote_volume'] = df['volume'] * df['price']
                volume_column = 'quote_volume'
                
            logger.info(f"Tính Volume metrics dùng cột: {volume_column}")
            
            # Lấy dữ liệu Volume hiện tại và 24h trước
            current_volume = float(df[volume_column].iloc[-1])
            previous_volume = float(df[volume_column].iloc[0]) if len(df) > 1 else current_volume
            
            # Tính thay đổi
            volume_change_24h = ((current_volume - previous_volume) / previous_volume * 100) if previous_volume != 0 else 0
            
            # Tính các metrics khác
            max_volume = float(df[volume_column].max())
            min_volume = float(df[volume_column].min())
            avg_volume = float(df[volume_column].mean())
            
            # Tính volatility (độ biến động)
            if len(df) > 1:
                std_volume = float(df[volume_column].std())
                volatility = (std_volume / avg_volume * 100) if avg_volume != 0 else 0
            else:
                volatility = 0
                
            # Thêm log để debug
            logger.info(f"Volume Data (USDT): current={current_volume:,.2f}, previous={previous_volume:,.2f}, change={volume_change_24h:.2f}%")
            
            return {
                'current_volume': current_volume,
                'previous_volume': previous_volume,
                'volume_change_24h': volume_change_24h,
                'max_volume': max_volume,
                'min_volume': min_volume,
                'avg_volume': avg_volume,
                'volatility': volatility,
                'data_points': len(df),
                'unit': 'USDT'  # Đánh dấu rõ đơn vị
            }
            
        except Exception as e:
            logger.error(f"Error calculating Volume metrics: {e}")
            return self._get_empty_volume_metrics()
    
    # ĐÃ SỬA: Cải thiện hàm tính metrics OI theo ngày
    def calculate_daily_oi_metrics(self, df, days=30):
        """
        Tính toán metrics OI theo ngày (30d focus) - ĐÃ SỬA ĐỂ LUÔN DÙNG USDT VALUE
        """
        try:
            if df.empty or len(df) < 2:
                logger.warning("Không đủ dữ liệu để tính OI metrics hàng ngày")
                return self._get_empty_oi_metrics_30d()
            
            # Lấy dữ liệu gần nhất
            recent_df = df.tail(days) if len(df) > days else df
            recent_df = recent_df.copy()
            
            # ĐÃ SỬA: Luôn sử dụng giá trị USDT, thêm logic để tìm cột phù hợp
            oi_column = None
            avg_oi_column = None
            
            # Danh sách ưu tiên cho cột OI (giá trị USDT)
            oi_columns_priority = [
                'open_interest_value',
                'sumOpenInterestValue',
                'openInterestValue'
            ]
            
            # Danh sách ưu tiên cho cột Average OI (giá trị USDT)
            avg_oi_columns_priority = [
                'avg_open_interest_value',
                'avgOpenInterestValue',
                'avgOpenInterest_value'
            ]
            
            # Tìm cột OI theo độ ưu tiên
            for col in oi_columns_priority:
                if col in recent_df.columns:
                    oi_column = col
                    break
            
            # Nếu không tìm thấy, kiểm tra xem có cột open_interest không
            if oi_column is None:
                if 'open_interest' in recent_df.columns and 'price' in recent_df.columns:
                    # Cần tính OI value từ OI * price
                    logger.warning("Không tìm thấy cột OI Value, đang tính toán từ OI * price")
                    recent_df['calculated_oi_value'] = recent_df['open_interest'] * recent_df['price']
                    oi_column = 'calculated_oi_value'
                else:
                    logger.error("Không tìm được cột phù hợp cho OI Value")
                    return self._get_empty_oi_metrics_30d()
            
            # Tìm cột Average OI theo độ ưu tiên
            for col in avg_oi_columns_priority:
                if col in recent_df.columns:
                    avg_oi_column = col
                    break
            
            # Nếu không tìm thấy, sử dụng cột OI
            if avg_oi_column is None:
                avg_oi_column = oi_column
            
            # Log cấu trúc dữ liệu
            logger.info(f"🔍 Cấu trúc dữ liệu OI: sử dụng cột {oi_column} và {avg_oi_column} (luôn theo USDT)")
            
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
            
            # ĐÃ SỬA: Dựa trên số ngày thay đổi tích cực/tiêu cực và % thay đổi
            if positive_days > negative_days and oi_change_30d > 0:
                trend_direction = 'bullish'
            elif negative_days > positive_days and oi_change_30d < 0:
                trend_direction = 'bearish'
            else:
                trend_direction = 'neutral'
            
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
                'total_data_points': len(recent_df),
                # ĐÃ THÊM: Đánh dấu rõ đơn vị
                'unit': 'USDT',
                'used_columns': {'oi': oi_column, 'avg_oi': avg_oi_column}
            }
            
            # Log kết quả
            logger.info(f"✅ Tính toán OI metrics 30d: {trend_direction} {oi_change_30d:.2f}%, giá trị hiện tại = {current_oi:,.2f} USDT")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính OI metrics hàng ngày: {str(e)}")
            return self._get_empty_oi_metrics_30d()

    def calculate_daily_volume_metrics(self, df, days=30):
        """
        Tính toán metrics Volume theo ngày (30d focus) - ĐÃ SỬA ĐỂ LUÔN DÙNG QUOTE_VOLUME (USDT)
        """
        try:
            if df.empty or len(df) < 2:
                logger.warning("Không đủ dữ liệu để tính Volume metrics hàng ngày")
                return self._get_empty_volume_metrics_30d()
            
            # Lấy dữ liệu gần nhất
            recent_df = df.tail(days) if len(df) > days else df
            recent_df = recent_df.copy()
            
            # ĐÃ SỬA: Luôn sử dụng giá trị USDT, thêm logic để tìm cột phù hợp
            volume_column = None
            
            # Danh sách ưu tiên cho cột Volume (giá trị USDT)
            volume_columns_priority = [
                'quote_volume',
                'quoteVolume',
                'total_volume'
            ]
            
            # Tìm cột Volume theo độ ưu tiên
            for col in volume_columns_priority:
                if col in recent_df.columns:
                    volume_column = col
                    break
            
            # Nếu không tìm thấy, kiểm tra xem có cột volume không
            if volume_column is None:
                if 'volume' in recent_df.columns and 'price' in recent_df.columns:
                    # Cần tính Volume value từ volume * price
                    logger.warning("Không tìm thấy cột Quote Volume, đang tính toán từ volume * price")
                    recent_df['calculated_quote_volume'] = recent_df['volume'] * recent_df['price']
                    volume_column = 'calculated_quote_volume'
                elif 'volume' in recent_df.columns:
                    # Không lý tưởng, nhưng nếu không có cách nào khác
                    logger.warning("Sử dụng cột volume làm fallback - có thể không phản ánh chính xác giá trị USDT")
                    volume_column = 'volume'
                else:
                    logger.error("Không tìm được cột phù hợp cho Volume")
                    return self._get_empty_volume_metrics_30d()
            
            # Log cấu trúc dữ liệu
            logger.info(f"🔍 Cấu trúc dữ liệu Volume: sử dụng cột {volume_column} (theo USDT)")
            
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
            
            # ĐÃ SỬA: Xác định trend direction dựa trên số ngày thay đổi tích cực/tiêu cực và % thay đổi
            if positive_days > negative_days and volume_change_30d > 0:
                trend_direction = 'increasing'
            elif negative_days > positive_days and volume_change_30d < 0:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
            
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
                'total_data_points': len(recent_df),
                # ĐÃ THÊM: Đánh dấu rõ đơn vị
                'unit': 'USDT',
                'used_column': volume_column
            }
            
            # Log kết quả
            logger.info(f"✅ Tính toán Volume metrics 30d: {trend_direction} {volume_change_30d:.2f}%, giá trị hiện tại = {current_volume:,.2f} USDT")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính Volume metrics hàng ngày: {str(e)}")
            return self._get_empty_volume_metrics_30d()
       
    def calculate_oi_volume_correlation(self, df, period='24h'):
        """
        Tính toán tương quan giữa OI và Volume - ĐẢM BẢO DÙNG GIÁ TRỊ USDT
        """
        try:
            if df.empty or len(df) < 3:
                return {
                    'correlation': 0,
                    'correlation_strength': 'no_data',
                    'sample_size': 0,
                    'interpretation': 'Không đủ dữ liệu'
                }
            
            # Xác định cột phù hợp dựa trên cấu trúc dữ liệu thực tế
            oi_col = None
            vol_col = None
            
            # Kiểm tra các trường OI - ưu tiên giá trị USDT
            for possible_oi in ['open_interest_value', 'avg_open_interest_value', 'openInterestValue', 'open_interest']:
                if possible_oi in df.columns and df[possible_oi].notna().any() and (df[possible_oi] > 0).any():
                    oi_col = possible_oi
                    break
            
            # Kiểm tra các trường Volume - ưu tiên giá trị USDT
            for possible_vol in ['quote_volume', 'quoteVolume', 'volume']:
                if possible_vol in df.columns and df[possible_vol].notna().any() and (df[possible_vol] > 0).any():
                    vol_col = possible_vol
                    break
            
            if oi_col is None or vol_col is None:
                logger.error("Không tìm thấy cấu trúc dữ liệu OI-Volume phù hợp")
                return {
                    'correlation': 0,
                    'correlation_strength': 'error',
                    'sample_size': 0,
                    'interpretation': 'Dữ liệu không hợp lệ'
                }
            
            # Đảm bảo dùng giá trị USDT
            if oi_col == 'open_interest' and 'price' in df.columns:
                logger.info(f"Chuyển đổi {oi_col} sang giá trị USDT")
                df = df.copy()
                df['open_interest_value'] = df['open_interest'] * df['price']
                oi_col = 'open_interest_value'
                
            if vol_col == 'volume' and 'price' in df.columns:
                logger.info(f"Chuyển đổi {vol_col} sang giá trị USDT")
                df = df.copy()
                df['quote_volume'] = df['volume'] * df['price']
                vol_col = 'quote_volume'
            
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
            
            logger.info(f"📊 OI-Volume correlation ({period}): {correlation:.3f} ({strength}_{direction})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi tính correlation OI-Volume: {str(e)}")
            return {
                'correlation': 0,
                'correlation_strength': 'error',
                'sample_size': 0,
                'interpretation': 'Không thể tính toán'
            }
    
    def detect_oi_volume_anomalies(self, df, threshold=2.5, dedup_window_minutes=30):
        """
        Phát hiện bất thường cho OI và Volume - ĐẢM BẢO DÙNG GIÁ TRỊ USDT
        
        Args:
            df: DataFrame chứa dữ liệu
            threshold: Ngưỡng Z-score để coi là bất thường
            dedup_window_minutes: Cửa sổ thời gian (phút) để tránh lặp lại cảnh báo
        """
        try:
            anomalies = []
            
            if df.empty or len(df) < 10:
                return anomalies
            
            # Tự động xác định cấu trúc dữ liệu - ưu tiên giá trị USDT
            # Liệt kê các cột OI cần kiểm tra theo độ ưu tiên
            oi_columns = [
                ('open_interest_value', 'OI_Value_USDT'),
                ('openInterestValue', 'OI_Value_USDT'),
                ('avg_open_interest_value', 'Avg_OI_Value_USDT'),
                ('open_interest', 'OI')  # Fallback nếu không có lựa chọn nào khác
            ]
            
            # Liệt kê các cột Volume cần kiểm tra theo độ ưu tiên
            volume_columns = [
                ('quote_volume', 'Volume_USDT'),
                ('quoteVolume', 'Volume_USDT'),
                ('volume', 'Volume')  # Fallback nếu không có lựa chọn nào khác
            ]
            
            # Xác định cột OI khả dụng
            available_oi_cols = []
            for col, name in oi_columns:
                if col in df.columns and df[col].notna().any() and (df[col] > 0).any():
                    available_oi_cols.append((col, name))
                    # Nếu tìm thấy cột ưu tiên cao (USDT), dừng tìm kiếm
                    if 'value' in col.lower() or 'usdt' in name.lower():
                        break
            
            # Xác định cột Volume khả dụng
            available_vol_cols = []
            for col, name in volume_columns:
                if col in df.columns and df[col].notna().any() and (df[col] > 0).any():
                    available_vol_cols.append((col, name))
                    # Nếu tìm thấy cột ưu tiên cao (USDT), dừng tìm kiếm
                    if 'quote' in col.lower() or 'usdt' in name.lower():
                        break
            
            # Kết hợp cả hai danh sách
            columns_to_check = available_oi_cols + available_vol_cols
            
            # Cần chuyển đổi giá trị non-USDT sang USDT nếu cần
            df_check = df.copy()
            
            # Xử lý cột OI nếu không phải giá trị USDT
            if available_oi_cols and 'open_interest' in available_oi_cols[0][0] and 'value' not in available_oi_cols[0][0].lower() and 'price' in df.columns:
                oi_col = available_oi_cols[0][0]
                logger.info(f"Chuyển đổi {oi_col} sang giá trị USDT")
                df_check['open_interest_value_calculated'] = df[oi_col] * df['price']
                columns_to_check = [(c, n) if c != oi_col else ('open_interest_value_calculated', 'OI_Value_USDT') for c, n in columns_to_check]
                
            # Xử lý cột Volume nếu không phải giá trị USDT
            if available_vol_cols and 'volume' == available_vol_cols[0][0] and 'price' in df.columns:
                vol_col = available_vol_cols[0][0]
                logger.info(f"Chuyển đổi {vol_col} sang giá trị USDT")
                df_check['quote_volume_calculated'] = df[vol_col] * df['price']
                columns_to_check = [(c, n) if c != vol_col else ('quote_volume_calculated', 'Volume_USDT') for c, n in columns_to_check]
            
            if not columns_to_check:
                logger.warning("Không tìm thấy cột OI hoặc Volume phù hợp để phát hiện bất thường")
                return anomalies
            
            # Log cấu trúc dữ liệu
            col_names = [f"{name} (từ {col})" for col, name in columns_to_check]
            logger.info(f"🔍 Kiểm tra bất thường cho các chỉ số: {', '.join(col_names)}")
            
            # Xác định trường timestamp phù hợp
            timestamp_field = None
            for possible_field in ['timestamp', 'hour_timestamp', 'date_timestamp', 'date']:
                if possible_field in df.columns:
                    timestamp_field = possible_field
                    break
            
            if timestamp_field is None:
                logger.warning("Không tìm thấy cột timestamp để phát hiện bất thường")
                return anomalies
            
            # Chuyển đổi timestamp sang datetime nếu chưa phải
            if not pd.api.types.is_datetime64_any_dtype(df_check[timestamp_field]):
                df_check[timestamp_field] = pd.to_datetime(df_check[timestamp_field])
            
            # Danh sách để theo dõi bất thường đã phát hiện để tránh lặp lại
            detected_anomalies = {}  # Key: (metric, rounded_value), Value: timestamp
            
            for col, name in columns_to_check:
                # Tính Z-score
                mean_val = df_check[col].mean()
                std_val = df_check[col].std()
                
                if std_val > 0:
                    z_scores = np.abs((df_check[col] - mean_val) / std_val)
                    anomaly_mask = z_scores > threshold
                    
                    if anomaly_mask.any():
                        anomaly_indices = df_check[anomaly_mask].index
                        for idx in anomaly_indices:
                            value = df_check.loc[idx, col]
                            timestamp = df_check.loc[idx, timestamp_field]
                            z_score = z_scores.loc[idx]
                            
                            # Làm tròn giá trị để nhóm các bất thường tương tự
                            # Làm tròn đến 2 chữ số có nghĩa
                            rounded_value = round(value, -int(np.floor(np.log10(abs(value)))) + 2) if value != 0 else 0
                            anomaly_key = (name, rounded_value)
                            
                            # Kiểm tra xem bất thường này đã được phát hiện gần đây chưa
                            is_duplicate = False
                            if anomaly_key in detected_anomalies:
                                previous_timestamp = detected_anomalies[anomaly_key]
                                # Tính khoảng thời gian giữa 2 phát hiện
                                time_diff = (timestamp - previous_timestamp).total_seconds() / 60
                                if time_diff < dedup_window_minutes:
                                    is_duplicate = True
                                    logger.info(f"⏭️ Bỏ qua anomaly trùng lặp cho {name} với giá trị {rounded_value} (phát hiện cách đây {time_diff:.1f} phút)")
                            
                            if not is_duplicate:
                                # Cập nhật timestamp mới nhất cho anomaly này
                                detected_anomalies[anomaly_key] = timestamp
                                
                                # Thêm chú thích đơn vị USDT cho các giá trị liên quan
                                message = f"Bất thường {name}: {value:,.2f}" + (" USDT" if 'usdt' in name.lower() else "")
                                
                                anomalies.append({
                                    'timestamp': timestamp,
                                    'metric': name,
                                    'value': float(value),
                                    'z_score': float(z_score),
                                    'threshold': threshold,
                                    'severity': 'high' if z_score > threshold + 1 else 'moderate',
                                    'data_type': 'oi' if 'oi' in name.lower() else 'volume',  # Phân loại dữ liệu
                                    'message': message
                                })
            
            logger.info(f"🚨 Phát hiện {len(anomalies)} anomalies với threshold {threshold} (đã lọc trùng lặp)")
            return anomalies
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi phát hiện anomalies: {str(e)}")
            return []

    # ĐÃ THÊM: Hàm mới để kiểm tra xem anomaly có phải là gần đây không
    def _is_recent_anomaly(self, timestamp, minutes=30):
        """Kiểm tra xem anomaly có phải là gần đây không (trong khoảng X phút)"""
        try:
            if isinstance(timestamp, str):
                timestamp = pd.to_datetime(timestamp)
            
            now = datetime.now()
            time_diff = (now - timestamp).total_seconds() / 60
            
            return time_diff <= minutes
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra thời gian anomaly: {str(e)}")
            return False
    
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