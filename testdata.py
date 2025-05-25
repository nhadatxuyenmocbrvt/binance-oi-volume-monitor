import os
import sys
import sqlite3
import pandas as pd
import requests
import hmac
import hashlib
import time
from datetime import datetime, timedelta

# Hằng số
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
DB_PATH = './data/market_data.db'
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'DOGEUSDT']

# Cấu hình log
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('data_checker')

class DataChecker:
    def __init__(self):
        self.base_url = 'https://fapi.binance.com'
        self.api_key = BINANCE_API_KEY
        self.api_secret = BINANCE_API_SECRET
        self.conn = None
        self.connect_db()
        
    def connect_db(self):
        """Kết nối đến cơ sở dữ liệu"""
        try:
            self.conn = sqlite3.connect(DB_PATH)
            logger.info(f"✅ Đã kết nối đến cơ sở dữ liệu tại {DB_PATH}")
        except Exception as e:
            logger.error(f"❌ Lỗi khi kết nối đến cơ sở dữ liệu: {str(e)}")
    
    def _generate_signature(self, params):
        """Tạo chữ ký HMAC-SHA256 cho request"""
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint, method='GET', params=None):
        """Thực hiện request đến Binance API"""
        if params is None:
            params = {}
            
        url = f"{self.base_url}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key
        }
        
        if self.api_key and self.api_secret and 'signature' not in params:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=params, timeout=30)
            else:
                logger.error(f"❌ Phương thức không được hỗ trợ: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            return None
    
    def get_open_interest_direct(self, symbol, period='1d', limit=30):
        """Lấy dữ liệu Open Interest trực tiếp từ Binance API"""
        endpoint = '/futures/data/openInterestHist'
        
        params = {
            'symbol': symbol,
            'period': period,
            'limit': limit
        }
        
        data = self._make_request(endpoint, params=params)
        
        if data and isinstance(data, list):
            df = pd.DataFrame(data)
            
            if not df.empty:
                # Chuyển đổi kiểu dữ liệu
                df['sumOpenInterest'] = pd.to_numeric(df['sumOpenInterest'])
                df['sumOpenInterestValue'] = pd.to_numeric(df['sumOpenInterestValue'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # Sắp xếp theo thời gian
                df = df.sort_values('timestamp')
                
                return df
        
        return pd.DataFrame()
    
    def get_ticker_24h_direct(self, symbol):
        """Lấy thông tin ticker 24h trực tiếp từ Binance API"""
        endpoint = '/fapi/v1/ticker/24hr'
        params = {'symbol': symbol}
        
        data = self._make_request(endpoint, params=params)
        
        if data:
            return {
                'symbol': data['symbol'],
                'volume': float(data['volume']),
                'quoteVolume': float(data['quoteVolume']),
                'lastPrice': float(data['lastPrice']),
                'openInterest': None  # Ticker API không bao gồm OI
            }
        
        return None
    
    def get_open_interest_current_direct(self, symbol):
        """Lấy dữ liệu Open Interest hiện tại trực tiếp từ Binance API"""
        endpoint = '/fapi/v1/openInterest'
        params = {'symbol': symbol}
        
        data = self._make_request(endpoint, params=params)
        
        if data and 'openInterest' in data:
            # Lấy giá hiện tại để tính giá trị OI
            ticker = self.get_ticker_24h_direct(symbol)
            
            if ticker:
                oi_value = float(data['openInterest']) * float(ticker['lastPrice'])
                return {
                    'symbol': symbol,
                    'openInterest': float(data['openInterest']),
                    'openInterestValue': oi_value,
                    'price': ticker['lastPrice']
                }
        
        return None
    
    def get_db_data(self, symbol, days=30):
        """Lấy dữ liệu từ database"""
        try:
            # Lấy dữ liệu daily_tracking từ DB
            query = '''
            SELECT date_timestamp, price, quote_volume, open_interest, open_interest_value
            FROM daily_tracking 
            WHERE symbol = ? 
            ORDER BY date_timestamp DESC 
            LIMIT ?
            '''
            
            df = pd.read_sql_query(query, self.conn, params=(symbol, days))
            
            if not df.empty:
                df['date_timestamp'] = pd.to_datetime(df['date_timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi lấy dữ liệu từ DB: {str(e)}")
            return pd.DataFrame()
    
    def analyze_symbol_data(self, symbol):
        """Phân tích dữ liệu của một symbol"""
        logger.info(f"🔍 Đang phân tích dữ liệu cho {symbol}...")
        
        # 1. Lấy dữ liệu OI từ Binance API
        oi_api_data = self.get_open_interest_direct(symbol)
        if oi_api_data.empty:
            logger.error(f"❌ Không thể lấy dữ liệu OI từ Binance API cho {symbol}")
            return
        
        # 2. Lấy thông tin OI hiện tại
        current_oi = self.get_open_interest_current_direct(symbol)
        
        # 3. Lấy dữ liệu từ DB
        db_data = self.get_db_data(symbol)
        
        # 4. So sánh dữ liệu
        print(f"\n{'='*80}")
        print(f"🔎 KẾT QUẢ PHÂN TÍCH CHO {symbol}")
        print(f"{'='*80}")
        
        # In thông tin OI hiện tại
        if current_oi:
            print(f"\n📊 OI HIỆN TẠI (trực tiếp từ Binance):")
            print(f"   Contracts: {current_oi['openInterest']:,.2f}")
            print(f"   Giá trị (USDT): {current_oi['openInterestValue']:,.2f}")
            print(f"   Giá hiện tại: {current_oi['price']:,.2f}")
        
        # In mẫu dữ liệu OI từ API
        if not oi_api_data.empty:
            print(f"\n📈 MẪU DỮ LIỆU OI TỪ BINANCE API (dữ liệu gần đây nhất):")
            latest_oi = oi_api_data.iloc[-1]
            print(f"   Ngày: {latest_oi['timestamp'].strftime('%Y-%m-%d')}")
            print(f"   Contracts: {latest_oi['sumOpenInterest']:,.2f}")
            print(f"   Giá trị (USDT): {latest_oi['sumOpenInterestValue']:,.2f}")
            print(f"   Tỷ lệ Giá trị/Contracts: {latest_oi['sumOpenInterestValue'] / latest_oi['sumOpenInterest']:,.2f}")
        
        # In mẫu dữ liệu từ DB
        if not db_data.empty:
            print(f"\n💾 MẪU DỮ LIỆU TỪ DATABASE (dữ liệu gần đây nhất):")
            latest_db = db_data.iloc[0]  # Lấy dòng đầu tiên vì đã sắp xếp DESC
            print(f"   Ngày: {latest_db['date_timestamp'].strftime('%Y-%m-%d')}")
            print(f"   Giá: {latest_db['price']:,.2f}")
            print(f"   Volume (USDT): {latest_db['quote_volume']:,.2f}")
            print(f"   OI (Contracts): {latest_db['open_interest']:,.2f}")
            print(f"   OI (USDT): {latest_db['open_interest_value']:,.2f}")
            if latest_db['open_interest'] > 0:
                print(f"   Tỷ lệ OI Value/OI: {latest_db['open_interest_value'] / latest_db['open_interest']:,.2f}")
        
        # Kiểm tra sai lệch
        if not oi_api_data.empty and not db_data.empty:
            print(f"\n🔍 PHÂN TÍCH SAI LỆCH:")
            
            api_latest = oi_api_data.iloc[-1]
            db_latest = db_data.iloc[0]
            
            # So sánh giá trị OI
            if 'open_interest_value' in db_latest and db_latest['open_interest_value'] > 0:
                oi_ratio = api_latest['sumOpenInterestValue'] / db_latest['open_interest_value']
                print(f"   Tỷ lệ OI (USDT) API/DB: {oi_ratio:,.2f}x")
                
                if oi_ratio > 1000:
                    print(f"   ⚠️ CẢNH BÁO: OI trong API lớn hơn DB ~{oi_ratio:,.0f} lần!")
                    print(f"   💡 Gợi ý: Dữ liệu trong DB có thể đang bị chia với một hệ số.")
                elif oi_ratio < 0.001:
                    print(f"   ⚠️ CẢNH BÁO: OI trong DB lớn hơn API ~{1/oi_ratio:,.0f} lần!")
                    print(f"   💡 Gợi ý: Dữ liệu trong DB có thể đang bị nhân với một hệ số.")
            
            # So sánh giá trị contract
            if 'open_interest' in db_latest and db_latest['open_interest'] > 0:
                contract_ratio = api_latest['sumOpenInterest'] / db_latest['open_interest']
                print(f"   Tỷ lệ OI (Contracts) API/DB: {contract_ratio:,.2f}x")
        
        print(f"\n{'='*80}\n")

    def check_conversion_factors(self, symbol):
        """Kiểm tra các hệ số chuyển đổi có thể có"""
        logger.info(f"🧮 Đang kiểm tra các hệ số chuyển đổi có thể có cho {symbol}...")
        
        # Lấy dữ liệu từ API và DB
        oi_api_data = self.get_open_interest_direct(symbol)
        db_data = self.get_db_data(symbol)
        
        if oi_api_data.empty or db_data.empty:
            logger.error(f"❌ Không đủ dữ liệu để kiểm tra hệ số chuyển đổi")
            return
        
        # Chọn những ngày trùng nhau để so sánh
        api_dates = oi_api_data['timestamp'].dt.date.unique()
        db_dates = pd.to_datetime(db_data['date_timestamp']).dt.date.unique()
        
        common_dates = set(api_dates).intersection(set(db_dates))
        
        if not common_dates:
            logger.warning("⚠️ Không tìm thấy ngày trùng nhau giữa API và DB")
            return
        
        print(f"\n{'='*80}")
        print(f"🧮 KIỂM TRA HỆ SỐ CHUYỂN ĐỔI CHO {symbol}")
        print(f"{'='*80}")
        
        # Kiểm tra cho một số ngày
        factors = []
        print(f"\n{'Ngày':^12} | {'OI API (USDT)':>18} | {'OI DB (USDT)':>18} | {'Hệ số':>10}")
        print(f"{'-'*12} | {'-'*18} | {'-'*18} | {'-'*10}")
        
        for date in sorted(list(common_dates)[-5:]):  # Lấy 5 ngày gần nhất
            # Tìm dữ liệu API cho ngày này
            api_row = oi_api_data[oi_api_data['timestamp'].dt.date == date].iloc[-1]
            
            # Tìm dữ liệu DB cho ngày này
            db_row = db_data[pd.to_datetime(db_data['date_timestamp']).dt.date == date].iloc[0]
            
            # Tính hệ số
            api_value = api_row['sumOpenInterestValue']
            db_value = db_row['open_interest_value']
            
            if db_value > 0:
                factor = api_value / db_value
                factors.append(factor)
                
                print(f"{date} | {api_value:>18,.2f} | {db_value:>18,.2f} | {factor:>10,.2f}x")
        
        # Kết luận
        if factors:
            avg_factor = sum(factors) / len(factors)
            print(f"\n📊 Hệ số trung bình: {avg_factor:,.2f}x")
            
            if avg_factor > 100:
                power = round(len(str(int(avg_factor)))) - 1
                suggested_factor = 10 ** power
                print(f"💡 Gợi ý: Có thể dữ liệu đã bị chia cho ~{suggested_factor:,}.")
                print(f"    Thử nhân dữ liệu trong DB với {suggested_factor:,} để đạt giá trị thực.")
            elif avg_factor < 0.01:
                power = len(str(int(1/avg_factor)))
                suggested_factor = 10 ** power
                print(f"💡 Gợi ý: Có thể dữ liệu đã bị nhân với ~{suggested_factor:,}.")
                print(f"    Thử chia dữ liệu trong DB cho {suggested_factor:,} để đạt giá trị thực.")
        
        print(f"\n{'='*80}\n")
        
    def run_all_checks(self):
        """Chạy tất cả các kiểm tra cho tất cả symbols"""
        for symbol in SYMBOLS:
            self.analyze_symbol_data(symbol)
            self.check_conversion_factors(symbol)
        
        # Kiểm tra một số truy vấn SQL
        self.check_sql_queries()
    
    def check_sql_queries(self):
        """Kiểm tra một số truy vấn SQL để phân tích dữ liệu"""
        print(f"\n{'='*80}")
        print(f"📋 KIỂM TRA TRUY VẤN SQL")
        print(f"{'='*80}")
        
        # Kiểm tra cấu trúc bảng
        print("\n🔍 CẤU TRÚC BẢNG DAILY_TRACKING:")
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(daily_tracking)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
        
        # Kiểm tra giá trị min/max của OI và Volume
        print("\n📊 PHẠM VI GIÁ TRỊ TRONG DAILY_TRACKING:")
        
        for field in ['open_interest_value', 'quote_volume']:
            cursor.execute(f"""
            SELECT symbol, MIN({field}), MAX({field}), AVG({field})
            FROM daily_tracking
            GROUP BY symbol
            """)
            
            results = cursor.fetchall()
            print(f"\n   {field.upper()}:")
            print(f"   {'Symbol':<10} | {'Min':>15} | {'Max':>15} | {'Avg':>15}")
            print(f"   {'-'*10} | {'-'*15} | {'-'*15} | {'-'*15}")
            
            for row in results:
                symbol, min_val, max_val, avg_val = row
                print(f"   {symbol:<10} | {min_val:>15,.2f} | {max_val:>15,.2f} | {avg_val:>15,.2f}")
        
        print(f"\n{'='*80}\n")

# Chạy kiểm tra
if __name__ == "__main__":
    checker = DataChecker()
    checker.run_all_checks()