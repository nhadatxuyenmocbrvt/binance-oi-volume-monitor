import time
import hmac
import hashlib
import requests
import pandas as pd
from urllib.parse import urlencode
from datetime import datetime, timedelta
from config.settings import BINANCE_API_KEY, BINANCE_API_SECRET, setup_logging

logger = setup_logging(__name__, 'binance_api.log')

class OptimizedBinanceAPI:
    """
    Binance API tối ưu cho việc thu thập OI & Volume
    Focus: 24h tracking (hourly) + 30d tracking (daily)
    FIX: StartTime validation errors
    """
    
    def __init__(self):
        self.base_url = 'https://fapi.binance.com'
        self.data_url = 'https://fapi.binance.com'
        self.api_key = BINANCE_API_KEY
        self.api_secret = BINANCE_API_SECRET
        
        # Rate limiting settings
        self.request_delay = 0.2
        self.max_retries = 3
        self.retry_delay = 1
        
        # Cache server time
        self._server_time_cache = None
        self._server_time_cache_expires = 0
        
        # Cache symbol info để validate startTime
        self._symbol_info_cache = {}
        
        logger.info("🔧 Khởi tạo OptimizedBinanceAPI - Focus OI & Volume [FIXED]")
        
    def _generate_signature(self, params):
        """Tạo chữ ký HMAC-SHA256 cho request"""
        query_string = urlencode(params, safe='')
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint, method='GET', params=None, signed=False, base_url=None):
        """Thực hiện request đến Binance API với retry và rate limiting"""
        if base_url is None:
            base_url = self.base_url
            
        url = f"{base_url}{endpoint}"
        headers = {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        if params is None:
            params = {}
            
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        # Retry logic với exponential backoff
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.request_delay)
                
                if method == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=30)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=params, timeout=30)
                else:
                    logger.error(f"❌ Phương thức không được hỗ trợ: {method}")
                    return None
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) * self.retry_delay
                    logger.warning(f"⚠️ Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 418:  # IP banned
                    logger.error(f"🚫 IP banned temporarily")
                    time.sleep(60)
                    continue
                elif response.status_code == 400:  # Bad request - log details
                    error_msg = response.text
                    logger.error(f"❌ Bad Request (400): {error_msg}")
                    return None
                else:
                    logger.error(f"❌ API Error: {response.status_code} - {response.text}")
                    if attempt == self.max_retries - 1:
                        return None
                    time.sleep((2 ** attempt) * self.retry_delay)
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Request timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep((2 ** attempt) * self.retry_delay)
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"🔌 Connection error (attempt {attempt + 1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep((2 ** attempt) * self.retry_delay)
                
            except Exception as e:
                logger.error(f"❌ Unexpected error: {str(e)}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep((2 ** attempt) * self.retry_delay)
        
        return None
    
    def get_server_time(self, force_refresh=False):
        """Lấy thời gian chính xác từ máy chủ Binance với caching"""
        current_time = time.time() * 1000
        
        if not force_refresh and self._server_time_cache and current_time < self._server_time_cache_expires:
            time_diff = current_time - (self._server_time_cache_expires - 300000)
            return int(self._server_time_cache + time_diff)
        
        endpoint = '/fapi/v1/time'
        result = self._make_request(endpoint)
        
        if result and 'serverTime' in result:
            self._server_time_cache = result['serverTime']
            self._server_time_cache_expires = current_time + 300000
            logger.info(f"🕒 Server time updated: {datetime.fromtimestamp(result['serverTime']/1000)}")
            return result['serverTime']
        else:
            safe_time = int(current_time - 60000)
            logger.warning(f"⚠️ Cannot get server time, using safe time: {datetime.fromtimestamp(safe_time/1000)}")
            return safe_time
    
    def get_symbol_info(self, symbol):
        """
        Lấy thông tin symbol để validate startTime - FIX MỚI
        """
        if symbol in self._symbol_info_cache:
            return self._symbol_info_cache[symbol]
        
        try:
            exchange_info = self.get_exchange_info()
            if exchange_info and 'symbols' in exchange_info:
                for sym_info in exchange_info['symbols']:
                    if sym_info['symbol'] == symbol:
                        info = {
                            'onboardDate': sym_info.get('onboardDate', 0),
                            'status': sym_info.get('status', 'TRADING')
                        }
                        self._symbol_info_cache[symbol] = info
                        logger.info(f"📋 Symbol {symbol} info cached: onboard={datetime.fromtimestamp(info['onboardDate']/1000) if info['onboardDate'] else 'Unknown'}")
                        return info
            
            # Fallback nếu không tìm thấy
            fallback_info = {'onboardDate': 0, 'status': 'TRADING'}
            self._symbol_info_cache[symbol] = fallback_info
            return fallback_info
            
        except Exception as e:
            logger.error(f"❌ Error getting symbol info for {symbol}: {str(e)}")
            fallback_info = {'onboardDate': 0, 'status': 'TRADING'}
            self._symbol_info_cache[symbol] = fallback_info
            return fallback_info
    
    def get_exchange_info(self):
        """Lấy thông tin về các cặp giao dịch"""
        endpoint = '/fapi/v1/exchangeInfo'
        return self._make_request(endpoint)
    
    def _validate_start_time(self, symbol, start_time):
        """
        Validate và adjust startTime để tránh lỗi invalid - FIX MỚI
        """
        if not start_time:
            return start_time
        
        server_time = self.get_server_time()
        
        # Convert to timestamp if needed
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        
        # Kiểm tra nếu trong tương lai
        if start_time > server_time:
            logger.warning(f"⚠️ {symbol}: startTime in future, adjusting...")
            start_time = server_time - (24 * 60 * 60 * 1000)
        
        # Lấy thông tin symbol để kiểm tra onboard date
        symbol_info = self.get_symbol_info(symbol)
        onboard_date = symbol_info.get('onboardDate', 0)
        
        if onboard_date > 0:
            # Đảm bảo startTime không trước onboard date
            if start_time < onboard_date:
                logger.warning(f"⚠️ {symbol}: startTime before onboard date, adjusting from {datetime.fromtimestamp(start_time/1000)} to {datetime.fromtimestamp(onboard_date/1000)}")
                start_time = onboard_date + (60 * 60 * 1000)  # Thêm 1 giờ buffer
        
        # Giới hạn tối đa 30 ngày
        max_lookback = 30 * 24 * 60 * 60 * 1000
        min_allowed_time = server_time - max_lookback
        
        if start_time < min_allowed_time:
            logger.warning(f"⚠️ {symbol}: startTime too far back, adjusting to 30 days limit")
            start_time = min_allowed_time
        
        return start_time
    
    def get_klines(self, symbol, interval, start_time=None, end_time=None, limit=1000):
        """
        Lấy dữ liệu nến (klines) tối ưu với validation
        """
        endpoint = '/fapi/v1/klines'
        
        if not symbol or not interval:
            logger.error("❌ Symbol và interval không được để trống")
            return None
        
        server_time = self.get_server_time()
        
        # Validate và adjust timestamps
        if start_time:
            start_time = self._validate_start_time(symbol, start_time)
        
        if end_time:
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp() * 1000)
            if end_time > server_time:
                end_time = server_time
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, 1500)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        logger.info(f"📊 Requesting klines for {symbol} {interval}: {datetime.fromtimestamp((start_time or 0)/1000)} - {datetime.fromtimestamp((end_time or server_time)/1000)}")
        
        data = self._make_request(endpoint, params=params)
        
        if data:
            df = self._process_klines_data(data)
            logger.info(f"✅ Retrieved {len(df)} klines for {symbol} {interval}")
            return df
        
        logger.warning(f"⚠️ No klines data for {symbol} {interval}")
        return None
    
    def get_open_interest(self, symbol, period='1h', start_time=None, end_time=None, limit=500):
        """
        Lấy dữ liệu Open Interest tối ưu với validation - FIX START_TIME
        """
        endpoint = '/futures/data/openInterestHist'
        
        valid_periods = ['5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d']
        if period not in valid_periods:
            logger.error(f"❌ Invalid period: {period}. Valid: {valid_periods}")
            return None
        
        server_time = self.get_server_time()
        
        # Validate start_time với symbol-specific logic
        if start_time:
            original_start = start_time
            start_time = self._validate_start_time(symbol, start_time)
            
            # Đặc biệt check cho OI data availability
            if start_time != original_start:
                logger.info(f"🔧 {symbol} OI startTime adjusted: {datetime.fromtimestamp(original_start/1000 if isinstance(original_start, int) else original_start.timestamp())} → {datetime.fromtimestamp(start_time/1000)}")
        
        if end_time:
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp() * 1000)
            if end_time > server_time:
                end_time = server_time
        
        params = {
            'symbol': symbol,
            'period': period,
            'limit': min(limit, 500)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        logger.info(f"🔢 Requesting OI for {symbol} {period}: {datetime.fromtimestamp((start_time or 0)/1000)} - {datetime.fromtimestamp((end_time or server_time)/1000)}")
        
        data = self._make_request(endpoint, params=params)
        
        if data:
            df = self._process_oi_data(data)
            # Log một mẫu giá trị để debug
            if not df.empty:
                logger.info(f"🔍 Sample OI data for {symbol}: OI={df['sumOpenInterest'].iloc[0]}, Value={df['sumOpenInterestValue'].iloc[0]}")
            logger.info(f"✅ Retrieved {len(df)} OI points for {symbol} {period}")
            return df
        
        logger.warning(f"⚠️ No OI data for {symbol} {period}")
        return None
    
    def get_open_interest_chunked(self, symbol, period='1h', start_time=None, end_time=None, days_per_chunk=7):
        """
        Lấy dữ liệu OI theo chunks với smart start_time validation
        """
        all_data = []
        
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        if isinstance(end_time, datetime):
            end_time = int(end_time.timestamp() * 1000)
        
        if not end_time:
            end_time = self.get_server_time()
        
        # Validate start_time trước khi chia chunks
        if start_time:
            start_time = self._validate_start_time(symbol, start_time)
        
        chunk_duration = days_per_chunk * 24 * 60 * 60 * 1000
        current_start = start_time
        chunk_count = 0
        max_chunks = 10  # Giới hạn số chunks để tránh vòng lặp vô tận
        
        while current_start < end_time and chunk_count < max_chunks:
            current_end = min(current_start + chunk_duration, end_time)
            
            # Skip chunks that are too small
            if current_end - current_start < (60 * 60 * 1000):  # Less than 1 hour
                logger.info(f"⏭️ Skipping small chunk for {symbol}: {datetime.fromtimestamp(current_start/1000)}")
                break
            
            df = self.get_open_interest(symbol, period, current_start, current_end, 500)
            
            if df is not None and not df.empty:
                # Log để debug giá trị OI
                logger.info(f"🔍 OI value range for chunk {chunk_count+1}: {df['sumOpenInterest'].min()} - {df['sumOpenInterest'].max()}")
                logger.info(f"🔍 OI value in USD range: {df['sumOpenInterestValue'].min()} - {df['sumOpenInterestValue'].max()}")
                
                all_data.append(df)
                logger.info(f"📊 OI Chunk {chunk_count + 1}: {len(df)} points from {datetime.fromtimestamp(current_start/1000)}")
            else:
                logger.warning(f"⚠️ Empty chunk for {symbol}: {datetime.fromtimestamp(current_start/1000)}")
            
            current_start = current_end + (60 * 60 * 1000)  # 1 hour overlap
            chunk_count += 1
            
            # Rate limiting between chunks
            time.sleep(1.0)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True).drop_duplicates(subset=['timestamp'])
            logger.info(f"✅ Total {len(result)} OI points collected for {symbol} ({chunk_count} chunks)")
            
            # Log thêm thông tin để debug
            if not result.empty:
                logger.info(f"📈 Final OI data summary for {symbol}:")
                logger.info(f"   - OI range: {result['sumOpenInterest'].min()} - {result['sumOpenInterest'].max()}")
                logger.info(f"   - OI value range: {result['sumOpenInterestValue'].min()} - {result['sumOpenInterestValue'].max()}")
                logger.info(f"   - Date range: {result['timestamp'].min()} - {result['timestamp'].max()}")
            
            return result.sort_values('timestamp').reset_index(drop=True)
        
        logger.warning(f"⚠️ No OI data collected for {symbol}")
        return None
    
    def get_klines_chunked(self, symbol, interval, start_time, end_time, chunk_size=1000):
        """Lấy dữ liệu klines theo chunks với validation"""
        all_data = []
        
        if isinstance(start_time, datetime):
            start_time = int(start_time.timestamp() * 1000)
        if isinstance(end_time, datetime):
            end_time = int(end_time.timestamp() * 1000)
        
        # Validate start_time
        start_time = self._validate_start_time(symbol, start_time)
        
        interval_ms = self._get_interval_milliseconds(interval)
        chunk_duration = chunk_size * interval_ms
        
        current_start = start_time
        
        while current_start < end_time:
            current_end = min(current_start + chunk_duration, end_time)
            
            df = self.get_klines(symbol, interval, current_start, current_end, chunk_size)
            
            if df is not None and not df.empty:
                all_data.append(df)
                logger.info(f"📈 Chunk: {len(df)} candles from {datetime.fromtimestamp(current_start/1000)}")
            
            current_start = current_end + interval_ms
            time.sleep(0.5)
        
        if all_data:
            result = pd.concat(all_data, ignore_index=True).drop_duplicates(subset=['open_time'])
            logger.info(f"✅ Total {len(result)} klines collected for {symbol} {interval}")
            return result.sort_values('open_time').reset_index(drop=True)
        
        return None
    
    def get_open_interest_realtime(self, symbol):
        """Lấy dữ liệu Open Interest hiện tại"""
        endpoint = '/fapi/v1/openInterest'
        params = {'symbol': symbol}
        
        data = self._make_request(endpoint, params=params)
        
        if data and 'openInterest' in data:
            # Chuyển từ string sang float để tính toán
            open_interest = float(data['openInterest'])
            logger.info(f"📊 Current OI for {symbol}: {open_interest}")
            
            # Lấy thêm giá hiện tại để tính OI theo USDT
            ticker = self.get_ticker(symbol)
            if ticker and 'lastPrice' in ticker:
                price = float(ticker['lastPrice'])
                oi_value = open_interest * price
                logger.info(f"💰 Current OI Value (USDT) for {symbol}: {oi_value}")
                
                # Thêm giá trị USDT vào kết quả
                data['openInterestValue'] = oi_value
                # Thêm timestamp hiện tại
                data['timestamp'] = datetime.now()
            
            return data
        
        logger.warning(f"⚠️ No current OI data for {symbol}")
        return None
    
    def get_ticker(self, symbol=None):
        """Lấy thông tin ticker 24h"""
        endpoint = '/fapi/v1/ticker/24hr'
        params = {}
        
        if symbol:
            params['symbol'] = symbol
        
        data = self._make_request(endpoint, params=params)
        
        if data:
            if symbol:
                logger.info(f"📈 Ticker for {symbol}: {data.get('lastPrice', 'N/A')}")
            else:
                logger.info(f"📈 Retrieved ticker data for {len(data) if isinstance(data, list) else 1} symbols")
            return data
        
        logger.warning(f"⚠️ No ticker data for {symbol or 'all symbols'}")
        return None
    
    def get_24h_ticker(self, symbol):
        """Lấy ticker 24h cho một symbol cụ thể"""
        return self.get_ticker(symbol)
    
    def get_funding_rate(self, symbol, start_time=None, end_time=None, limit=100):
        """Lấy funding rate (optional)"""
        endpoint = '/fapi/v1/fundingRate'
        params = {'symbol': symbol, 'limit': limit}
        
        if start_time:
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp() * 1000)
            params['startTime'] = start_time
            
        if end_time:
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp() * 1000)
            params['endTime'] = end_time
        
        return self._make_request(endpoint, params=params)
    
    # Helper methods
    def _get_interval_milliseconds(self, interval):
        """Chuyển đổi interval string sang milliseconds"""
        interval_map = {
            '1m': 60 * 1000,
            '3m': 3 * 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '2h': 2 * 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '8h': 8 * 60 * 60 * 1000,
            '12h': 12 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '3d': 3 * 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
        }
        return interval_map.get(interval, 60 * 60 * 1000)
    
    def _process_klines_data(self, data):
        """Xử lý dữ liệu klines thành DataFrame"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades_count', 
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        
        if df.empty:
            return df
        
        # Convert data types
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                       'taker_buy_base_volume', 'taker_buy_quote_volume', 'trades_count']
        
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert timestamps
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # Remove the ignore column
        df = df.drop('ignore', axis=1)
        
        # Log sample data để debug
        if not df.empty:
            logger.info(f"📊 Sample volume: {df['volume'].iloc[0]}, Quote volume: {df['quote_volume'].iloc[0]}")
        
        return df
    
    def _process_oi_data(self, data):
        """Xử lý dữ liệu Open Interest thành DataFrame"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
        
        # Convert data types
        if 'sumOpenInterest' in df.columns:
            # Đảm bảo đơn vị chính xác - đây là giá trị gốc, không cần chia thêm
            df['sumOpenInterest'] = pd.to_numeric(df['sumOpenInterest'], errors='coerce')
            # Log giá trị để debug
            if not df.empty:
                logger.info(f"📊 Sample OI value: {df['sumOpenInterest'].iloc[0]}")
        
        if 'sumOpenInterestValue' in df.columns:
            # Đây là giá trị theo USDT
            df['sumOpenInterestValue'] = pd.to_numeric(df['sumOpenInterestValue'], errors='coerce')
            # Log giá trị để debug
            if not df.empty:
                logger.info(f"💰 Sample OI value (USDT): {df['sumOpenInterestValue'].iloc[0]}")
        
        # Convert timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        return df
    
    def test_connection(self):
        """Test kết nối API"""
        try:
            server_time = self.get_server_time(force_refresh=True)
            exchange_info = self.get_exchange_info()
            
            if server_time and exchange_info:
                logger.info("✅ API connection test successful")
                return True
            else:
                logger.error("❌ API connection test failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ API connection test error: {str(e)}")
            return False

# Backward compatibility
BinanceAPI = OptimizedBinanceAPI