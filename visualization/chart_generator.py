import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import setup_logging

logger = setup_logging(__name__, 'chart_generator.log')

class ChartGenerator:
    def __init__(self):
        # Đảm bảo thư mục charts tồn tại
        os.makedirs('data/charts', exist_ok=True)
        logger.info("Khởi tạo ChartGenerator")
    
    def plot_price_and_oi(self, price_df, oi_df, symbol, timeframe='1d', lookback_days=30):
        """Vẽ biểu đồ giá và Open Interest"""
        try:
            if price_df.empty or oi_df.empty:
                logger.warning(f"Không có dữ liệu để vẽ biểu đồ cho {symbol}")
                return None
            
            # Đảm bảo kiểu dữ liệu datetime cho các cột thời gian
            if 'open_time' in price_df.columns and not pd.api.types.is_datetime64_any_dtype(price_df['open_time']):
                price_df['open_time'] = pd.to_datetime(price_df['open_time'])
                
            if 'timestamp' in oi_df.columns and not pd.api.types.is_datetime64_any_dtype(oi_df['timestamp']):
                oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'])
            
            # Lọc dữ liệu theo khoảng thời gian
            end_time = datetime.now()
            start_time = end_time - timedelta(days=lookback_days)
            
            price_df = price_df[(price_df['open_time'] >= start_time) & (price_df['open_time'] <= end_time)]
            oi_df = oi_df[(oi_df['timestamp'] >= start_time) & (oi_df['timestamp'] <= end_time)]
            
            if price_df.empty or oi_df.empty:
                logger.warning(f"Không có dữ liệu trong khoảng thời gian cho {symbol}")
                return None
            
            # Tạo figure với hai subplots
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
            
            # Vẽ biểu đồ giá
            ax1.plot(price_df['open_time'], price_df['close'], label='Giá đóng cửa', color='blue')
            ax1.set_title(f'{symbol} - Giá và Open Interest ({timeframe})', fontsize=16)
            ax1.set_ylabel('Giá', fontsize=12)
            ax1.grid(True)
            ax1.legend(loc='upper left')
            
            # Vẽ biểu đồ Open Interest
            ax2.plot(oi_df['timestamp'], oi_df['open_interest'], label='Open Interest', color='green')
            ax2.set_xlabel('Thời gian', fontsize=12)
            ax2.set_ylabel('Open Interest', fontsize=12)
            ax2.grid(True)
            ax2.legend(loc='upper left')
            
            # Định dạng trục x
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            file_path = f'data/charts/{symbol}_{timeframe}_price_oi.png'
            plt.savefig(file_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ giá và OI cho {symbol} tại {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ giá và OI: {str(e)}")
            return None
    
    def plot_volume_analysis(self, df, symbol, timeframe='1d', lookback_days=30):
        """Vẽ biểu đồ phân tích Volume"""
        try:
            if df.empty:
                logger.warning(f"Không có dữ liệu để vẽ biểu đồ Volume cho {symbol}")
                return None
            
            # Đảm bảo kiểu dữ liệu datetime cho cột thời gian
            if 'open_time' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['open_time']):
                df['open_time'] = pd.to_datetime(df['open_time'])
                
            # Tính toán metrics cho Volume
            df['volume_ma5'] = df['volume'].rolling(window=5).mean()
            df['volume_ma20'] = df['volume'].rolling(window=20).mean()
            
            # Lọc dữ liệu theo khoảng thời gian
            end_time = datetime.now()
            start_time = end_time - timedelta(days=lookback_days)
            
            df = df[(df['open_time'] >= start_time) & (df['open_time'] <= end_time)]
            
            if df.empty:
                logger.warning(f"Không có dữ liệu Volume trong khoảng thời gian cho {symbol}")
                return None
            
            # Tạo figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Vẽ biểu đồ Volume
            width = 0.8
            ax.bar(df['open_time'], df['volume'], width=width, label='Volume', color='blue', alpha=0.6)
            ax.plot(df['open_time'], df['volume_ma5'], label='MA5', color='red', linewidth=2)
            ax.plot(df['open_time'], df['volume_ma20'], label='MA20', color='orange', linewidth=2)
            
            ax.set_title(f'{symbol} - Phân tích Volume ({timeframe})', fontsize=16)
            ax.set_xlabel('Thời gian', fontsize=12)
            ax.set_ylabel('Volume', fontsize=12)
            ax.grid(True)
            ax.legend(loc='upper left')
            
            # Định dạng trục x
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            file_path = f'data/charts/{symbol}_{timeframe}_volume.png'
            plt.savefig(file_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ Volume cho {symbol} tại {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ Volume: {str(e)}")
            return None
    
    def plot_oi_analysis(self, df, symbol, lookback_days=30):
        """Vẽ biểu đồ phân tích Open Interest"""
        try:
            if df.empty:
                logger.warning(f"Không có dữ liệu để vẽ biểu đồ OI cho {symbol}")
                return None
            
            # Đảm bảo kiểu dữ liệu datetime cho cột thời gian
            if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
            # Tính toán metrics cho OI
            df['oi_ma5'] = df['open_interest'].rolling(window=5).mean()
            df['oi_ma20'] = df['open_interest'].rolling(window=20).mean()
            
            # Lọc dữ liệu theo khoảng thời gian
            end_time = datetime.now()
            start_time = end_time - timedelta(days=lookback_days)
            
            df = df[(df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)]
            
            if df.empty:
                logger.warning(f"Không có dữ liệu OI trong khoảng thời gian cho {symbol}")
                return None
            
            # Tạo figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Vẽ biểu đồ OI
            ax.plot(df['timestamp'], df['open_interest'], label='Open Interest', color='green')
            ax.plot(df['timestamp'], df['oi_ma5'], label='MA5', color='red', linewidth=2)
            ax.plot(df['timestamp'], df['oi_ma20'], label='MA20', color='orange', linewidth=2)
            
            ax.set_title(f'{symbol} - Phân tích Open Interest', fontsize=16)
            ax.set_xlabel('Thời gian', fontsize=12)
            ax.set_ylabel('Open Interest', fontsize=12)
            ax.grid(True)
            ax.legend(loc='upper left')
            
            # Định dạng trục x
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Lưu biểu đồ
            file_path = f'data/charts/{symbol}_oi.png'
            plt.savefig(file_path)
            plt.close()
            
            logger.info(f"Đã tạo biểu đồ OI cho {symbol} tại {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Lỗi khi tạo biểu đồ OI: {str(e)}")
            return None
    
    def generate_all_charts(self, db, symbol, timeframe='1d'):
        """Tạo tất cả các biểu đồ cho một symbol"""
        try:
            # Lấy dữ liệu
            price_df = db.get_klines(symbol, timeframe)
            oi_df = db.get_open_interest(symbol)
            
            # Vẽ các biểu đồ
            price_oi_chart = self.plot_price_and_oi(price_df, oi_df, symbol, timeframe)
            volume_chart = self.plot_volume_analysis(price_df, symbol, timeframe)
            oi_chart = self.plot_oi_analysis(oi_df, symbol)
            
            results = {
                'price_oi': price_oi_chart,
                'volume': volume_chart,
                'oi': oi_chart
            }
            
            logger.info(f"Đã tạo tất cả biểu đồ cho {symbol}")
            return results
        except Exception as e:
            logger.error(f"Lỗi khi tạo các biểu đồ cho {symbol}: {str(e)}")
            return None