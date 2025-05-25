import os
import sqlite3
import pandas as pd
import json
import random
from datetime import datetime, timedelta
from config.settings import DB_PATH, setup_logging, SYMBOLS

logger = setup_logging(__name__, 'database.log')

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        # Đảm bảo thư mục tồn tại
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = None
        self.connect()
        self.create_tables()
        logger.info(f"Đã khởi tạo cơ sở dữ liệu tại {db_path}")
    
    def connect(self):
        """Kết nối đến cơ sở dữ liệu"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            logger.info("Đã kết nối đến cơ sở dữ liệu")
        except Exception as e:
            logger.error(f"Lỗi khi kết nối đến cơ sở dữ liệu: {str(e)}")
    
    def create_tables(self):
        """Tạo các bảng cần thiết nếu chưa tồn tại"""
        try:
            cursor = self.conn.cursor()
            
            # Bảng lưu dữ liệu giá (klines)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open_time TIMESTAMP NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                close_time TIMESTAMP NOT NULL,
                quote_volume REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                taker_buy_base_volume REAL NOT NULL,
                taker_buy_quote_volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, open_time)
            )
            ''')
            
            # Bảng lưu dữ liệu Open Interest - ĐÃ SỬA để thêm các cột bổ sung
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_interest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open_interest REAL NOT NULL,
                open_interest_value REAL NOT NULL,
                avg_open_interest REAL,
                avg_open_interest_value REAL,
                date_only DATE,
                UNIQUE(symbol, timestamp)
            )
            ''')
            
            # Bảng lưu dữ liệu ticker (volume realtime)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL NOT NULL,
                trade_count INTEGER NOT NULL,
                last_price REAL NOT NULL,
                price_change_percent REAL NOT NULL,
                UNIQUE(symbol, timestamp)
            )
            ''')
            
            # Bảng lưu dữ liệu anomaly (bất thường)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                data_type TEXT NOT NULL,
                value REAL NOT NULL,
                z_score REAL NOT NULL,
                message TEXT NOT NULL,
                notified BOOLEAN DEFAULT 0,
                UNIQUE(symbol, timestamp, data_type)
            )
            ''')
            
            # BẢNG TRACKING 24H TỐI ƯU
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS hourly_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                hour_timestamp TIMESTAMP NOT NULL,
                price REAL NOT NULL,
                volume REAL NOT NULL,
                open_interest REAL NOT NULL,
                price_change_1h REAL DEFAULT 0,
                volume_change_1h REAL DEFAULT 0,
                oi_change_1h REAL DEFAULT 0,
                UNIQUE(symbol, hour_timestamp)
            )
            ''')
            
            # ĐÃ THÊM: Bảng mới để lưu trữ daily tracking tối ưu
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date_timestamp DATE NOT NULL,
                price REAL NOT NULL,
                total_volume REAL NOT NULL,
                quote_volume REAL NOT NULL,
                open_interest REAL NOT NULL,
                open_interest_value REAL NOT NULL,
                avg_open_interest REAL,
                avg_open_interest_value REAL,
                price_change_1d REAL DEFAULT 0,
                volume_change_1d REAL DEFAULT 0,
                oi_change_1d REAL DEFAULT 0,
                last_update TIMESTAMP NOT NULL,
                UNIQUE(symbol, date_timestamp)
            )
            ''')
            
            self.conn.commit()
            logger.info("Đã tạo các bảng cần thiết")
        except Exception as e:
            logger.error(f"Lỗi khi tạo bảng: {str(e)}")
    
    def close(self):
        """Đóng kết nối cơ sở dữ liệu"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Đã đóng kết nối cơ sở dữ liệu")
    
    def save_klines(self, symbol, timeframe, df):
        """Lưu dữ liệu nến (klines) vào cơ sở dữ liệu"""
        try:
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu klines để lưu cho {symbol} - {timeframe}")
                return 0
            
            # Định dạng lại DataFrame để phù hợp với cấu trúc bảng
            df_to_save = df[['open_time', 'open', 'high', 'low', 'close', 'volume',
                             'close_time', 'quote_volume', 'trades_count',
                             'taker_buy_base_volume', 'taker_buy_quote_volume']].copy()
            
            # Thêm cột symbol và timeframe
            df_to_save['symbol'] = symbol
            df_to_save['timeframe'] = timeframe
            
            # Lưu vào cơ sở dữ liệu với INSERT OR REPLACE
            cursor = self.conn.cursor()
            for _, row in df_to_save.iterrows():
                values = (
                    row['symbol'],
                    row['timeframe'],
                    row['open_time'] if isinstance(row['open_time'], str) else row['open_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume'],
                    row['close_time'] if isinstance(row['close_time'], str) else row['close_time'].strftime('%Y-%m-%d %H:%M:%S'),
                    row['quote_volume'],
                    row['trades_count'],
                    row['taker_buy_base_volume'],
                    row['taker_buy_quote_volume']
                )
                
                cursor.execute('''
                INSERT OR REPLACE INTO klines 
                (symbol, timeframe, open_time, open, high, low, close, volume, close_time, 
                quote_volume, trades_count, taker_buy_base_volume, taker_buy_quote_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', values)
            
            self.conn.commit()
            logger.info(f"Đã lưu {len(df_to_save)} mẫu klines cho {symbol} - {timeframe}")
            return len(df_to_save)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu klines cho {symbol} - {timeframe}: {str(e)}")
            return 0
    
    # ĐÃ SỬA: Cải thiện hàm save_open_interest để lưu đầy đủ dữ liệu
    def save_open_interest(self, symbol, df):
        """Lưu dữ liệu Open Interest vào cơ sở dữ liệu - ĐÃ SỬA"""
        try:
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu Open Interest để lưu cho {symbol}")
                return 0
            
            # Kiểm tra các cột cần thiết
            required_columns = ['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']
            for col in required_columns:
                if col not in df.columns:
                    logger.warning(f"Thiếu cột {col} trong dữ liệu OI của {symbol}")
                    return 0
            
            # Định dạng lại DataFrame
            df_to_save = df[['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']].copy()
            
            # Thêm các cột trung bình nếu có
            if 'avgOpenInterest' in df.columns and 'avgOpenInterestValue' in df.columns:
                df_to_save['avgOpenInterest'] = df['avgOpenInterest']
                df_to_save['avgOpenInterestValue'] = df['avgOpenInterestValue']
            else:
                df_to_save['avgOpenInterest'] = df_to_save['sumOpenInterest']
                df_to_save['avgOpenInterestValue'] = df_to_save['sumOpenInterestValue']
            
            # Đảm bảo timestamp là datetime
            if not pd.api.types.is_datetime64_any_dtype(df_to_save['timestamp']):
                df_to_save['timestamp'] = pd.to_datetime(df_to_save['timestamp'])
            
            # Thêm cột date_only
            df_to_save['date_only'] = df_to_save['timestamp'].dt.date
            
            # Đổi tên cột
            df_to_save.columns = ['timestamp', 'open_interest', 'open_interest_value', 
                                'avg_open_interest', 'avg_open_interest_value', 'date_only']
            
            # Thêm cột symbol
            df_to_save['symbol'] = symbol
            
            # Log để debug giá trị
            if not df_to_save.empty:
                logger.info(f"Debug: Saving OI record for {symbol}: " + 
                            f"OI={df_to_save['open_interest'].iloc[-1]:,.2f}, " + 
                            f"Value={df_to_save['open_interest_value'].iloc[-1]:,.2f} USDT, " +
                            f"AvgOI={df_to_save['avg_open_interest'].iloc[-1]:,.2f}, " + 
                            f"AvgValue={df_to_save['avg_open_interest_value'].iloc[-1]:,.2f} USDT")
            
            cursor = self.conn.cursor()
            for _, row in df_to_save.iterrows():
                timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row['timestamp'], 'strftime') else row['timestamp']
                date_only_str = row['date_only'].strftime('%Y-%m-%d') if hasattr(row['date_only'], 'strftime') else row['date_only']
                
                values = (
                    row['symbol'],
                    timestamp_str,
                    row['open_interest'],
                    row['open_interest_value'],
                    row['avg_open_interest'],
                    row['avg_open_interest_value'],
                    date_only_str
                )
                
                cursor.execute('''
                INSERT OR REPLACE INTO open_interest 
                (symbol, timestamp, open_interest, open_interest_value, 
                avg_open_interest, avg_open_interest_value, date_only)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', values)
                
                # ĐÃ THÊM: Cập nhật daily_tracking table
                if timeframe_from_timestamp(timestamp_str) == '1d':
                    self._update_daily_tracking_from_oi(
                        symbol, 
                        date_only_str, 
                        row['open_interest'],
                        row['open_interest_value'],
                        row['avg_open_interest'],
                        row['avg_open_interest_value']
                    )
            
            self.conn.commit()
            logger.info(f"Đã lưu {len(df_to_save)} mẫu Open Interest cho {symbol}")
            return len(df_to_save)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu Open Interest cho {symbol}: {str(e)}")
            return 0
    
    # ĐÃ THÊM: Hàm mới để cập nhật daily tracking từ dữ liệu OI
    def _update_daily_tracking_from_oi(self, symbol, date_str, oi, oi_value, avg_oi, avg_oi_value):
        """Cập nhật bảng daily_tracking từ dữ liệu OI"""
        try:
            cursor = self.conn.cursor()
            
            # Kiểm tra xem đã có bản ghi cho ngày này chưa
            cursor.execute('''
            SELECT id, price, total_volume, quote_volume FROM daily_tracking
            WHERE symbol = ? AND date_timestamp = ?
            ''', (symbol, date_str))
            
            existing = cursor.fetchone()
            
            if existing:
                # Cập nhật bản ghi hiện có
                cursor.execute('''
                UPDATE daily_tracking SET
                open_interest = ?,
                open_interest_value = ?,
                avg_open_interest = ?,
                avg_open_interest_value = ?,
                last_update = ?
                WHERE id = ?
                ''', (
                    oi,
                    oi_value,
                    avg_oi,
                    avg_oi_value,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    existing[0]
                ))
            else:
                # Lấy dữ liệu giá từ klines cho ngày này
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                next_day = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                
                cursor.execute('''
                SELECT close, quote_volume FROM klines
                WHERE symbol = ? AND timeframe = '1d' AND 
                open_time >= ? AND open_time < ?
                LIMIT 1
                ''', (symbol, date_str, next_day))
                
                kline_data = cursor.fetchone()
                
                price = kline_data[0] if kline_data else 0
                quote_volume = kline_data[1] if kline_data else 0
                
                # Tạo bản ghi mới
                cursor.execute('''
                INSERT INTO daily_tracking
                (symbol, date_timestamp, price, total_volume, quote_volume, 
                open_interest, open_interest_value, avg_open_interest, avg_open_interest_value,
                price_change_1d, volume_change_1d, oi_change_1d, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)
                ''', (
                    symbol,
                    date_str,
                    price,
                    0,  # total_volume (sẽ được cập nhật sau)
                    quote_volume,
                    oi,
                    oi_value,
                    avg_oi,
                    avg_oi_value,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi cập nhật daily_tracking từ OI: {str(e)}")
            return False
            
    # Sửa hàm save_hourly_tracking để hiển thị đúng giá trị
    def save_hourly_tracking(self, hour_timestamp):
        """Lưu dữ liệu tracking 24h - TỐI ƯU"""
        try:
            cursor = self.conn.cursor()
            
            for symbol in SYMBOLS:
                # Lấy dữ liệu gần nhất
                price_data = self.get_latest_price(symbol)
                volume_data = self.get_latest_volume(symbol)
                oi_data = self.get_latest_oi(symbol)
                
                # Log debug values
                logger.info(f"DEBUG {symbol} tracking values: price={price_data}, volume={volume_data}, oi={oi_data}")
                
                # Tính thay đổi so với giờ trước
                prev_data = self.get_hourly_data(symbol, hour_timestamp - timedelta(hours=1))
                
                price_change_1h = 0
                volume_change_1h = 0
                oi_change_1h = 0
                
                if prev_data:
                    if prev_data['price'] > 0:
                        price_change_1h = ((price_data - prev_data['price']) / prev_data['price']) * 100
                    if prev_data['volume'] > 0:
                        volume_change_1h = ((volume_data - prev_data['volume']) / prev_data['volume']) * 100
                    if prev_data['open_interest'] > 0:
                        oi_change_1h = ((oi_data - prev_data['open_interest']) / prev_data['open_interest']) * 100
                
                # Lưu dữ liệu tracking
                data = (
                    symbol,
                    hour_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    price_data,
                    volume_data,
                    oi_data,
                    price_change_1h,
                    volume_change_1h,
                    oi_change_1h
                )
                
                cursor.execute('''
                INSERT OR REPLACE INTO hourly_tracking 
                (symbol, hour_timestamp, price, volume, open_interest, 
                price_change_1h, volume_change_1h, oi_change_1h)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', data)
            
            self.conn.commit()
            logger.info(f"Đã lưu dữ liệu tracking 24h cho {hour_timestamp.strftime('%H:00')}")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu tracking 24h: {str(e)}")
            return False
    
    # ĐÃ THÊM: Hàm mới để cập nhật daily tracking
    def save_daily_tracking(self, date_timestamp=None):
        """Lưu dữ liệu tracking theo ngày - ĐƯỢC THÊM MỚI"""
        try:
            if date_timestamp is None:
                date_timestamp = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            date_str = date_timestamp.strftime('%Y-%m-%d')
            cursor = self.conn.cursor()
            
            for symbol in SYMBOLS:
                try:
                    # Lấy dữ liệu từ klines
                    cursor.execute('''
                    SELECT close, quote_volume FROM klines
                    WHERE symbol = ? AND timeframe = '1d' AND
                    date(open_time) = ?
                    LIMIT 1
                    ''', (symbol, date_str))
                    
                    kline_data = cursor.fetchone()
                    
                    if not kline_data:
                        logger.warning(f"Không có dữ liệu klines cho {symbol} ngày {date_str}")
                        continue
                    
                    price = kline_data[0]
                    quote_volume = kline_data[1]
                    
                    # Lấy dữ liệu OI cho ngày này
                    cursor.execute('''
                    SELECT open_interest, open_interest_value, avg_open_interest, avg_open_interest_value
                    FROM open_interest
                    WHERE symbol = ? AND date(date_only) = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    ''', (symbol, date_str))
                    
                    oi_data = cursor.fetchone()
                    
                    if not oi_data:
                        logger.warning(f"Không có dữ liệu OI cho {symbol} ngày {date_str}")
                        oi = 0
                        oi_value = 0
                        avg_oi = 0
                        avg_oi_value = 0
                    else:
                        oi = oi_data[0]
                        oi_value = oi_data[1]
                        avg_oi = oi_data[2] if oi_data[2] is not None else oi_data[0]
                        avg_oi_value = oi_data[3] if oi_data[3] is not None else oi_data[1]
                    
                    # Lấy dữ liệu ngày trước
                    prev_date = date_timestamp - timedelta(days=1)
                    prev_date_str = prev_date.strftime('%Y-%m-%d')
                    
                    cursor.execute('''
                    SELECT price, quote_volume, open_interest_value
                    FROM daily_tracking
                    WHERE symbol = ? AND date_timestamp = ?
                    ''', (symbol, prev_date_str))
                    
                    prev_data = cursor.fetchone()
                    
                    # Tính toán thay đổi
                    price_change_1d = 0
                    volume_change_1d = 0
                    oi_change_1d = 0
                    
                    if prev_data:
                        prev_price = prev_data[0]
                        prev_volume = prev_data[1]
                        prev_oi = prev_data[2]
                        
                        if prev_price > 0:
                            price_change_1d = ((price - prev_price) / prev_price) * 100
                        if prev_volume > 0:
                            volume_change_1d = ((quote_volume - prev_volume) / prev_volume) * 100
                        if prev_oi > 0:
                            oi_change_1d = ((oi_value - prev_oi) / prev_oi) * 100
                    
                    # Lưu dữ liệu
                    cursor.execute('''
                    INSERT OR REPLACE INTO daily_tracking
                    (symbol, date_timestamp, price, total_volume, quote_volume,
                    open_interest, open_interest_value, avg_open_interest, avg_open_interest_value,
                    price_change_1d, volume_change_1d, oi_change_1d, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        date_str,
                        price,
                        0,  # total_volume tạm thời để 0
                        quote_volume,
                        oi,
                        oi_value,
                        avg_oi,
                        avg_oi_value,
                        price_change_1d,
                        volume_change_1d,
                        oi_change_1d,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    logger.info(f"Đã lưu daily tracking cho {symbol} ngày {date_str}")
                    
                except Exception as e:
                    logger.error(f"Lỗi khi lưu daily tracking cho {symbol}: {str(e)}")
            
            self.conn.commit()
            logger.info(f"Đã lưu dữ liệu tracking ngày {date_str} cho tất cả symbols")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu daily tracking: {str(e)}")
            return False
    
    def save_ticker(self, symbol, ticker_data):
        """Lưu dữ liệu ticker (volume realtime) vào cơ sở dữ liệu - ĐÃ SỬA"""
        try:
            cursor = self.conn.cursor()
            
            timestamp = ticker_data['timestamp']
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo lưu volume theo USDT
            volume = float(ticker_data['volume'])
            quote_volume = float(ticker_data['quoteVolume'])  # ĐẢM BẢO SỬ DỤNG quoteVolume
            
            # Log để debug
            logger.info(f"💾 Saving Volume for {symbol}: {volume:,.2f} contracts, Quote Volume: {quote_volume:,.2f} USDT")
            
            data = (
                symbol,
                timestamp,
                volume,
                quote_volume,
                ticker_data.get('count', 0),
                float(ticker_data['lastPrice']),
                float(ticker_data['priceChangePercent'])
            )
            
            cursor.execute('''
            INSERT OR REPLACE INTO ticker 
            (symbol, timestamp, volume, quote_volume, trade_count, last_price, price_change_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            self.conn.commit()
            logger.info(f"Đã lưu dữ liệu ticker cho {symbol}")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu ticker cho {symbol}: {str(e)}")
            return False
    
    def save_realtime_open_interest(self, symbol, oi_data):
        """Lưu dữ liệu Open Interest realtime vào cơ sở dữ liệu - ĐÃ SỬA"""
        try:
            cursor = self.conn.cursor()
            
            timestamp = oi_data['timestamp']
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            # Đảm bảo lưu cả giá trị OI theo contracts và theo USDT
            open_interest = float(oi_data['openInterest'])
            open_interest_value = float(oi_data.get('openInterestValue', 0))  # SỬA: Lấy giá trị thực tế
            
            # Tính date_only
            if isinstance(oi_data['timestamp'], datetime):
                date_only = oi_data['timestamp'].date().strftime('%Y-%m-%d')
            else:
                date_only = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').date().strftime('%Y-%m-%d')
            
            # Log để debug
            logger.info(f"💾 Saving OI for {symbol}: {open_interest:,.2f} contracts, {open_interest_value:,.2f} USDT")
            
            data = (
                symbol,
                timestamp,
                open_interest,
                open_interest_value,  # SỬA: Dùng giá trị thực tế
                open_interest,  # avg_open_interest (same as current for realtime)
                open_interest_value,  # avg_open_interest_value
                date_only
            )
            
            cursor.execute('''
            INSERT OR REPLACE INTO open_interest 
            (symbol, timestamp, open_interest, open_interest_value, 
            avg_open_interest, avg_open_interest_value, date_only)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            self.conn.commit()
            logger.info(f"Đã lưu dữ liệu Open Interest realtime cho {symbol}")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu Open Interest realtime cho {symbol}: {str(e)}")
            return False
    
    def initialize_24h_tracking_data(self):
        """Thu thập và lưu dữ liệu lịch sử 24h khi khởi động hệ thống"""
        try:
            # Kiểm tra số lượng dữ liệu tracking hiện có
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT hour_timestamp) FROM hourly_tracking')
            count = cursor.fetchone()[0]
            
            if count >= 24:
                logger.info(f"✅ Đã có đủ dữ liệu tracking 24h: {count} giờ")
                return True
            
            logger.info(f"⏳ Thiếu dữ liệu tracking 24h (có {count}/24 giờ), đang tải dữ liệu lịch sử...")
            
            # Import here to avoid circular import
            from data_collector.historical_data import HistoricalDataCollector
            
            # Thu thập dữ liệu 24h từ Binance API
            collector = HistoricalDataCollector()
            data_24h = collector.collect_24h_hourly_data()
            
            if not data_24h or data_24h['success_count'] == 0:
                logger.error("❌ Không thể thu thập dữ liệu 24h từ Binance API")
                return False
            
            # Xử lý và lưu dữ liệu cho từng giờ trong 24h qua
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
            saved_hours = 0
            
            for hour_offset in range(23, -1, -1):
                hour_time = now - timedelta(hours=hour_offset)
                
                # Kiểm tra xem giờ này đã có dữ liệu chưa
                cursor.execute('''
                SELECT COUNT(*) FROM hourly_tracking 
                WHERE hour_timestamp = ?
                ''', (hour_time.strftime('%Y-%m-%d %H:%M:%S'),))
                
                if cursor.fetchone()[0] > 0:
                    logger.info(f"⏭️ Đã có dữ liệu cho {hour_time.strftime('%Y-%m-%d %H:%M')}, bỏ qua")
                    continue
                
                # Tìm dữ liệu phù hợp nhất cho giờ này từ dữ liệu đã thu thập
                for symbol in SYMBOLS:
                    price = None
                    volume = None
                    oi = None
                    
                    # Lấy dữ liệu klines gần nhất với giờ này
                    if symbol in data_24h['klines'] and not data_24h['klines'][symbol].empty:
                        klines_df = data_24h['klines'][symbol]
                        klines_df['time_diff'] = abs((pd.to_datetime(klines_df['open_time']) - hour_time).dt.total_seconds())
                        closest_kline = klines_df.loc[klines_df['time_diff'].idxmin()]
                        
                        price = closest_kline['close']
                        volume = closest_kline['quote_volume']
                    
                    # Lấy dữ liệu OI gần nhất với giờ này
                    if symbol in data_24h['open_interest'] and not data_24h['open_interest'][symbol].empty:
                        oi_df = data_24h['open_interest'][symbol]
                        oi_df['time_diff'] = abs((pd.to_datetime(oi_df['timestamp']) - hour_time).dt.total_seconds())
                        closest_oi = oi_df.loc[oi_df['time_diff'].idxmin()]
                        
                        oi = closest_oi['sumOpenInterestValue']
                    
                    # Nếu không có dữ liệu, sử dụng dữ liệu realtime hiện tại
                    if price is None:
                        price = self.get_latest_price(symbol)
                    if volume is None:
                        volume = self.get_latest_volume(symbol)
                    if oi is None:
                        oi = self.get_latest_oi(symbol)
                    
                    # Tính thay đổi so với giờ trước (nếu có)
                    prev_data = self.get_hourly_data(symbol, hour_time - timedelta(hours=1))
                    price_change = 0
                    volume_change = 0
                    oi_change = 0
                    
                    if prev_data:
                        if prev_data['price'] > 0:
                            price_change = ((price - prev_data['price']) / prev_data['price']) * 100
                        if prev_data['volume'] > 0:
                            volume_change = ((volume - prev_data['volume']) / prev_data['volume']) * 100
                        if prev_data['open_interest'] > 0:
                            oi_change = ((oi - prev_data['open_interest']) / prev_data['open_interest']) * 100
                    
                    # Lưu vào database
                    cursor.execute('''
                    INSERT OR REPLACE INTO hourly_tracking 
                    (symbol, hour_timestamp, price, volume, open_interest, 
                    price_change_1h, volume_change_1h, oi_change_1h)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        symbol,
                        hour_time.strftime('%Y-%m-%d %H:%M:%S'),
                        price,
                        volume,
                        oi,
                        price_change,
                        volume_change,
                        oi_change
                    ))
                
                saved_hours += 1
                logger.info(f"✅ Đã lưu dữ liệu lịch sử cho {hour_time.strftime('%Y-%m-%d %H:%M')}")
            
            self.conn.commit()
            logger.info(f"🎉 Hoàn thành tải dữ liệu lịch sử 24h: đã lưu {saved_hours} giờ")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Lỗi khi khởi tạo dữ liệu tracking 24h: {str(e)}")
            return False
    
    # ĐÃ THÊM: Hàm khởi tạo dữ liệu daily tracking 30 ngày
    def initialize_30d_tracking_data(self):
        """Thu thập và lưu dữ liệu daily tracking 30 ngày - ĐƯỢC THÊM MỚI"""
        try:
            # Kiểm tra số lượng dữ liệu tracking hiện có
            cursor = self.conn.cursor()
            cursor.execute('SELECT COUNT(DISTINCT date_timestamp) FROM daily_tracking')
            count = cursor.fetchone()[0]
            
            if count >= 30:
                logger.info(f"✅ Đã có đủ dữ liệu tracking 30d: {count} ngày")
                return True
            
            logger.info(f"⏳ Thiếu dữ liệu daily tracking (có {count}/30 ngày), đang tải dữ liệu lịch sử...")
            
            # Thu thập dữ liệu 30 ngày
            self.initialize_30d_data()
            
            # Lưu dữ liệu tracking cho 30 ngày
            now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            for day_offset in range(29, -1, -1):
                day_time = now - timedelta(days=day_offset)
                self.save_daily_tracking(day_time)
                logger.info(f"✅ Đã khởi tạo daily tracking cho ngày {day_time.strftime('%Y-%m-%d')}")
            
            logger.info("🎉 Hoàn thành khởi tạo daily tracking 30 ngày")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi khởi tạo dữ liệu tracking 30d: {str(e)}")
            return False
    
    def get_latest_price(self, symbol):
        """Lấy giá mới nhất của symbol"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT last_price FROM ticker 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Lỗi khi lấy giá mới nhất cho {symbol}: {str(e)}")
            return 0
    
    def get_latest_volume(self, symbol):
        """Lấy volume mới nhất của symbol theo USDT"""
        try:
            cursor = self.conn.cursor()
            # Thay đổi từ volume sang quote_volume
            cursor.execute('''
            SELECT quote_volume FROM ticker 
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Lỗi khi lấy volume mới nhất cho {symbol}: {str(e)}")
            return 0

    def get_latest_oi(self, symbol):
        """Lấy Open Interest mới nhất của symbol theo USDT"""
        try:
            cursor = self.conn.cursor()
            # Thay đổi từ open_interest sang open_interest_value
            cursor.execute('''
            SELECT open_interest_value FROM open_interest
            WHERE symbol = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
            ''', (symbol,))
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Lỗi khi lấy OI mới nhất cho {symbol}: {str(e)}")
            return 0
    
    def get_hourly_data(self, symbol, hour_timestamp):
        """Lấy dữ liệu tracking theo giờ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT price, volume, open_interest 
            FROM hourly_tracking 
            WHERE symbol = ? AND hour_timestamp = ?
            ''', (symbol, hour_timestamp.strftime('%Y-%m-%d %H:%M:%S')))
            
            result = cursor.fetchone()
            if result:
                return {
                    'price': result[0],
                    'volume': result[1],
                    'open_interest': result[2]
                }
            return None
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu hourly cho {symbol}: {str(e)}")
            return None
    
    def get_24h_tracking_data(self, symbol=None):
        """Lấy dữ liệu tracking 24h - TỐI ƯU"""
        try:
            # Lấy 24 giờ gần nhất
            end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            start_time = end_time - timedelta(hours=23)
            
            if symbol:
                query = '''
                SELECT symbol, hour_timestamp, price, volume, open_interest,
                       price_change_1h, volume_change_1h, oi_change_1h
                FROM hourly_tracking 
                WHERE symbol = ? AND hour_timestamp >= ? AND hour_timestamp <= ?
                ORDER BY hour_timestamp ASC
                '''
                df = pd.read_sql_query(query, self.conn, params=(symbol, start_time, end_time))
            else:
                query = '''
                SELECT symbol, hour_timestamp, price, volume, open_interest,
                       price_change_1h, volume_change_1h, oi_change_1h
                FROM hourly_tracking 
                WHERE hour_timestamp >= ? AND hour_timestamp <= ?
                ORDER BY symbol, hour_timestamp ASC
                '''
                df = pd.read_sql_query(query, self.conn, params=(start_time, end_time))
            
            if not df.empty:
                df['hour_timestamp'] = pd.to_datetime(df['hour_timestamp'])
            
            logger.info(f"Đã lấy {len(df)} mẫu tracking 24h cho {symbol or 'all symbols'}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu tracking 24h: {str(e)}")
            return pd.DataFrame()
    
    # ĐÃ THÊM: Hàm lấy dữ liệu tracking 30 ngày
    def get_30d_tracking_data(self, symbol=None):
        """Lấy dữ liệu tracking 30d - ĐƯỢC THÊM MỚI"""
        try:
            # Lấy 30 ngày gần nhất
            end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_date = end_date - timedelta(days=29)
            
            if symbol:
                query = '''
                SELECT symbol, date_timestamp, price, quote_volume, open_interest_value,
                       avg_open_interest_value, price_change_1d, volume_change_1d, oi_change_1d
                FROM daily_tracking 
                WHERE symbol = ? AND date_timestamp >= ? AND date_timestamp <= ?
                ORDER BY date_timestamp ASC
                '''
                df = pd.read_sql_query(query, self.conn, params=(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                ))
            else:
                query = '''
                SELECT symbol, date_timestamp, price, quote_volume, open_interest_value,
                       avg_open_interest_value, price_change_1d, volume_change_1d, oi_change_1d
                FROM daily_tracking 
                WHERE date_timestamp >= ? AND date_timestamp <= ?
                ORDER BY symbol, date_timestamp ASC
                '''
                df = pd.read_sql_query(query, self.conn, params=(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                ))
            
            if not df.empty:
                df['date_timestamp'] = pd.to_datetime(df['date_timestamp'])
            
            logger.info(f"Đã lấy {len(df)} mẫu tracking 30d cho {symbol or 'all symbols'}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu tracking 30d: {str(e)}")
            return pd.DataFrame()
    
    def get_klines(self, symbol, timeframe, limit=100):
        """Lấy dữ liệu nến từ cơ sở dữ liệu"""
        try:
            query = '''
            SELECT * FROM klines 
            WHERE symbol = ? AND timeframe = ?
            ORDER BY open_time DESC
            '''
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn, params=(symbol, timeframe))
            
            if not df.empty:
                df['open_time'] = pd.to_datetime(df['open_time'], format='mixed', errors='coerce')
                df['close_time'] = pd.to_datetime(df['close_time'], format='mixed', errors='coerce')
                df = df.sort_values('open_time').reset_index(drop=True)
            
            logger.info(f"Đã lấy {len(df)} mẫu klines cho {symbol} - {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu klines: {str(e)}")
            return pd.DataFrame()

    # ĐÃ SỬA: Cải thiện hàm lấy Open Interest
    def get_open_interest(self, symbol, limit=100, period='all'):
        """Lấy dữ liệu Open Interest từ cơ sở dữ liệu - ĐÃ SỬA"""
        try:
            # Lọc theo period
            if period == 'daily':
                # Lấy dữ liệu theo ngày (unique date_only)
                query = '''
                SELECT o1.* FROM open_interest o1
                JOIN (
                    SELECT date_only, MAX(timestamp) as max_timestamp
                    FROM open_interest
                    WHERE symbol = ?
                    GROUP BY date_only
                ) o2 ON o1.timestamp = o2.max_timestamp AND o1.date_only = o2.date_only
                WHERE o1.symbol = ?
                ORDER BY o1.date_only DESC
                '''
                params = (symbol, symbol)
            else:
                # Lấy tất cả dữ liệu
                query = '''
                SELECT * FROM open_interest 
                WHERE symbol = ?
                ORDER BY timestamp DESC
                '''
                params = (symbol,)
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
                df['date_only'] = pd.to_datetime(df['date_only'], format='mixed', errors='coerce').dt.date
                df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Đã lấy {len(df)} mẫu Open Interest cho {symbol} (period: {period})")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu Open Interest: {str(e)}")
            return pd.DataFrame()

    # ĐÃ SỬA: Cải thiện hàm xuất dữ liệu JSON cho 30 ngày
    def export_to_json(self, output_dir='./data/json'):
        """Xuất dữ liệu JSON tối ưu cho giao diện mới - ĐÃ SỬA"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Thêm xuất file cho GitHub Pages
            github_pages_dir = './docs/assets/data'
            os.makedirs(github_pages_dir, exist_ok=True)
            
            # Xuất dữ liệu cho từng symbol
            for symbol in SYMBOLS:
                symbol_data = self.export_symbol_data(symbol)
                
                # Lưu dữ liệu cho symbol vào thư mục chính
                with open(f"{output_dir}/{symbol}.json", 'w', encoding='utf-8') as f:
                    json.dump(symbol_data, f, ensure_ascii=False, indent=2)
                
                # Lưu vào thư mục GitHub Pages
                with open(f"{github_pages_dir}/{symbol}.json", 'w', encoding='utf-8') as f:
                    json.dump(symbol_data, f, ensure_ascii=False, indent=2)
            
            # Lưu danh sách symbols vào thư mục chính
            with open(f"{output_dir}/symbols.json", 'w', encoding='utf-8') as f:
                json.dump(SYMBOLS, f, ensure_ascii=False)
            
            # Lưu danh sách symbols vào thư mục GitHub Pages
            with open(f"{github_pages_dir}/symbols.json", 'w', encoding='utf-8') as f:
                json.dump(SYMBOLS, f, ensure_ascii=False)
            
            # Xuất metadata
            metadata = {
                'last_update': datetime.now().isoformat(),
                'symbols_count': len(SYMBOLS),
                'data_range': {
                    'hourly_hours': 24,
                    'daily_days': 30
                }
            }
            
            # Lưu metadata vào cả hai thư mục
            with open(f"{output_dir}/metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            with open(f"{github_pages_dir}/metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Xuất anomalies nếu có
            anomalies_df = self.get_anomalies(limit=50)
            if not anomalies_df.empty:
                anomalies_df['timestamp'] = anomalies_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                anomalies_json = anomalies_df.to_dict(orient='records')
                
                # Lưu vào cả hai thư mục
                with open(f"{output_dir}/anomalies.json", 'w', encoding='utf-8') as f:
                    json.dump(anomalies_json, f, ensure_ascii=False, indent=2)
                
                with open(f"{github_pages_dir}/anomalies.json", 'w', encoding='utf-8') as f:
                    json.dump(anomalies_json, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Đã xuất dữ liệu JSON tối ưu trong thư mục {output_dir} và {github_pages_dir}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi xuất dữ liệu JSON: {str(e)}")
            return False
    
    # ĐÃ SỬA: Cải thiện hàm xuất dữ liệu symbol
    def export_symbol_data(self, symbol):
        """Xuất dữ liệu chi tiết cho một symbol - ĐÃ SỬA"""
        try:
            symbol_data = {
                'symbol': symbol,
                'last_update': datetime.now().isoformat(),
                'klines': {},
                'open_interest': [],
                'tracking_24h': [],
                'tracking_30d': []  # THÊM trường tracking 30 ngày
            }
            
            # 1. Xuất dữ liệu klines (30 ngày gần nhất cho 1d)
            timeframes = ['1h', '4h', '1d']
            for timeframe in timeframes:
                limit = 50 if timeframe == '1d' else 168
                klines_df = self.get_klines(symbol, timeframe, limit=limit)
                
                if not klines_df.empty:
                    # Chỉ lấy 30 ngày gần nhất cho 1d
                    if timeframe == '1d' and len(klines_df) > 30:
                        klines_df = klines_df.tail(30)
                    
                    # QUAN TRỌNG: Đảm bảo các cột đúng, không đổi tên
                    klines_clean = klines_df[['open_time', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']].copy()
                    klines_clean['open_time'] = klines_clean['open_time'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                    
                    # Log để debug
                    if len(klines_clean) > 0:
                        logger.info(f"{symbol} {timeframe}: first={klines_clean['open_time'].iloc[0]}, last={klines_clean['open_time'].iloc[-1]}, count={len(klines_clean)}")
                    
                    symbol_data['klines'][timeframe] = klines_clean.to_dict(orient='records')
            
            # 2. Xuất dữ liệu Open Interest (30 ngày gần nhất) - ĐÃ SỬA
            # Sử dụng daily period để lấy dữ liệu OI theo ngày
            oi_df = self.get_open_interest(symbol, limit=30, period='daily')
            
            if not oi_df.empty:
                # ĐÃ SỬA: Bao gồm cả các trường bổ sung
                oi_clean = oi_df[['timestamp', 'open_interest', 'open_interest_value', 
                                'avg_open_interest', 'avg_open_interest_value']].copy()
                oi_clean['timestamp'] = oi_clean['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                
                # Log để debug
                if len(oi_clean) > 0:
                    logger.info(f"{symbol} OI: first={oi_clean['timestamp'].iloc[0]}, last={oi_clean['timestamp'].iloc[-1]}, count={len(oi_clean)}")
                
                symbol_data['open_interest'] = oi_clean.to_dict(orient='records')
            
            # 3. Xuất dữ liệu tracking 24h
            tracking_df = self.get_24h_tracking_data(symbol)
            
            if tracking_df.empty or len(tracking_df) < 24:
                # Nếu chưa đủ 24 giờ, tự động khởi tạo dữ liệu lịch sử
                logger.info(f"Không đủ dữ liệu tracking 24h cho {symbol}, đang khởi tạo dữ liệu lịch sử")
                self.initialize_24h_tracking_data()
                tracking_df = self.get_24h_tracking_data(symbol)
            
            if not tracking_df.empty:
                tracking_clean = tracking_df[['hour_timestamp', 'price', 'volume', 'open_interest', 
                                            'price_change_1h', 'volume_change_1h', 'oi_change_1h']].copy()
                tracking_clean['hour_timestamp'] = tracking_clean['hour_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                
                # Log để debug
                if len(tracking_clean) > 0:
                    logger.info(f"{symbol} 24h: first={tracking_clean['hour_timestamp'].iloc[0]}, last={tracking_clean['hour_timestamp'].iloc[-1]}, count={len(tracking_clean)}")
                
                symbol_data['tracking_24h'] = tracking_clean.to_dict(orient='records')
            
            # 4. ĐÃ THÊM: Xuất dữ liệu tracking 30d
            tracking_30d_df = self.get_30d_tracking_data(symbol)
            
            if tracking_30d_df.empty or len(tracking_30d_df) < 20:  # Yêu cầu ít nhất 20 ngày
                # Nếu chưa đủ dữ liệu, tự động khởi tạo
                logger.info(f"Không đủ dữ liệu tracking 30d cho {symbol}, đang khởi tạo dữ liệu")
                self.initialize_30d_tracking_data()
                tracking_30d_df = self.get_30d_tracking_data(symbol)
            
            if not tracking_30d_df.empty:
                tracking_30d_clean = tracking_30d_df[['date_timestamp', 'price', 'quote_volume', 'open_interest_value',
                                                'avg_open_interest_value', 'price_change_1d', 'volume_change_1d', 'oi_change_1d']].copy()
                tracking_30d_clean['date_timestamp'] = tracking_30d_clean['date_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                
                # FIX: Đảm bảo sử dụng open_interest_value thay vì open_interest
                # Log để debug
                if len(tracking_30d_clean) > 0:
                    logger.info(f"{symbol} 30d: first={tracking_30d_clean['date_timestamp'].iloc[0]}, " +
                             f"last={tracking_30d_clean['date_timestamp'].iloc[-1]}, count={len(tracking_30d_clean)}")
                    
                    # Log giá trị OI để kiểm tra
                    logger.info(f"{symbol} 30d OI Value: latest={tracking_30d_clean['open_interest_value'].iloc[-1]:,.2f} USDT")
                
                symbol_data['tracking_30d'] = tracking_30d_clean.to_dict(orient='records')
            
            return symbol_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi xuất dữ liệu cho {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'error': str(e),
                'klines': {},
                'open_interest': [],
                'tracking_24h': [],
                'tracking_30d': []
            }

    def initialize_30d_data(self):
        """Thu thập và khởi tạo dữ liệu 30 ngày"""
        try:
            logger.info("📅 Khởi tạo dữ liệu 30 ngày...")
            
            # Import để tránh circular import
            from data_collector.historical_data import HistoricalDataCollector
            
            # Thu thập dữ liệu 30 ngày
            collector = HistoricalDataCollector()
            data_30d = collector.collect_30d_daily_data()
            
            saved_count = 0
            if data_30d and data_30d['success_count'] > 0:
                # Lưu dữ liệu klines
                for symbol in data_30d['klines']:
                    df = data_30d['klines'][symbol]
                    if not df.empty:
                        # Kiểm tra dữ liệu trước khi lưu
                        if 'quote_volume' in df.columns:
                            logger.info(f"📊 {symbol} Kiểm tra Quote Volume trước khi lưu: {df['quote_volume'].iloc[-1]:,.2f} USDT")
                        
                        # Lưu dữ liệu
                        saved = self.save_klines(symbol, '1d', df)
                        if saved > 0:
                            saved_count += 1
                
                # Lưu dữ liệu Open Interest
                for symbol in data_30d['open_interest']:
                    df = data_30d['open_interest'][symbol]
                    if not df.empty:
                        # Lưu dữ liệu
                        self.save_open_interest(symbol, df)
                
                logger.info(f"✅ Đã khởi tạo dữ liệu 30 ngày cho {saved_count} symbols")
                return True
            else:
                logger.error("❌ Không thể thu thập dữ liệu 30 ngày")
                return False
                
        except Exception as e:
            logger.error(f"❌ Lỗi khi khởi tạo dữ liệu 30 ngày: {str(e)}")
            return False

    def get_anomalies(self, limit=20):
        """Lấy danh sách các bất thường đã phát hiện"""
        try:
            query = "SELECT * FROM anomalies ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            
            logger.info(f"Đã lấy {len(df)} mẫu anomalies")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu anomalies: {str(e)}")
            return pd.DataFrame()
    
    def save_anomaly(self, anomaly_data):
        """Lưu thông tin về bất thường vào cơ sở dữ liệu"""
        try:
            cursor = self.conn.cursor()
            
            timestamp = anomaly_data['timestamp']
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
            data = (
                anomaly_data['symbol'],
                timestamp,
                anomaly_data['data_type'],
                anomaly_data['value'],
                anomaly_data['z_score'],
                anomaly_data['message'],
                0  # Chưa thông báo
            )
            
            cursor.execute('''
            INSERT OR REPLACE INTO anomalies 
            (symbol, timestamp, data_type, value, z_score, message, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', data)
            
            self.conn.commit()
            logger.info(f"Đã lưu thông tin bất thường cho {anomaly_data['symbol']} - {anomaly_data['data_type']}")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu thông tin bất thường: {str(e)}")
            return False

# Helper function
def timeframe_from_timestamp(timestamp_str):
    """Xác định timeframe từ timestamp string"""
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    if timestamp.hour == 0 and timestamp.minute == 0:
        return '1d'
    elif timestamp.minute == 0:
        return '1h'
    else:
        return 'unknown'