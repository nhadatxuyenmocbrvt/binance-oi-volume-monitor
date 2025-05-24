import pandas as pd
from datetime import datetime, timedelta
import time
from config.settings import SYMBOLS, TIMEFRAMES, LOOKBACK_DAYS, setup_logging
from data_collector.binance_api import OptimizedBinanceAPI

logger = setup_logging(__name__, 'historical_data.log')

class OptimizedHistoricalDataCollector:
    """
    Thu thập dữ liệu lịch sử tối ưu cho OI & Volume
    Focus: 24h tracking (hourly) + 30d tracking (daily)
    """
    
    def __init__(self):
        self.api = OptimizedBinanceAPI()
        self.symbols = SYMBOLS
        self.timeframes = TIMEFRAMES
        self.lookback_days = max(LOOKBACK_DAYS, 7)  # Minimum 7 days
        
        # Test API connection
        if not self.api.test_connection():
            logger.warning("⚠️ API connection test failed, but continuing...")
        
        logger.info(f"🔧 Khởi tạo OptimizedHistoricalDataCollector với {len(self.symbols)} symbols")
        logger.info(f"📊 Symbols: {', '.join(self.symbols)}")
        logger.info(f"⏰ Timeframes: {', '.join(self.timeframes)}")
        logger.info(f"📅 Lookback: {self.lookback_days} days")
    
    def _get_24h_time_range(self):
        """Tính toán thời gian cho dữ liệu 24h theo giờ"""
        server_time = self.api.get_server_time()
        server_datetime = datetime.fromtimestamp(server_time/1000)
        
        # Làm tròn xuống giờ hiện tại
        current_hour = server_datetime.replace(minute=0, second=0, microsecond=0)
        
        # Lấy 24 giờ gần nhất (bao gồm giờ hiện tại)
        start_time = current_hour - timedelta(hours=23)  # 23 giờ trước + giờ hiện tại = 24 điểm
        end_time = current_hour + timedelta(minutes=30)  # Thêm buffer
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        logger.info(f"⏰ 24h range: {start_time.strftime('%Y-%m-%d %H:%M')} → {end_time.strftime('%Y-%m-%d %H:%M')}")
        return start_timestamp, end_timestamp
    
    def _get_30d_time_range(self):
        """Tính toán thời gian cho dữ liệu 30 ngày"""
        server_time = self.api.get_server_time()
        server_datetime = datetime.fromtimestamp(server_time/1000)
        
        # Làm tròn xuống ngày hiện tại
        current_date = server_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Lấy 30 ngày gần nhất
        start_date = current_date - timedelta(days=29)  # 29 ngày trước + ngày hiện tại = 30 ngày
        end_date = current_date + timedelta(days=1)  # Thêm buffer
        
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)
        
        logger.info(f"📅 30d range: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
        return start_timestamp, end_timestamp
    
    def _get_custom_time_range(self, days=None):
        """Tính toán thời gian tuỳ chỉnh"""
        if days is None:
            days = self.lookback_days
            
        server_time = self.api.get_server_time()
        end_timestamp = server_time
        start_timestamp = server_time - (days * 24 * 60 * 60 * 1000)
        
        start_date = datetime.fromtimestamp(start_timestamp/1000)
        end_date = datetime.fromtimestamp(end_timestamp/1000)
        
        logger.info(f"📊 Custom range ({days}d): {start_date.strftime('%Y-%m-%d %H:%M')} → {end_date.strftime('%Y-%m-%d %H:%M')}")
        return start_timestamp, end_timestamp
    
    def collect_24h_hourly_data(self):
        """
        Thu thập dữ liệu 24h theo từng giờ - CORE FUNCTION
        Tối ưu cho tracking OI & Volume theo giờ
        """
        logger.info("🕒 Bắt đầu thu thập dữ liệu 24h hourly - OI & Volume focus")
        start_time, end_time = self._get_24h_time_range()
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': '24h_hourly',
            'klines': {},
            'open_interest': {},
            'success_count': 0,
            'error_count': 0
        }
        
        total_symbols = len(self.symbols)
        
        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"📊 [{i}/{total_symbols}] Thu thập 24h data cho {symbol}")
            
            try:
                # Thu thập klines 1h cho 24h
                logger.info(f"   📈 Collecting 1h klines for {symbol}")
                klines_data = self.api.get_klines(
                    symbol=symbol, 
                    interval='1h', 
                    start_time=start_time, 
                    end_time=end_time, 
                    limit=25  # 24 + 1 buffer
                )
                
                if klines_data is not None and not klines_data.empty:
                    # Lọc chỉ lấy 24 điểm gần nhất
                    klines_data = klines_data.tail(24)
                    result['klines'][symbol] = klines_data
                    logger.info(f"   ✅ {len(klines_data)} klines collected")
                else:
                    logger.warning(f"   ⚠️ No klines data for {symbol}")
                    result['klines'][symbol] = pd.DataFrame()
                
                # Rate limiting between API calls
                time.sleep(0.3)
                
                # Thu thập Open Interest 1h cho 24h
                logger.info(f"   📊 Collecting 1h OI for {symbol}")
                oi_data = self.api.get_open_interest(
                    symbol=symbol, 
                    period='1h', 
                    start_time=start_time, 
                    end_time=end_time, 
                    limit=25
                )
                
                if oi_data is not None and not oi_data.empty:
                    # Lọc chỉ lấy 24 điểm gần nhất
                    oi_data = oi_data.tail(24)
                    result['open_interest'][symbol] = oi_data
                    logger.info(f"   ✅ {len(oi_data)} OI points collected")
                else:
                    logger.warning(f"   ⚠️ No OI data for {symbol}")
                    result['open_interest'][symbol] = pd.DataFrame()
                
                result['success_count'] += 1
                logger.info(f"   🎯 {symbol}: Success")
                
                # Rate limiting between symbols
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"   ❌ Error collecting 24h data for {symbol}: {str(e)}")
                result['klines'][symbol] = pd.DataFrame()
                result['open_interest'][symbol] = pd.DataFrame()
                result['error_count'] += 1
        
        logger.info(f"✅ 24h collection complete: {result['success_count']}/{total_symbols} success, {result['error_count']} errors")
        return result
    
    def collect_30d_daily_data(self):
        """
        Thu thập dữ liệu 30 ngày daily - CORE FUNCTION  
        Tối ưu cho tracking OI & Volume theo ngày
        """
        logger.info("📅 Bắt đầu thu thập dữ liệu 30d daily - OI & Volume focus")
        start_time, end_time = self._get_30d_time_range()
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': '30d_daily',
            'klines': {},
            'open_interest': {},
            'success_count': 0,
            'error_count': 0
        }
        
        total_symbols = len(self.symbols)
        
        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"📊 [{i}/{total_symbols}] Thu thập 30d data cho {symbol}")
            
            try:
                # Thu thập klines 1d cho 30 ngày
                logger.info(f"   📈 Collecting daily klines for {symbol}")
                klines_data = self.api.get_klines(
                    symbol=symbol, 
                    interval='1d', 
                    start_time=start_time, 
                    end_time=end_time, 
                    limit=31  # 30 + 1 buffer
                )
                
                if klines_data is not None and not klines_data.empty:
                    # Lọc chỉ lấy 30 ngày gần nhất
                    klines_data = klines_data.tail(30)
                    result['klines'][symbol] = klines_data
                    logger.info(f"   ✅ {len(klines_data)} daily klines collected")
                else:
                    logger.warning(f"   ⚠️ No daily klines for {symbol}")
                    result['klines'][symbol] = pd.DataFrame()
                
                # Rate limiting
                time.sleep(0.3)
                
                # Thu thập Open Interest (chunked cho 30 ngày)
                logger.info(f"   📊 Collecting 30d OI for {symbol}")
                oi_data = self.api.get_open_interest_chunked(
                    symbol=symbol, 
                    period='1h',  # Lấy hourly rồi aggregate về daily
                    start_time=start_time, 
                    end_time=end_time,
                    days_per_chunk=10  # 10 ngày per chunk để tránh rate limit
                )
                
                if oi_data is not None and not oi_data.empty:
                    # Aggregate hourly OI to daily
                    oi_daily = self._aggregate_oi_to_daily(oi_data)
                    result['open_interest'][symbol] = oi_daily
                    logger.info(f"   ✅ {len(oi_daily)} daily OI points collected")
                else:
                    logger.warning(f"   ⚠️ No OI data for {symbol}")
                    result['open_interest'][symbol] = pd.DataFrame()
                
                result['success_count'] += 1
                logger.info(f"   🎯 {symbol}: Success")
                
                # Rate limiting between symbols
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"   ❌ Error collecting 30d data for {symbol}: {str(e)}")
                result['klines'][symbol] = pd.DataFrame()
                result['open_interest'][symbol] = pd.DataFrame()
                result['error_count'] += 1
        
        logger.info(f"✅ 30d collection complete: {result['success_count']}/{total_symbols} success, {result['error_count']} errors")
        return result
    
    def collect_realtime_data(self):
        """
        Thu thập dữ liệu realtime cho tất cả symbols
        Tối ưu cho cập nhật tracking
        """
        logger.info("⚡ Thu thập dữ liệu realtime cho tracking")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'data_type': 'realtime',
            'ticker': {},
            'open_interest': {},
            'success_count': 0,
            'error_count': 0
        }
        
        total_symbols = len(self.symbols)
        
        for i, symbol in enumerate(self.symbols, 1):
            try:
                logger.info(f"⚡ [{i}/{total_symbols}] Realtime data for {symbol}")
                
                # Lấy ticker data (volume, price)
                ticker_data = self.api.get_ticker(symbol)
                if ticker_data:
                    result['ticker'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'volume': float(ticker_data['volume']),
                        'quoteVolume': float(ticker_data['quoteVolume']),
                        'count': int(ticker_data['count']),
                        'lastPrice': float(ticker_data['lastPrice']),
                        'priceChangePercent': float(ticker_data['priceChangePercent']),
                        'openPrice': float(ticker_data['openPrice']),
                        'highPrice': float(ticker_data['highPrice']),
                        'lowPrice': float(ticker_data['lowPrice'])
                    }
                    logger.info(f"   📈 Ticker: {ticker_data['lastPrice']} ({ticker_data['priceChangePercent']}%)")
                
                # Rate limiting
                time.sleep(0.2)
                
                # Lấy Open Interest current
                oi_data = self.api.get_open_interest_realtime(symbol)
                if oi_data:
                    result['open_interest'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'openInterest': float(oi_data['openInterest'])
                    }
                    logger.info(f"   📊 OI: {oi_data['openInterest']}")
                
                result['success_count'] += 1
                
                # Rate limiting between symbols
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"   ❌ Error getting realtime data for {symbol}: {str(e)}")
                result['error_count'] += 1
        
        logger.info(f"✅ Realtime collection: {result['success_count']}/{total_symbols} success")
        return result
    
    def collect_klines_data(self, custom_timeframes=None, custom_days=None):
        """
        Thu thập dữ liệu klines lịch sử theo timeframes
        """
        timeframes = custom_timeframes or self.timeframes
        start_time, end_time = self._get_custom_time_range(custom_days)
        
        logger.info(f"📈 Thu thập klines data cho {len(timeframes)} timeframes")
        
        result = {}
        total_items = len(self.symbols) * len(timeframes)
        current_item = 0
        
        for symbol in self.symbols:
            result[symbol] = {}
            
            for timeframe in timeframes:
                current_item += 1
                logger.info(f"📊 [{current_item}/{total_items}] {symbol} - {timeframe}")
                
                try:
                    # Sử dụng chunked collection cho timeframes nhỏ
                    if timeframe in ['1m', '3m', '5m', '15m', '30m']:
                        df = self.api.get_klines_chunked(
                            symbol=symbol,
                            interval=timeframe,
                            start_time=start_time,
                            end_time=end_time,
                            chunk_size=1000
                        )
                    else:
                        df = self.api.get_klines(
                            symbol=symbol,
                            interval=timeframe,
                            start_time=start_time,
                            end_time=end_time,
                            limit=1000
                        )
                    
                    if df is not None and not df.empty:
                        result[symbol][timeframe] = df
                        logger.info(f"   ✅ {len(df)} candles collected")
                    else:
                        logger.warning(f"   ⚠️ No data for {symbol} {timeframe}")
                        result[symbol][timeframe] = pd.DataFrame()
                    
                    # Rate limiting
                    time.sleep(0.4)
                    
                except Exception as e:
                    logger.error(f"   ❌ Error: {str(e)}")
                    result[symbol][timeframe] = pd.DataFrame()
        
        logger.info("✅ Klines collection complete")
        return result
    
    def collect_open_interest_data(self, custom_days=None):
        """
        Thu thập dữ liệu Open Interest lịch sử
        """
        days = custom_days or min(self.lookback_days, 30)  # Max 30 days
        start_time, end_time = self._get_custom_time_range(days)
        
        logger.info(f"📊 Thu thập OI data cho {days} ngày")
        
        result = {}
        
        for i, symbol in enumerate(self.symbols, 1):
            logger.info(f"📊 [{i}/{len(self.symbols)}] OI for {symbol}")
            
            try:
                # Sử dụng chunked collection để lấy nhiều dữ liệu
                df = self.api.get_open_interest_chunked(
                    symbol=symbol,
                    period='1h',
                    start_time=start_time,
                    end_time=end_time,
                    days_per_chunk=7  # 7 days per chunk
                )
                
                if df is not None and not df.empty:
                    result[symbol] = df
                    logger.info(f"   ✅ {len(df)} OI points collected")
                else:
                    logger.warning(f"   ⚠️ No OI data for {symbol}")
                    result[symbol] = pd.DataFrame()
                
                # Rate limiting between symbols
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"   ❌ Error: {str(e)}")
                result[symbol] = pd.DataFrame()
        
        logger.info("✅ OI collection complete")
        return result
    
    def collect_all_historical_data(self, mode='full'):
        """
        Thu thập tất cả dữ liệu lịch sử
        mode: 'full', 'klines_only', 'oi_only'
        """
        logger.info(f"📚 Bắt đầu thu thập dữ liệu lịch sử - mode: {mode}")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'mode': mode,
            'klines': {},
            'open_interest': {}
        }
        
        if mode in ['full', 'klines_only']:
            logger.info("📈 Collecting klines data...")
            result['klines'] = self.collect_klines_data()
        
        if mode in ['full', 'oi_only']:
            logger.info("📊 Collecting OI data...")
            result['open_interest'] = self.collect_open_interest_data()
        
        logger.info("✅ All historical data collection complete")
        return result
    
    # Helper methods
    def _aggregate_oi_to_daily(self, oi_hourly_df):
        """
        Aggregate hourly OI data to daily
        """
        if oi_hourly_df.empty:
            return pd.DataFrame()
        
        try:
            # Tạo date column
            oi_hourly_df['date'] = oi_hourly_df['timestamp'].dt.date
            
            # Group by date và tính average OI cho mỗi ngày
            daily_oi = oi_hourly_df.groupby('date').agg({
                'sumOpenInterest': 'mean',  # Average OI trong ngày
                'sumOpenInterestValue': 'mean',
                'timestamp': 'first'  # Lấy timestamp đầu tiên của ngày
            }).reset_index()
            
            # Rename columns
            daily_oi = daily_oi.rename(columns={
                'sumOpenInterest': 'avg_open_interest',
                'sumOpenInterestValue': 'avg_open_interest_value'
            })
            
            # Sort by date
            daily_oi = daily_oi.sort_values('date').reset_index(drop=True)
            
            logger.info(f"📊 Aggregated {len(oi_hourly_df)} hourly points to {len(daily_oi)} daily points")
            return daily_oi
            
        except Exception as e:
            logger.error(f"❌ Error aggregating OI to daily: {str(e)}")
            return pd.DataFrame()
    
    def get_data_summary(self):
        """
        Lấy tóm tắt dữ liệu có sẵn
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'symbols': self.symbols,
            'timeframes': self.timeframes,
            'lookback_days': self.lookback_days,
            'api_status': 'connected' if self.api.test_connection() else 'disconnected'
        }
        
        logger.info(f"📋 Data summary: {len(self.symbols)} symbols, {len(self.timeframes)} timeframes")
        return summary
    
    def validate_data_quality(self, data):
        """
        Kiểm tra chất lượng dữ liệu
        """
        quality_report = {
            'timestamp': datetime.now().isoformat(),
            'symbols_with_data': 0,
            'symbols_without_data': 0,
            'total_klines_points': 0,
            'total_oi_points': 0,
            'issues': []
        }
        
        if 'klines' in data:
            for symbol, timeframe_data in data['klines'].items():
                has_data = False
                for timeframe, df in timeframe_data.items():
                    if not df.empty:
                        has_data = True
                        quality_report['total_klines_points'] += len(df)
                
                if has_data:
                    quality_report['symbols_with_data'] += 1
                else:
                    quality_report['symbols_without_data'] += 1
                    quality_report['issues'].append(f"No klines data for {symbol}")
        
        if 'open_interest' in data:
            for symbol, df in data['open_interest'].items():
                if not df.empty:
                    quality_report['total_oi_points'] += len(df)
                else:
                    quality_report['issues'].append(f"No OI data for {symbol}")
        
        logger.info(f"📊 Data quality: {quality_report['symbols_with_data']} symbols OK, {len(quality_report['issues'])} issues")
        return quality_report

# Backward compatibility
HistoricalDataCollector = OptimizedHistoricalDataCollector