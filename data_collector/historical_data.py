import pandas as pd
from datetime import datetime, timedelta
import time
from config.settings import SYMBOLS, TIMEFRAMES, LOOKBACK_DAYS, setup_logging
from data_collector.binance_api import BinanceAPI

logger = setup_logging(__name__, 'historical_data.log')

class HistoricalDataCollector:
    def __init__(self):
        self.api = BinanceAPI()
        self.symbols = SYMBOLS
        self.timeframes = TIMEFRAMES
        self.lookback_days = LOOKBACK_DAYS
        logger.info(f"Khởi tạo HistoricalDataCollector với {len(self.symbols)} symbols và {len(self.timeframes)} timeframes")
    
    def _get_start_end_time(self):
        """Tính toán thời gian bắt đầu và kết thúc cho dữ liệu lịch sử"""
        # Lấy thời gian từ máy chủ Binance để đảm bảo không nằm trong tương lai
        server_time = self.api.get_server_time()
        
        # Chuyển server_time sang datetime để log
        server_datetime = datetime.fromtimestamp(server_time/1000)
        logger.info(f"Thời gian máy chủ Binance: {server_datetime}")
        
        # Đảm bảo lookback_days là số dương
        lookback_days = abs(self.lookback_days)
        if lookback_days != self.lookback_days:
            logger.warning(f"Giá trị LOOKBACK_DAYS ({self.lookback_days}) là âm, đã chuyển thành dương: {lookback_days}")
            self.lookback_days = lookback_days
        
        # Giới hạn lookback_days không vượt quá 7 ngày cho Open Interest
        if lookback_days > 7:
            logger.warning(f"Giá trị LOOKBACK_DAYS ({lookback_days}) vượt quá 7 ngày, đã điều chỉnh thành 7 ngày cho Open Interest")
            lookback_days = 7
        
        # Tính thời gian bắt đầu (lookback_days ngày trước server_time)
        lookback_ms = lookback_days * 24 * 60 * 60 * 1000
        start_timestamp = server_time - lookback_ms
        
        # Sử dụng server_time làm end_timestamp
        end_timestamp = server_time
        
        # Log thời gian đã chuyển đổi để kiểm tra
        start_date = datetime.fromtimestamp(start_timestamp/1000)
        end_date = datetime.fromtimestamp(end_timestamp/1000)
        
        logger.info(f"Timestamps đã điều chỉnh: start={start_timestamp} ({start_date}), end={end_timestamp} ({end_date})")
        
        return start_timestamp, end_timestamp

    def collect_open_interest_data(self):
        """Thu thập dữ liệu Open Interest lịch sử cho tất cả symbols"""
        start_time, end_time = self._get_start_end_time()
        logger.info(f"Thu thập dữ liệu Open Interest từ {datetime.fromtimestamp(start_time/1000)} đến {datetime.fromtimestamp(end_time/1000)}")
        
        result = {}
        for symbol in self.symbols:
            logger.info(f"Đang lấy dữ liệu Open Interest cho {symbol}")
            try:
                # Lấy dữ liệu theo nhiều lần nếu khoảng thời gian lớn
                all_data = []
                current_start = start_time
                
                # Giới hạn số lần request để tránh vòng lặp vô tận
                max_requests = 30
                request_count = 0
                
                while current_start < end_time and request_count < max_requests:
                    # Giới hạn khoảng thời gian mỗi request để tránh lỗi
                    # Giảm xuống 12 giờ thay vì 24 giờ
                    current_end = min(current_start + (1000 * 60 * 60 * 12), end_time)  # Giới hạn 12 giờ mỗi request
                    
                    # In thông tin request để debug
                    start_date = datetime.fromtimestamp(current_start/1000)
                    end_date = datetime.fromtimestamp(current_end/1000)
                    logger.info(f"Request OI: symbol={symbol}, start={start_date}, end={end_date}")
                    
                    # Thêm thời gian chờ trước mỗi request để tránh rate limit
                    time.sleep(1.0)  # Tăng thời gian chờ lên 1 giây
                    
                    # Thử tối đa 3 lần nếu request thất bại
                    retry_count = 0
                    max_retries = 3
                    success = False
                    
                    while retry_count < max_retries and not success:
                        df = self.api.get_open_interest(symbol, period='1h', start_time=current_start, end_time=current_end)
                        
                        if df is not None and not df.empty:
                            all_data.append(df)
                            logger.info(f"Nhận được {len(df)} bản ghi OI cho {symbol}")
                            success = True
                        else:
                            retry_count += 1
                            if retry_count < max_retries:
                                wait_time = 2 ** retry_count  # Backoff exponential: 2, 4, 8 giây
                                logger.warning(f"Lần thử {retry_count}/{max_retries} thất bại, thử lại sau {wait_time} giây")
                                time.sleep(wait_time)
                    
                    if not success:
                        logger.warning(f"Không nhận được dữ liệu OI cho {symbol} trong khoảng {start_date} - {end_date} sau {max_retries} lần thử")
                    
                    # Cập nhật thời gian bắt đầu cho request tiếp theo
                    current_start = current_end
                    request_count += 1
                
                if all_data:
                    # Gộp tất cả dữ liệu
                    result[symbol] = pd.concat(all_data).drop_duplicates()
                    logger.info(f"Đã lấy tổng cộng {len(result[symbol])} mẫu Open Interest cho {symbol}")
                else:
                    logger.warning(f"Không có dữ liệu Open Interest cho {symbol}")
                    result[symbol] = pd.DataFrame()
                    
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu Open Interest cho {symbol}: {str(e)}")
                result[symbol] = pd.DataFrame()
        
        return result
    
    def collect_klines_data(self):
        """Thu thập dữ liệu nến lịch sử cho tất cả symbols và timeframes"""
        start_time, end_time = self._get_start_end_time()
        logger.info(f"Thu thập dữ liệu nến từ {datetime.fromtimestamp(start_time/1000)} đến {datetime.fromtimestamp(end_time/1000)}")
        
        result = {}
        for symbol in self.symbols:
            result[symbol] = {}
            for timeframe in self.timeframes:
                logger.info(f"Đang lấy dữ liệu klines cho {symbol} - {timeframe}")
                try:
                    # Lấy dữ liệu theo nhiều lần nếu khoảng thời gian lớn
                    all_data = []
                    current_start = start_time
                    
                    # Giới hạn số lần request để tránh vòng lặp vô tận
                    max_requests = 30
                    request_count = 0
                    
                    while current_start < end_time and request_count < max_requests:
                        # Tính toán thời gian kết thúc cho mỗi request
                        current_end = min(current_start + (1000 * 60 * 60 * 24), end_time)  # Giới hạn 1 ngày mỗi request
                        
                        logger.info(f"Request klines: symbol={symbol}, timeframe={timeframe}, start={datetime.fromtimestamp(current_start/1000)}, end={datetime.fromtimestamp(current_end/1000)}")
                        
                        df = self.api.get_klines(symbol, timeframe, current_start, current_end)
                        if df is not None and not df.empty:
                            all_data.append(df)
                            logger.info(f"Nhận được {len(df)} nến cho {symbol} - {timeframe}")
                            # Đợi một chút để tránh rate limit
                            time.sleep(0.5)
                        else:
                            logger.warning(f"Không nhận được dữ liệu klines cho {symbol} - {timeframe}")
                        
                        # Cập nhật thời gian bắt đầu cho request tiếp theo
                        current_start = current_end
                        request_count += 1
                    
                    if all_data:
                        # Gộp tất cả dữ liệu
                        result[symbol][timeframe] = pd.concat(all_data).drop_duplicates()
                        logger.info(f"Đã lấy tổng cộng {len(result[symbol][timeframe])} nến cho {symbol} - {timeframe}")
                    else:
                        logger.warning(f"Không có dữ liệu cho {symbol} - {timeframe}")
                        result[symbol][timeframe] = pd.DataFrame()
                except Exception as e:
                    logger.error(f"Lỗi khi lấy dữ liệu klines cho {symbol} - {timeframe}: {str(e)}")
                    result[symbol][timeframe] = pd.DataFrame()
        
        return result
    
    def collect_open_interest_data(self):
        """Thu thập dữ liệu Open Interest lịch sử cho tất cả symbols"""
        start_time, end_time = self._get_start_end_time()
        logger.info(f"Thu thập dữ liệu Open Interest từ {datetime.fromtimestamp(start_time/1000)} đến {datetime.fromtimestamp(end_time/1000)}")
        
        result = {}
        for symbol in self.symbols:
            logger.info(f"Đang lấy dữ liệu Open Interest cho {symbol}")
            try:
                # Lấy dữ liệu theo nhiều lần nếu khoảng thời gian lớn
                all_data = []
                current_start = start_time
                
                # Giới hạn số lần request để tránh vòng lặp vô tận
                max_requests = 30
                request_count = 0
                
                while current_start < end_time and request_count < max_requests:
                    # Giới hạn khoảng thời gian mỗi request để tránh lỗi
                    current_end = min(current_start + (1000 * 60 * 60 * 24), end_time)  # Giới hạn 1 ngày mỗi request
                    
                    # In thông tin request để debug
                    start_date = datetime.fromtimestamp(current_start/1000)
                    end_date = datetime.fromtimestamp(current_end/1000)
                    logger.info(f"Request OI: symbol={symbol}, start={start_date}, end={end_date}")
                    
                    # Thêm thời gian chờ trước mỗi request để tránh rate limit
                    time.sleep(0.5)
                    
                    df = self.api.get_open_interest(symbol, period='1h', start_time=current_start, end_time=current_end)
                    
                    if df is not None and not df.empty:
                        all_data.append(df)
                        logger.info(f"Nhận được {len(df)} bản ghi OI cho {symbol}")
                    else:
                        logger.warning(f"Không nhận được dữ liệu OI cho {symbol} trong khoảng {start_date} - {end_date}")
                    
                    # Cập nhật thời gian bắt đầu cho request tiếp theo
                    current_start = current_end
                    request_count += 1
                
                if all_data:
                    # Gộp tất cả dữ liệu
                    result[symbol] = pd.concat(all_data).drop_duplicates()
                    logger.info(f"Đã lấy tổng cộng {len(result[symbol])} mẫu Open Interest cho {symbol}")
                else:
                    logger.warning(f"Không có dữ liệu Open Interest cho {symbol}")
                    result[symbol] = pd.DataFrame()
                    
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu Open Interest cho {symbol}: {str(e)}")
                result[symbol] = pd.DataFrame()
        
        return result
    
    def collect_all_historical_data(self):
        """Thu thập tất cả dữ liệu lịch sử (klines và open interest)"""
        logger.info("Bắt đầu thu thập tất cả dữ liệu lịch sử")
        
        klines_data = self.collect_klines_data()
        oi_data = self.collect_open_interest_data()
        
        return {
            'klines': klines_data,
            'open_interest': oi_data
        }
    
    def collect_realtime_data(self):
        """Thu thập dữ liệu realtime cho tất cả symbols"""
        logger.info("Thu thập dữ liệu realtime")
        result = {
            'ticker': {},
            'open_interest': {}
        }
        
        for symbol in self.symbols:
            try:
                # Lấy dữ liệu ticker (volume)
                ticker_data = self.api.get_ticker(symbol)
                if ticker_data:
                    result['ticker'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'volume': float(ticker_data['volume']),
                        'quoteVolume': float(ticker_data['quoteVolume']),
                        'count': int(ticker_data['count']),
                        'lastPrice': float(ticker_data['lastPrice']),
                        'priceChangePercent': float(ticker_data['priceChangePercent'])
                    }
                
                # Lấy dữ liệu open interest
                oi_data = self.api.get_open_interest_realtime(symbol)
                if oi_data:
                    result['open_interest'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'openInterest': float(oi_data['openInterest'])
                    }
                
                time.sleep(0.3)  # Đợi một chút để tránh rate limit
            except Exception as e:
                logger.error(f"Lỗi khi lấy dữ liệu realtime cho {symbol}: {str(e)}")
        
        return result