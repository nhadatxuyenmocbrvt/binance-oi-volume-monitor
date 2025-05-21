import os
import sqlite3
import pandas as pd
from datetime import datetime
from config.settings import DB_PATH, setup_logging

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
            
            # Lưu vào cơ sở dữ liệu - Sửa để xử lý lỗi UNIQUE constraint
            # Thay vì dùng to_sql, chúng ta sẽ lưu từng bản ghi thông qua INSERT OR REPLACE
            cursor = self.conn.cursor()
            for _, row in df_to_save.iterrows():
                # Chuẩn bị dữ liệu
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
                
                # Thêm dữ liệu vào bảng với INSERT OR REPLACE
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
    
    def save_open_interest(self, symbol, df):
        """Lưu dữ liệu Open Interest vào cơ sở dữ liệu"""
        try:
            if df is None or df.empty:
                logger.warning(f"Không có dữ liệu Open Interest để lưu cho {symbol}")
                return 0
            
            # Định dạng lại DataFrame để phù hợp với cấu trúc bảng
            df_to_save = df[['timestamp', 'sumOpenInterest', 'sumOpenInterestValue']].copy()
            df_to_save.columns = ['timestamp', 'open_interest', 'open_interest_value']
            
            # Thêm cột symbol
            df_to_save['symbol'] = symbol
            
            # Lưu vào cơ sở dữ liệu - Sửa để xử lý lỗi UNIQUE constraint
            cursor = self.conn.cursor()
            for _, row in df_to_save.iterrows():
                # Chuẩn bị dữ liệu
                values = (
                    row['symbol'],
                    row['timestamp'] if isinstance(row['timestamp'], str) else row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    row['open_interest'],
                    row['open_interest_value']
                )
                
                # Thêm dữ liệu vào bảng với INSERT OR REPLACE
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
    
    def save_ticker(self, symbol, ticker_data):
        """Lưu dữ liệu ticker (volume realtime) vào cơ sở dữ liệu"""
        try:
            cursor = self.conn.cursor()
            
            # Chuẩn bị dữ liệu
            timestamp = ticker_data['timestamp']
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
            data = (
                symbol,
                timestamp,
                ticker_data['volume'],
                ticker_data['quoteVolume'],
                ticker_data['count'],
                ticker_data['lastPrice'],
                ticker_data['priceChangePercent']
            )
            
            # Thêm dữ liệu vào bảng với INSERT OR REPLACE
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
        """Lưu dữ liệu Open Interest realtime vào cơ sở dữ liệu"""
        try:
            cursor = self.conn.cursor()
            
            # Chuẩn bị dữ liệu
            timestamp = oi_data['timestamp']
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
            data = (
                symbol,
                timestamp,
                oi_data['openInterest'],
                0  # Không có giá trị OI, đặt bằng 0
            )
            
            # Thêm dữ liệu vào bảng với INSERT OR REPLACE
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
    
    def save_anomaly(self, anomaly_data):
        """Lưu thông tin về bất thường vào cơ sở dữ liệu"""
        try:
            cursor = self.conn.cursor()
            
            # Chuẩn bị dữ liệu
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
            
            # Thêm dữ liệu vào bảng với INSERT OR REPLACE
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
    
    def get_klines(self, symbol, timeframe, limit=None):
        """Lấy dữ liệu nến từ cơ sở dữ liệu"""
        try:
            query = f'''
            SELECT * FROM klines 
            WHERE symbol = '{symbol}' AND timeframe = '{timeframe}'
            ORDER BY open_time DESC
            '''
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn)
            
            # Chuyển đổi các cột thời gian sang datetime với định dạng linh hoạt
            if not df.empty:
                # Sử dụng format='mixed' để tự động nhận diện định dạng datetime
                # và errors='coerce' để xử lý bất kỳ định dạng không hợp lệ
                df['open_time'] = pd.to_datetime(df['open_time'], format='mixed', errors='coerce')
                df['close_time'] = pd.to_datetime(df['close_time'], format='mixed', errors='coerce')
            
            logger.info(f"Đã lấy {len(df)} mẫu klines cho {symbol} - {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu klines: {str(e)}")
            return pd.DataFrame()

    def get_open_interest(self, symbol, limit=None):
        """Lấy dữ liệu Open Interest từ cơ sở dữ liệu"""
        try:
            query = f'''
            SELECT * FROM open_interest 
            WHERE symbol = '{symbol}'
            ORDER BY timestamp DESC
            '''
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn)
            
            # Chuyển đổi timestamp sang datetime với định dạng linh hoạt
            if not df.empty:
                # Sử dụng format='mixed' để tự động nhận diện định dạng datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            
            logger.info(f"Đã lấy {len(df)} mẫu Open Interest cho {symbol}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu Open Interest: {str(e)}")
            return pd.DataFrame()

    def get_ticker(self, symbol, limit=None):
        """Lấy dữ liệu ticker từ cơ sở dữ liệu"""
        try:
            query = f'''
            SELECT * FROM ticker 
            WHERE symbol = '{symbol}'
            ORDER BY timestamp DESC
            '''
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn)
            
            # Chuyển đổi timestamp sang datetime với định dạng linh hoạt
            if not df.empty:
                # Sử dụng format='mixed' để tự động nhận diện định dạng datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            
            logger.info(f"Đã lấy {len(df)} mẫu ticker cho {symbol}")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu ticker: {str(e)}")
            return pd.DataFrame()

    def get_anomalies(self, limit=100, notified=None):
        """Lấy danh sách các bất thường đã phát hiện"""
        try:
            query = "SELECT * FROM anomalies"
            
            if notified is not None:
                query += f" WHERE notified = {1 if notified else 0}"
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn)
            
            # Chuyển đổi timestamp sang datetime với định dạng linh hoạt
            if not df.empty:
                # Sử dụng format='mixed' để tự động nhận diện định dạng datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            
            logger.info(f"Đã lấy {len(df)} mẫu anomalies")
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu anomalies: {str(e)}")
            return pd.DataFrame()
    
    def mark_anomaly_as_notified(self, anomaly_id):
        """Đánh dấu một bất thường đã được thông báo"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE anomalies SET notified = 1 WHERE id = ?", (anomaly_id,))
            self.conn.commit()
            logger.info(f"Đã đánh dấu anomaly {anomaly_id} là đã thông báo")
            return True
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Lỗi khi đánh dấu anomaly đã thông báo: {str(e)}")
            return False
    
    def export_to_json(self, output_dir='./data/json'):
        """Xuất dữ liệu để sử dụng cho GitHub Pages"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Xuất dữ liệu klines
            query = '''
            SELECT symbol, timeframe, open_time, open, high, low, close, volume
            FROM klines
            ORDER BY symbol, timeframe, open_time
            '''
            klines_df = pd.read_sql_query(query, self.conn)
            
            # Xử lý đúng định dạng thời gian - FIX ISSUE
            try:
                # Thử chuyển đổi với định dạng từ cơ sở dữ liệu
                klines_df['open_time'] = pd.to_datetime(klines_df['open_time'], errors='coerce')
            except:
                # Nếu lỗi, thử với định dạng ISO
                klines_df['open_time'] = pd.to_datetime(klines_df['open_time'], format='ISO8601', errors='coerce')
            
            # Chuyển đổi sang chuỗi ISO để tránh lỗi định dạng
            klines_df['open_time'] = klines_df['open_time'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Xuất dữ liệu Open Interest
            query = '''
            SELECT symbol, timestamp, open_interest
            FROM open_interest
            ORDER BY symbol, timestamp
            '''
            oi_df = pd.read_sql_query(query, self.conn)
            
            # Xử lý đúng định dạng thời gian - FIX ISSUE
            try:
                # Thử chuyển đổi với định dạng từ cơ sở dữ liệu
                oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], errors='coerce')
            except:
                # Nếu lỗi, thử với định dạng ISO
                oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], format='ISO8601', errors='coerce')
            
            # Chuyển đổi sang chuỗi ISO để tránh lỗi định dạng
            oi_df['timestamp'] = oi_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Xuất dữ liệu anomalies
            query = '''
            SELECT symbol, timestamp, data_type, value, z_score, message
            FROM anomalies
            ORDER BY timestamp DESC
            LIMIT 100
            '''
            anomalies_df = pd.read_sql_query(query, self.conn)
            
            # Xử lý đúng định dạng thời gian - FIX ISSUE
            try:
                # Thử chuyển đổi với định dạng từ cơ sở dữ liệu
                anomalies_df['timestamp'] = pd.to_datetime(anomalies_df['timestamp'], errors='coerce')
            except:
                # Nếu lỗi, thử với định dạng ISO
                anomalies_df['timestamp'] = pd.to_datetime(anomalies_df['timestamp'], format='ISO8601', errors='coerce')
            
            # Chuyển đổi sang chuỗi ISO để tránh lỗi định dạng
            anomalies_df['timestamp'] = anomalies_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            
            # Tạo dữ liệu tổng hợp cho mỗi symbol
            for symbol in klines_df['symbol'].unique():
                symbol_data = {
                    'klines': {},
                    'open_interest': []
                }
                
                # Dữ liệu klines cho từng timeframe
                for timeframe in klines_df[klines_df['symbol'] == symbol]['timeframe'].unique():
                    df_filtered = klines_df[(klines_df['symbol'] == symbol) & (klines_df['timeframe'] == timeframe)]
                    symbol_data['klines'][timeframe] = df_filtered.to_dict(orient='records')
                
                # Dữ liệu Open Interest
                df_filtered = oi_df[oi_df['symbol'] == symbol]
                symbol_data['open_interest'] = df_filtered.to_dict(orient='records')
                
                # Lưu dữ liệu cho symbol
                with open(f"{output_dir}/{symbol}.json", 'w', encoding='utf-8') as f:
                    import json
                    json.dump(symbol_data, f, ensure_ascii=False)
            
            # Lưu dữ liệu anomalies
            with open(f"{output_dir}/anomalies.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(anomalies_df.to_dict(orient='records'), f, ensure_ascii=False)
            
            # Lưu danh sách các symbols có sẵn
            symbols_list = list(klines_df['symbol'].unique())
            with open(f"{output_dir}/symbols.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(symbols_list, f, ensure_ascii=False)
            
            logger.info(f"Đã xuất dữ liệu sang định dạng JSON trong thư mục {output_dir}")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi xuất dữ liệu sang JSON: {str(e)}")
            return False