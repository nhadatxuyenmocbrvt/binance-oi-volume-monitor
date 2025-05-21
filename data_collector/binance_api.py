import time
import hmac
import hashlib
import requests
import pandas as pd
from urllib.parse import urlencode
from datetime import datetime, timedelta
from config.settings import BINANCE_API_KEY, BINANCE_API_SECRET, setup_logging

logger = setup_logging(__name__, 'binance_api.log')

class BinanceAPI:
    def __init__(self):
        self.base_url = 'https://fapi.binance.com'
        self.api_key = BINANCE_API_KEY
        self.api_secret = BINANCE_API_SECRET
        logger.info("Khởi tạo Binance API")
        
    def _generate_signature(self, params):
        """Tạo chữ ký HMAC-SHA256 cho request"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint, method='GET', params=None, signed=False):
        """Thực hiện request đến Binance API"""
        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key}
        
        if params is None:
            params = {}
            
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, params=params)
            else:
                logger.error(f"Phương thức không được hỗ trợ: {method}")
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Lỗi API: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Lỗi khi gọi API: {str(e)}")
            return None
    
    def get_server_time(self):
        """Lấy thời gian chính xác từ máy chủ Binance"""
        endpoint = '/fapi/v1/time'
        result = self._make_request(endpoint)
        if result and 'serverTime' in result:
            logger.info(f"Đã lấy thời gian máy chủ Binance: {result['serverTime']}")
            return result['serverTime']
        else:
            # Nếu không lấy được, trả về thời gian hiện tại trừ đi 1 tháng 
            # (để đảm bảo không trong tương lai)
            safe_time = int(time.time() * 1000) - 30 * 24 * 60 * 60 * 1000
            logger.warning(f"Không thể lấy thời gian máy chủ Binance, sử dụng thời gian an toàn: {safe_time}")
            return safe_time
    
    def get_exchange_info(self):
        """Lấy thông tin về các cặp giao dịch"""
        endpoint = '/fapi/v1/exchangeInfo'
        return self._make_request(endpoint)
    
    def get_funding_rate(self, symbol, start_time=None, end_time=None, limit=100):
        """Lấy funding rate của một symbol"""
        endpoint = '/fapi/v1/fundingRate'
        params = {'symbol': symbol, 'limit': limit}
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        return self._make_request(endpoint, params=params)
    
    def get_klines(self, symbol, interval, start_time=None, end_time=None, limit=500):
        """Lấy dữ liệu nến (klines)"""
        endpoint = '/fapi/v1/klines'
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        
        # Lấy thời gian máy chủ Binance
        server_time = self.get_server_time()
        
        # Xử lý start_time
        if start_time:
            # Đảm bảo start_time không nằm trong tương lai
            if start_time > server_time:
                logger.warning(f"start_time ({start_time}) vượt quá server_time ({server_time}), điều chỉnh lại")
                start_time = server_time - (30 * 24 * 60 * 60 * 1000)  # 30 ngày trước server_time
            
            # Đảm bảo không vượt quá 90 ngày
            min_allowed_time = server_time - (90 * 24 * 60 * 60 * 1000)
            if start_time < min_allowed_time:
                logger.warning(f"start_time ({start_time}) quá xa so với giới hạn 90 ngày, điều chỉnh lại")
                start_time = min_allowed_time
                
            params['startTime'] = start_time
        
        # Xử lý end_time
        if end_time:
            # Đảm bảo end_time không nằm trong tương lai
            if end_time > server_time:
                logger.warning(f"end_time ({end_time}) vượt quá server_time ({server_time}), điều chỉnh lại")
                end_time = server_time
                
            params['endTime'] = end_time
            
        # In ra datetime để kiểm tra
        start_date = datetime.fromtimestamp(start_time/1000) if start_time else "N/A"
        end_date = datetime.fromtimestamp(end_time/1000) if end_time else "N/A"
        logger.info(f"Request klines cho {symbol}: từ {start_date} đến {end_date}")
            
        data = self._make_request(endpoint, params=params)
        if data:
            # Chuyển đổi dữ liệu thành DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades_count', 
                'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
            ])
            
            # Chuyển đổi kiểu dữ liệu
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                          'taker_buy_base_volume', 'taker_buy_quote_volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            
            # Chuyển đổi timestamp thành datetime
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
            
            return df
        return None
    
    def get_open_interest(self, symbol, period='5m', limit=500, start_time=None, end_time=None):
        """Lấy dữ liệu Open Interest"""
        endpoint = '/futures/data/openInterestHist'
        params = {'symbol': symbol, 'period': period, 'limit': limit}
        
        # Lấy thời gian máy chủ Binance
        server_time = self.get_server_time()
        
        # Xử lý start_time
        if start_time is not None:
            # Đảm bảo start_time là số nguyên
            if not isinstance(start_time, int):
                try:
                    if hasattr(start_time, 'timestamp'):
                        start_time = int(start_time.timestamp() * 1000)
                    else:
                        start_time = int(start_time)
                except:
                    logger.warning(f"start_time không hợp lệ, sử dụng mặc định 7 ngày: {start_time}")
                    start_time = server_time - (7 * 24 * 60 * 60 * 1000)  # 7 ngày trước
            
            # Kiểm tra nếu startTime trong tương lai
            if start_time > server_time:
                logger.warning(f"start_time {start_time} nằm trong tương lai, điều chỉnh về 7 ngày trước server time")
                start_time = server_time - (7 * 24 * 60 * 60 * 1000)
            
            # Kiểm tra nếu quá xa so với hiện tại (giảm xuống còn 7 ngày do giới hạn API)
            max_lookback_ms = 7 * 24 * 60 * 60 * 1000  # 7 ngày thay vì 30 ngày
            if server_time - start_time > max_lookback_ms:
                logger.warning(f"start_time quá xa trong quá khứ, đã điều chỉnh giới hạn 7 ngày")
                start_time = server_time - max_lookback_ms
            
            # In ra datetime để kiểm tra
            start_date = datetime.fromtimestamp(start_time/1000)
            logger.info(f"Sử dụng startTime = {start_time} ({start_date}) cho symbol {symbol}")
            
            params['startTime'] = start_time
        
        # Xử lý end_time
        if end_time is not None:
            if not isinstance(end_time, int):
                try:
                    if hasattr(end_time, 'timestamp'):
                        end_time = int(end_time.timestamp() * 1000)
                    else:
                        end_time = int(end_time)
                except:
                    logger.warning(f"end_time không hợp lệ, sử dụng thời gian máy chủ")
                    end_time = server_time
            
            # Kiểm tra nếu endTime trong tương lai
            if end_time > server_time:
                logger.warning(f"end_time {end_time} nằm trong tương lai, điều chỉnh về server time")
                end_time = server_time
            
            # Đảm bảo khoảng thời gian request không quá lớn (giới hạn 24 giờ cho mỗi request)
            if start_time is not None and end_time - start_time > 24 * 60 * 60 * 1000:
                logger.warning(f"Khoảng thời gian quá lớn, giới hạn xuống 24 giờ")
                end_time = start_time + 24 * 60 * 60 * 1000
            
            # In ra datetime để kiểm tra
            end_date = datetime.fromtimestamp(end_time/1000)
            logger.info(f"Sử dụng endTime = {end_time} ({end_date}) cho symbol {symbol}")
            
            params['endTime'] = end_time
        
        # Thực hiện request API với cơ chế thử lại
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # Thời gian chờ ban đầu (giây)
        
        while retry_count < max_retries:
            data = self._make_request(endpoint, params=params)
            if data:
                # Xử lý dữ liệu
                df = pd.DataFrame(data)
                if not df.empty:
                    df['sumOpenInterest'] = pd.to_numeric(df['sumOpenInterest'])
                    df['sumOpenInterestValue'] = pd.to_numeric(df['sumOpenInterestValue'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    logger.info(f"Nhận được {len(df)} bản ghi OI cho {symbol}")
                    return df
                else:
                    logger.warning(f"Kết quả trả về rỗng cho OI của {symbol}")
                    return df
            else:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = retry_delay * (2 ** retry_count)  # Backoff exponential
                    logger.warning(f"Thử lại lần {retry_count}/{max_retries} sau {wait_time} giây")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"Không nhận được dữ liệu OI cho {symbol} sau {max_retries} lần thử")
        
        return None

    def get_open_interest_realtime(self, symbol):
        """Lấy dữ liệu Open Interest hiện tại"""
        endpoint = '/fapi/v1/openInterest'
        params = {'symbol': symbol}
        return self._make_request(endpoint, params=params)

    def get_ticker(self, symbol=None):
        """Lấy thông tin giá hiện tại của một hoặc tất cả các symbol"""
        endpoint = '/fapi/v1/ticker/24hr'
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._make_request(endpoint, params=params)