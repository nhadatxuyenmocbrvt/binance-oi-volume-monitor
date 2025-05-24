import os
import sqlite3
import pandas as pd
import json
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
            
            # Bảng lưu dữ liệu Open Interest
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS open_interest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open_interest REAL NOT NULL,
                open_interest_value REAL NOT NULL,
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
    
    # Sửa hàm save_open_interest để đảm bảo lưu giá trị đúng
    def save_open_interest(self, symbol, df):
        """Lưu dữ liệu Open Interest vào cơ sở dữ liệu"""
        try:
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu Open Interest để lưu cho {symbol}")
                return 0
            
            # Định dạng lại DataFrame
            df_to_save = df[['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']].copy()
            df_to_save.columns = ['timestamp', 'open_interest', 'open_interest_value']
            df_to_save['symbol'] = symbol
            
            # Log để debug giá trị
            if not df_to_save.empty:
                logger.info(f"Debug: First OI record for {symbol}: " + 
                            f"OI={df_to_save['open_interest'].iloc[0]}, " + 
                            f"Value={df_to_save['open_interest_value'].iloc[0]}")
            
            cursor = self.conn.cursor()
            for _, row in df_to_save.iterrows():
                values = (
                    row['symbol'],
                    row['timestamp'] if isinstance(row['timestamp'], str) else row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    row['open_interest'],
                    row['open_interest_value']
                )
                
                cursor.execute('''
                INSERT OR REPLACE INTO open_interest 
                (symbol, timestamp, open_interest, open_interest_value)
                VALUES (?, ?, ?, ?)
                ''', values)
            
            self.conn.commit()
            logger.info(f"Đã lưu {len(df_to_save)} mẫu Open Interest cho {symbol}")
            return len(df_to_save)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu Open Interest cho {symbol}: {str(e)}")
            return 0
            
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
            
            # Log để debug
            logger.info(f"💾 Saving OI for {symbol}: {open_interest:,.2f} contracts, {open_interest_value:,.2f} USDT")
            
            data = (
                symbol,
                timestamp,
                open_interest,
                open_interest_value  # SỬA: Dùng giá trị thực tế
            )
            
            cursor.execute('''
            INSERT OR REPLACE INTO open_interest 
            (symbol, timestamp, open_interest, open_interest_value)
            VALUES (?, ?, ?, ?)
            ''', data)
            
            self.conn.commit()
            logger.info(f"Đã lưu dữ liệu Open Interest realtime cho {symbol}")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi lưu dữ liệu Open Interest realtime cho {symbol}: {str(e)}")
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
            cursor.execute('''
            SELECT quote_volume FROM ticker  # Thay đổi từ volume sang quote_volume
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
            cursor.execute('''
            SELECT open_interest_value FROM open_interest  # Thay đổi từ open_interest sang open_interest_value
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

    def get_open_interest(self, symbol, limit=100):
        """Lấy dữ liệu Open Interest từ cơ sở dữ liệu"""
        try:
            query = '''
            SELECT * FROM open_interest 
            WHERE symbol = ?
            ORDER BY timestamp DESC
            '''
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn, params=(symbol,))
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
                df = df.sort_values('timestamp').reset_index(drop=True)
            
            logger.info(f"Đã lấy {len(df)} mẫu Open Interest cho {symbol}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu Open Interest: {str(e)}")
            return pd.DataFrame()

    def export_to_json(self, output_dir='./data/json'):
        """Xuất dữ liệu JSON tối ưu cho giao diện mới"""
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
    
    def export_symbol_data(self, symbol):
        """Xuất dữ liệu chi tiết cho một symbol - ĐÃ SỬA"""
        try:
            symbol_data = {
                'symbol': symbol,
                'last_update': datetime.now().isoformat(),
                'klines': {},
                'open_interest': [],
                'tracking_24h': []
            }
            
            # 1. Xuất dữ liệu klines (30 ngày gần nhất cho 1d)
            timeframes = ['1h', '4h', '1d']
            for timeframe in timeframes:
                klines_df = self.get_klines(symbol, timeframe, limit=30 if timeframe == '1d' else 168)
                
                if not klines_df.empty:
                    # Chỉ lấy các cột cần thiết
                    klines_clean = klines_df[['open_time', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']].copy()
                    klines_clean['open_time'] = klines_clean['open_time'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                    symbol_data['klines'][timeframe] = klines_clean.to_dict(orient='records')
            
            # 2. Xuất dữ liệu Open Interest (30 ngày gần nhất) - ĐÃ SỬA để lấy cả open_interest_value
            oi_df = self.get_open_interest(symbol, limit=720)
            if not oi_df.empty:
                oi_clean = oi_df[['timestamp', 'open_interest', 'open_interest_value']].copy()
                oi_clean['timestamp'] = oi_clean['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                symbol_data['open_interest'] = oi_clean.to_dict(orient='records')
            
            # 3. Xuất dữ liệu tracking 24h
            tracking_df = self.get_24h_tracking_data(symbol)
            if not tracking_df.empty:
                tracking_clean = tracking_df[['hour_timestamp', 'price', 'volume', 'open_interest', 
                                            'price_change_1h', 'volume_change_1h', 'oi_change_1h']].copy()
                tracking_clean['hour_timestamp'] = tracking_clean['hour_timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                symbol_data['tracking_24h'] = tracking_clean.to_dict(orient='records')
            
            return symbol_data
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi xuất dữ liệu cho {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'error': str(e),
                'klines': {},
                'open_interest': [],
                'tracking_24h': []
            }
    
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