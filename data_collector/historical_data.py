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
        end_time = current_hour + timedelta(minutes=5)  # Thêm buffer
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        logger.info(f"⏰ 24h range: {start_time.strftime('%Y-%m-%d %H:%M')} → {current_hour.strftime('%Y-%m-%d %H:%M')}")
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
    
    # Hàm cải thiện để xử lý dữ liệu klines, đảm bảo luôn có quote_volume
    def _process_klines_data(self, data):
        """Xử lý dữ liệu klines thành DataFrame và đảm bảo có quote_volume"""
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
        
        # ĐẢM BẢO quote_volume luôn có giá trị
        if 'quote_volume' not in df.columns or df['quote_volume'].isnull().any():
            df['quote_volume'] = df['volume'] * df['close']
            logger.info(f"🔄 Tính toán quote_volume từ volume và giá cho {len(df)} klines")
        
        # Log sample data để debug
        if not df.empty:
            logger.info(f"📊 Sample volume (contracts): {df['volume'].iloc[0]}, Quote volume (USDT): {df['quote_volume'].iloc[0]}")
        
        return df
    
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
                    limit=30  # Tăng từ 25 lên 30 để đủ dữ liệu
                )
                
                if klines_data is not None and not klines_data.empty:
                    # Kiểm tra kỹ lưỡng số lượng điểm dữ liệu
                    expected_hours = set()
                    current_hour = datetime.fromtimestamp(end_time/1000).replace(minute=0, second=0, microsecond=0)
                    
                    for i in range(24):
                        hour = current_hour - timedelta(hours=i)
                        expected_hours.add(hour.strftime('%Y-%m-%d %H:00:00'))
                    
                    # Chuyển timestamp thành format chuẩn để so sánh
                    if 'open_time' in klines_data.columns:
                        klines_data['hour_str'] = pd.to_datetime(klines_data['open_time']).dt.strftime('%Y-%m-%d %H:00:00')
                        
                        # Lọc chỉ lấy 24 giờ cần thiết
                        filtered_klines = klines_data[klines_data['hour_str'].isin(expected_hours)]
                        
                        if len(filtered_klines) < 24:
                            logger.warning(f"   ⚠️ Chỉ thu được {len(filtered_klines)}/24 điểm klines cho {symbol}")
                        
                        # Đảm bảo có quote_volume (USDT)
                        if 'quote_volume' not in filtered_klines.columns or filtered_klines['quote_volume'].isnull().any():
                            filtered_klines = filtered_klines.copy()
                            filtered_klines['quote_volume'] = filtered_klines['volume'] * filtered_klines['close']
                            logger.info(f"   🔄 Đã tính toán quote_volume cho {symbol} klines")
                        
                        # Log để kiểm tra quote_volume
                        if not filtered_klines.empty:
                            logger.info(f"   📊 {symbol} Quote volume gần nhất: {filtered_klines['quote_volume'].iloc[-1]:,.2f} USDT")
                        
                        result['klines'][symbol] = filtered_klines
                        logger.info(f"   ✅ {len(filtered_klines)}/{24} klines collected")
                    else:
                        # Lọc chỉ lấy 24 điểm gần nhất
                        if len(klines_data) > 24:
                            klines_data = klines_data.tail(24)
                        result['klines'][symbol] = klines_data
                        logger.info(f"   ✅ {len(klines_data)} klines collected")
                else:
                    logger.warning(f"   ⚠️ No klines data for {symbol}")
                    result['klines'][symbol] = pd.DataFrame()
                
                # Rate limiting between API calls
                time.sleep(0.5)  # Tăng thời gian chờ
                
                # Thu thập Open Interest chi tiết hơn cho 24h
                logger.info(f"   📊 Collecting 1h OI for {symbol}")
                
                # Tăng limit và thử thu thập theo từng chunk
                oi_data = None
                
                # Thử 3 phương pháp khác nhau
                for attempt in range(1, 4):
                    try:
                        if attempt == 1:
                            # Phương pháp 1: Lấy trực tiếp với limit cao
                            oi_data = self.api.get_open_interest(
                                symbol=symbol, 
                                period='1h', 
                                start_time=start_time, 
                                end_time=end_time, 
                                limit=50  # Tăng limit
                            )
                        elif attempt == 2:
                            # Phương pháp 2: Chia thành 2 chunk
                            mid_time = start_time + (end_time - start_time) // 2
                            
                            oi_data_1 = self.api.get_open_interest(
                                symbol=symbol, 
                                period='1h', 
                                start_time=start_time, 
                                end_time=mid_time, 
                                limit=30
                            )
                            
                            time.sleep(0.5)
                            
                            oi_data_2 = self.api.get_open_interest(
                                symbol=symbol, 
                                period='1h', 
                                start_time=mid_time+1, 
                                end_time=end_time, 
                                limit=30
                            )
                            
                            if oi_data_1 is not None and oi_data_2 is not None:
                                oi_data = pd.concat([oi_data_1, oi_data_2]).drop_duplicates()
                        else:
                            # Phương pháp 3: Sử dụng chunked API
                            oi_data = self.api.get_open_interest_chunked(
                                symbol=symbol,
                                period='1h',
                                start_time=start_time,
                                end_time=end_time,
                                days_per_chunk=1
                            )
                        
                        # Kiểm tra kết quả
                        if oi_data is not None and not oi_data.empty and len(oi_data) >= 20:
                            # Có đủ dữ liệu, thoát khỏi vòng lặp
                            logger.info(f"   ✅ Thu thập OI thành công bằng phương pháp {attempt}")
                            break
                        
                        # Không đủ dữ liệu, thử phương pháp tiếp theo
                        logger.warning(f"   ⚠️ Phương pháp {attempt} chỉ thu được {len(oi_data) if oi_data is not None else 0} điểm")
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"   ❌ Lỗi khi thu thập OI bằng phương pháp {attempt}: {str(e)}")
                        time.sleep(0.5)
                
                if oi_data is not None and not oi_data.empty:
                    # Lọc và kiểm tra như với klines
                    expected_hours = set()
                    current_hour = datetime.fromtimestamp(end_time/1000).replace(minute=0, second=0, microsecond=0)
                    
                    for i in range(24):
                        hour = current_hour - timedelta(hours=i)
                        expected_hours.add(hour.strftime('%Y-%m-%d %H:00:00'))
                    
                    # Chuyển timestamp thành format chuẩn để so sánh
                    if 'timestamp' in oi_data.columns:
                        oi_data['hour_str'] = pd.to_datetime(oi_data['timestamp']).dt.strftime('%Y-%m-%d %H:00:00')
                        
                        # Lọc chỉ lấy 24 giờ cần thiết
                        filtered_oi = oi_data[oi_data['hour_str'].isin(expected_hours)]
                        
                        if len(filtered_oi) < 24:
                            logger.warning(f"   ⚠️ Chỉ thu được {len(filtered_oi)}/24 điểm OI cho {symbol}")
                        
                        # ĐẢM BẢO có cột sumOpenInterestValue - tính từ giá nếu cần
                        if 'sumOpenInterestValue' not in filtered_oi.columns and 'sumOpenInterest' in filtered_oi.columns:
                            # Cần giá để tính giá trị USDT
                            if symbol in result['klines'] and not result['klines'][symbol].empty:
                                # Map giá theo timestamp
                                price_data = result['klines'][symbol]
                                price_map = {}
                                
                                for idx, row in price_data.iterrows():
                                    hour_key = pd.to_datetime(row['open_time']).strftime('%Y-%m-%d %H:00:00')
                                    price_map[hour_key] = row['close']
                                
                                # Thêm giá vào filtered_oi
                                filtered_oi = filtered_oi.copy()
                                filtered_oi['price'] = filtered_oi['hour_str'].map(price_map)
                                
                                # Tính sumOpenInterestValue
                                filtered_oi['sumOpenInterestValue'] = filtered_oi['sumOpenInterest'] * filtered_oi['price']
                                logger.info(f"   🔄 Đã tính toán OI Value cho {symbol}")
                            else:
                                logger.warning(f"   ⚠️ Không có dữ liệu giá để tính OI Value cho {symbol}")
                                # Sử dụng sumOpenInterest làm fallback
                                filtered_oi = filtered_oi.copy()
                                filtered_oi['sumOpenInterestValue'] = filtered_oi['sumOpenInterest']
                        
                        # Log để kiểm tra OI value
                        if not filtered_oi.empty and 'sumOpenInterestValue' in filtered_oi.columns:
                            logger.info(f"   📊 {symbol} OI value gần nhất: {filtered_oi['sumOpenInterestValue'].iloc[-1]:,.2f} USDT")
                        
                        result['open_interest'][symbol] = filtered_oi
                        logger.info(f"   ✅ {len(filtered_oi)}/{24} OI points collected")
                    else:
                        # Lọc chỉ lấy 24 điểm gần nhất
                        if len(oi_data) > 24:
                            oi_data = oi_data.tail(24)
                        result['open_interest'][symbol] = oi_data
                        logger.info(f"   ✅ {len(oi_data)} OI points collected")
                else:
                    logger.warning(f"   ⚠️ No OI data for {symbol}")
                    result['open_interest'][symbol] = pd.DataFrame()
                
                result['success_count'] += 1
                logger.info(f"   🎯 {symbol}: Success")
                
                # Rate limiting between symbols
                time.sleep(1.0)  # Tăng thời gian chờ
                
            except Exception as e:
                logger.error(f"   ❌ Error collecting 24h data for {symbol}: {str(e)}")
                result['klines'][symbol] = pd.DataFrame()
                result['open_interest'][symbol] = pd.DataFrame()
                result['error_count'] += 1
        
        logger.info(f"✅ 24h collection complete: {result['success_count']}/{total_symbols} success, {result['error_count']} errors")
        return result
    
    def collect_30d_daily_data(self):
        """Thu thập dữ liệu 30 ngày daily"""
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
                # Thu thập klines 1d cho 30 ngày với số lượng dữ liệu lớn hơn
                logger.info(f"   📈 Collecting daily klines for {symbol}")
                klines_data = self.api.get_klines(
                    symbol=symbol, 
                    interval='1d', 
                    start_time=start_time, 
                    end_time=end_time, 
                    limit=100  # Tăng limit lên để đảm bảo có đủ dữ liệu
                )
                
                if klines_data is not None and not klines_data.empty:
                    # Đảm bảo đúng 30 ngày gần nhất
                    if len(klines_data) > 30:
                        klines_data = klines_data.tail(30)
                    
                    # Đảm bảo quote_volume được lưu đúng
                    if 'quote_volume' not in klines_data.columns or klines_data['quote_volume'].isnull().any():
                        klines_data = klines_data.copy()
                        klines_data['quote_volume'] = klines_data['volume'] * klines_data['close']
                        logger.info(f"   🔄 Đã tính toán quote_volume cho {symbol} daily klines")
                    
                    # Log để kiểm tra giá trị
                    logger.info(f"   🔍 Kiểm tra giá trị: Volume ngày gần nhất = {klines_data['volume'].iloc[-1]:,.2f}, " +
                            f"Quote Volume = {klines_data['quote_volume'].iloc[-1]:,.2f} USDT")
                    
                    result['klines'][symbol] = klines_data
                    logger.info(f"   ✅ {len(klines_data)} daily klines collected")
                else:
                    logger.warning(f"   ⚠️ No daily klines for {symbol}")
                    result['klines'][symbol] = pd.DataFrame()
                
                # Rate limiting
                time.sleep(0.5)
                
                # Chiến lược thu thập OI 30 ngày
                # Sử dụng phương pháp 3 bước:
                # 1. Cố gắng lấy OI theo ngày với chunk nhỏ hơn
                # 2. Nếu thất bại, lấy dữ liệu 1h cho 7 ngày gần nhất
                # 3. Lấy dữ liệu 8h hoặc 4h cho phần còn lại (23 ngày)
                
                logger.info(f"   📊 Collecting 30d OI for {symbol} (phương pháp mới)")
                
                # Bước 1: Thử lấy OI theo ngày với chunk nhỏ hơn
                oi_data = self.api.get_open_interest_chunked(
                    symbol=symbol, 
                    period='1d',
                    start_time=start_time, 
                    end_time=end_time,
                    days_per_chunk=3  # Giảm kích thước chunk
                )
                
                if oi_data is not None and not oi_data.empty and len(oi_data) >= 15:
                    # Nếu có ít nhất 15 ngày dữ liệu, sử dụng nó
                    # Đảm bảo có openInterestValue (USDT)
                    if 'sumOpenInterestValue' not in oi_data.columns and 'sumOpenInterest' in oi_data.columns:
                        # Cần giá để tính OI value
                        if symbol in result['klines'] and not result['klines'][symbol].empty:
                            klines_df = result['klines'][symbol]
                            oi_data = oi_data.copy()
                            
                            # Tạo mapping giữa ngày và giá
                            price_map = {}
                            for idx, row in klines_df.iterrows():
                                date_key = pd.to_datetime(row['open_time']).strftime('%Y-%m-%d')
                                price_map[date_key] = row['close']
                            
                            # Chuyển timestamp thành ngày và map với giá
                            oi_data['date'] = pd.to_datetime(oi_data['timestamp']).dt.strftime('%Y-%m-%d')
                            oi_data['price'] = oi_data['date'].map(price_map)
                            
                            # Tính sumOpenInterestValue
                            oi_data['sumOpenInterestValue'] = oi_data['sumOpenInterest'] * oi_data['price']
                            logger.info(f"   🔄 Đã tính toán OI Value cho {symbol} daily OI")
                        else:
                            logger.warning(f"   ⚠️ Không có dữ liệu giá để tính OI Value cho {symbol}")
                            oi_data['sumOpenInterestValue'] = oi_data['sumOpenInterest']  # Fallback
                    
                    # Log để kiểm tra OI value
                    if 'sumOpenInterestValue' in oi_data.columns:
                        logger.info(f"   📊 {symbol} daily OI value: {oi_data['sumOpenInterestValue'].iloc[-1]:,.2f} USDT")
                    
                    result['open_interest'][symbol] = oi_data
                    logger.info(f"   ✅ {len(oi_data)} daily OI points collected (phương pháp 1)")
                else:
                    # Bước 2: Lấy dữ liệu 1h cho 7 ngày gần nhất
                    logger.info(f"   ⚠️ Không đủ dữ liệu OI theo ngày, chuyển sang phương pháp 2+3")
                    
                    # Tính thời gian cho 7 ngày gần nhất
                    recent_end_time = end_time
                    recent_start_time = end_time - (7 * 24 * 60 * 60 * 1000)
                    
                    # Lấy dữ liệu 1h cho 7 ngày gần nhất
                    oi_recent = self.api.get_open_interest_chunked(
                        symbol=symbol, 
                        period='1h',
                        start_time=recent_start_time, 
                        end_time=recent_end_time,
                        days_per_chunk=1  # Lấy từng ngày một
                    )
                    
                    # Tính thời gian cho 23 ngày còn lại
                    older_end_time = recent_start_time - 1
                    older_start_time = start_time
                    
                    # Bước 3: Lấy dữ liệu 8h hoặc 4h cho 23 ngày còn lại
                    oi_older = self.api.get_open_interest_chunked(
                        symbol=symbol, 
                        period='8h',  # Sử dụng 8h để giảm số lượng request
                        start_time=older_start_time, 
                        end_time=older_end_time,
                        days_per_chunk=3
                    )
                    
                    # Nếu vẫn không có dữ liệu, thử với 4h
                    if oi_older is None or oi_older.empty:
                        oi_older = self.api.get_open_interest_chunked(
                            symbol=symbol, 
                            period='4h',
                            start_time=older_start_time, 
                            end_time=older_end_time,
                            days_per_chunk=2
                        )
                    
                    # Tổng hợp dữ liệu
                    oi_complete = pd.DataFrame()
                    
                    # Tổng hợp dữ liệu 7 ngày gần nhất theo ngày
                    if oi_recent is not None and not oi_recent.empty:
                        oi_recent_daily = self._aggregate_oi_to_daily(oi_recent)
                        oi_complete = pd.concat([oi_complete, oi_recent_daily])
                    
                    # Tổng hợp dữ liệu 23 ngày còn lại theo ngày
                    if oi_older is not None and not oi_older.empty:
                        oi_older_daily = self._aggregate_oi_to_daily(oi_older)
                        oi_complete = pd.concat([oi_complete, oi_older_daily])
                    
                    # Sắp xếp theo thời gian và loại bỏ các mục trùng lặp
                    if not oi_complete.empty:
                        oi_complete = oi_complete.sort_values('date').drop_duplicates('date')
                        
                        # Kiểm tra xem có đủ cột cần thiết không
                        if 'sumOpenInterestValue' not in oi_complete.columns and symbol in result['klines']:
                            logger.warning(f"   ⚠️ Thiếu cột sumOpenInterestValue cho {symbol}, đang tính toán")
                            
                            # Tạo price map từ klines để tính giá trị USDT
                            klines_df = result['klines'][symbol]
                            price_map = {}
                            
                            for idx, row in klines_df.iterrows():
                                date_key = pd.to_datetime(row['open_time']).strftime('%Y-%m-%d')
                                price_map[date_key] = row['close']
                            
                            # Tính sumOpenInterestValue
                            oi_complete = oi_complete.copy()
                            oi_complete['date_str'] = oi_complete['date'].astype(str)
                            oi_complete['price'] = oi_complete['date_str'].map(price_map)
                            
                            if 'sumOpenInterest' in oi_complete.columns:
                                oi_complete['sumOpenInterestValue'] = oi_complete.apply(
                                    lambda row: row['sumOpenInterest'] * row['price'] if pd.notnull(row['price']) else row['sumOpenInterest'],
                                    axis=1
                                )
                            
                            # Xóa các cột tạm thời
                            if 'date_str' in oi_complete.columns:
                                oi_complete = oi_complete.drop('date_str', axis=1)
                        
                        # Log để kiểm tra giá trị OI
                        if 'sumOpenInterestValue' in oi_complete.columns:
                            logger.info(f"   📊 {symbol} tổng hợp OI value: {oi_complete['sumOpenInterestValue'].iloc[-1]:,.2f} USDT")
                        
                        result['open_interest'][symbol] = oi_complete
                        logger.info(f"   ✅ {len(oi_complete)} daily OI points collected (phương pháp tổng hợp)")
                    else:
                        logger.warning(f"   ⚠️ Không thể thu thập dữ liệu OI cho {symbol}")
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
        Tối ưu cho cập nhật tracking - ĐẢM BẢO DÙNG QUOTE VOLUME
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
                    # ĐẢM BẢO lưu cả volume (contracts) và quoteVolume (USDT)
                    volume = float(ticker_data['volume'])
                    quote_volume = float(ticker_data['quoteVolume'])  # Giá trị USDT
                    price = float(ticker_data['lastPrice'])
                    
                    # Log để kiểm tra
                    logger.info(f"   ✓ Ticker: price={price}, volume={volume:,.0f} contracts, " +
                               f"quoteVolume={quote_volume:,.2f} USDT")
                    
                    # Kiểm tra tính hợp lệ của quote_volume
                    expected_quote = volume * price
                    ratio = quote_volume / expected_quote if expected_quote > 0 else 0
                    
                    if ratio < 0.5 or ratio > 2.0:
                        logger.warning(f"   ⚠️ Có thể sai quote_volume: {quote_volume:,.2f} USDT " +
                                     f"(dự kiến: {expected_quote:,.2f} USDT), ratio={ratio:.2f}")
                        
                        # Nếu sai lệch quá lớn, tính lại quote_volume
                        if ratio < 0.01 or ratio > 100:
                            logger.warning(f"   ⚠️ Sai lệch quá lớn, tính lại quote_volume")
                            quote_volume = volume * price
                    
                    result['ticker'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'volume': volume,  # Contracts
                        'quoteVolume': quote_volume,  # USDT
                        'count': int(ticker_data['count']),
                        'lastPrice': price,
                        'priceChangePercent': float(ticker_data['priceChangePercent'])
                    }
                    logger.info(f"   📈 Saved Ticker: {price} ({ticker_data['priceChangePercent']}%), " +
                              f"Quote Volume: {quote_volume:,.2f} USDT")
                
                # Rate limiting
                time.sleep(0.2)
                
                # Lấy Open Interest current
                oi_data = self.api.get_open_interest_realtime(symbol)
                if oi_data:
                    open_interest = float(oi_data['openInterest'])  # Contracts
                    # Đảm bảo có open_interest_value (USDT)
                    if 'openInterestValue' not in oi_data or float(oi_data.get('openInterestValue', 0)) <= 0:
                        # Nếu không có, tính từ contracts và giá
                        price = float(ticker_data['lastPrice']) if ticker_data else 0
                        if price > 0:
                            open_interest_value = open_interest * price
                            logger.info(f"   ✓ Tính OI value: {open_interest:,.0f} contracts * {price} = {open_interest_value:,.2f} USDT")
                        else:
                            # Nếu không có giá, không thể tính USDT value
                            open_interest_value = open_interest  # Fallback không chính xác
                            logger.warning(f"   ⚠️ Không thể tính OI value, không có giá")
                    else:
                        open_interest_value = float(oi_data['openInterestValue'])
                    
                    result['open_interest'][symbol] = {
                        'symbol': symbol,
                        'timestamp': datetime.now(),
                        'openInterest': open_interest,  # Contracts
                        'openInterestValue': open_interest_value  # USDT
                    }
                    logger.info(f"   📊 OI: {open_interest:,.0f} contracts, " +
                              f"Value: {open_interest_value:,.2f} USDT")
                
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
                        # Đảm bảo có quote_volume (USDT)
                        if 'quote_volume' not in df.columns or df['quote_volume'].isnull().any():
                            df = df.copy()
                            df['quote_volume'] = df['volume'] * df['close']
                            logger.info(f"   🔄 Đã tính toán quote_volume cho {symbol} {timeframe}")
                        
                        # Log để kiểm tra quote_volume
                        if not df.empty:
                            logger.info(f"   📊 {symbol} {timeframe} Quote volume gần nhất: {df['quote_volume'].iloc[-1]:,.2f} USDT")
                        
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
                # Cải thiện chiến lược thu thập dữ liệu
                # Tách thành 2 phần: 7 ngày gần nhất và phần còn lại
                
                # Phần 1: 7 ngày gần nhất với period='1h'
                recent_end_time = end_time
                recent_start_time = end_time - (7 * 24 * 60 * 60 * 1000)
                
                recent_oi = self.api.get_open_interest_chunked(
                    symbol=symbol,
                    period='1h',
                    start_time=recent_start_time,
                    end_time=recent_end_time,
                    days_per_chunk=1  # Lấy từng ngày một
                )
                
                # Phần 2: Phần còn lại với period='4h' hoặc '8h'
                if days > 7:
                    older_end_time = recent_start_time - 1
                    older_start_time = start_time
                    
                    older_oi = self.api.get_open_interest_chunked(
                        symbol=symbol,
                        period='4h',
                        start_time=older_start_time,
                        end_time=older_end_time,
                        days_per_chunk=2
                    )
                    
                    # Nếu không có dữ liệu, thử với 8h
                    if older_oi is None or older_oi.empty:
                        older_oi = self.api.get_open_interest_chunked(
                            symbol=symbol,
                            period='8h',
                            start_time=older_start_time,
                            end_time=older_end_time,
                            days_per_chunk=3
                        )
                    
                    # Kết hợp cả hai phần
                    if recent_oi is not None and not recent_oi.empty:
                        if older_oi is not None and not older_oi.empty:
                            combined_oi = pd.concat([older_oi, recent_oi])
                        else:
                            combined_oi = recent_oi
                    else:
                        combined_oi = older_oi if older_oi is not None else pd.DataFrame()
                else:
                    combined_oi = recent_oi if recent_oi is not None else pd.DataFrame()
                
                # Sắp xếp và loại bỏ trùng lặp
                if combined_oi is not None and not combined_oi.empty:
                    # Đảm bảo có sumOpenInterestValue (USDT)
                    if 'sumOpenInterestValue' not in combined_oi.columns and 'sumOpenInterest' in combined_oi.columns:
                        # Cần lấy giá để tính giá trị USDT - có thể từ API hoặc ước tính
                        try:
                            # Lấy giá hiện tại
                            ticker_data = self.api.get_ticker(symbol)
                            if ticker_data:
                                price = float(ticker_data['lastPrice'])
                                combined_oi = combined_oi.copy()
                                combined_oi['sumOpenInterestValue'] = combined_oi['sumOpenInterest'] * price
                                logger.info(f"   🔄 Đã ước tính OI Value cho {symbol} bằng giá hiện tại")
                            else:
                                logger.warning(f"   ⚠️ Không lấy được giá hiện tại cho {symbol}")
                                combined_oi['sumOpenInterestValue'] = combined_oi['sumOpenInterest']  # Fallback
                        except Exception as e:
                            logger.error(f"   ❌ Lỗi khi tính OI Value: {str(e)}")
                            combined_oi['sumOpenInterestValue'] = combined_oi['sumOpenInterest']  # Fallback
                    
                    # Log để kiểm tra giá trị OI
                    if 'sumOpenInterestValue' in combined_oi.columns:
                        logger.info(f"   📊 {symbol} OI value mới nhất: {combined_oi['sumOpenInterestValue'].iloc[-1]:,.2f} USDT")
                    
                    combined_oi = combined_oi.sort_values('timestamp').reset_index(drop=True)
                    result[symbol] = combined_oi
                    logger.info(f"   ✅ {len(combined_oi)} OI points collected")
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
    
    def _aggregate_oi_to_daily(self, oi_hourly_df):
        """Cải thiện phương thức tính OI theo ngày từ dữ liệu theo giờ - LUÔN DÙNG VALUE USDT"""
        if oi_hourly_df.empty:
            return pd.DataFrame()
        
        try:
            # Đảm bảo timestamp là datetime
            if not pd.api.types.is_datetime64_any_dtype(oi_hourly_df['timestamp']):
                oi_hourly_df['timestamp'] = pd.to_datetime(oi_hourly_df['timestamp'])
            
            # Tạo date column (ngày không có giờ)
            oi_hourly_df['date'] = oi_hourly_df['timestamp'].dt.date
            
            # ĐẢM BẢO có cột sumOpenInterestValue
            if 'sumOpenInterestValue' not in oi_hourly_df.columns and 'sumOpenInterest' in oi_hourly_df.columns:
                logger.warning(f"Không tìm thấy sumOpenInterestValue, tạm thời sử dụng sumOpenInterest")
                oi_hourly_df = oi_hourly_df.copy()
                oi_hourly_df['sumOpenInterestValue'] = oi_hourly_df['sumOpenInterest']  # Lưu ý: giá trị này không chính xác, cần giá để tính
            
            # Tính giá trị cho mỗi ngày bằng nhiều chỉ số khác nhau
            daily_oi = oi_hourly_df.groupby('date').agg({
                'timestamp': 'last',                  # Timestamp cuối cùng của ngày
                'sumOpenInterest': ['last', 'mean'],  # Lấy cả cuối ngày và trung bình
                'sumOpenInterestValue': ['last', 'mean']  # Lấy cả cuối ngày và trung bình theo USDT
            })
            
            # Flatten MultiIndex columns
            daily_oi.columns = ['_'.join(col).strip() for col in daily_oi.columns.values]
            daily_oi = daily_oi.reset_index()
            
            # Đổi tên các cột
            daily_oi = daily_oi.rename(columns={
                'sumOpenInterest_last': 'sumOpenInterest',
                'sumOpenInterest_mean': 'avgOpenInterest',
                'sumOpenInterestValue_last': 'sumOpenInterestValue',
                'sumOpenInterestValue_mean': 'avgOpenInterestValue'
            })
            
            # Thêm cột phụ trợ để tracking - dùng giá trị USDT
            daily_oi['daily_change'] = daily_oi['sumOpenInterestValue'].pct_change() * 100
            
            # Sort by date
            daily_oi = daily_oi.sort_values('date').reset_index(drop=True)
            
            # Log để debug
            if not daily_oi.empty:
                logger.info(f"   🔍 Kiểm tra giá trị OI đã tổng hợp (USDT): ngày gần nhất = {daily_oi['sumOpenInterestValue'].iloc[-1]:,.2f} USDT")
            
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
                        
                        # Kiểm tra giá trị quote_volume (USDT)
                        if 'quote_volume' in df.columns:
                            last_volume = df['quote_volume'].iloc[-1] if len(df) > 0 else 0
                            if symbol == 'BTCUSDT' and last_volume < 1000000000:  # < 1 tỷ USDT
                                quality_report['issues'].append(f"BTC quote_volume nghi ngờ sai ({last_volume:,.2f} USDT)")
                
                if has_data:
                    quality_report['symbols_with_data'] += 1
                else:
                    quality_report['symbols_without_data'] += 1
                    quality_report['issues'].append(f"No klines data for {symbol}")
        
        if 'open_interest' in data:
            for symbol, df in data['open_interest'].items():
                if not df.empty:
                    quality_report['total_oi_points'] += len(df)
                    
                    # Kiểm tra giá trị OI (USDT)
                    oi_col = next((col for col in ['sumOpenInterestValue', 'openInterestValue'] 
                                  if col in df.columns), None)
                    
                    if oi_col:
                        last_oi = df[oi_col].iloc[-1] if len(df) > 0 else 0
                        if symbol == 'BTCUSDT' and last_oi < 1000000000:  # < 1 tỷ USDT
                            quality_report['issues'].append(f"BTC OI Value nghi ngờ sai ({last_oi:,.2f} USDT)")
                else:
                    quality_report['issues'].append(f"No OI data for {symbol}")
        
        logger.info(f"📊 Data quality: {quality_report['symbols_with_data']} symbols OK, {len(quality_report['issues'])} issues")
        if quality_report['issues']:
            for issue in quality_report['issues']:
                logger.warning(f"⚠️ Quality issue: {issue}")
                
        return quality_report

    # Kiểm tra và sửa lỗi dữ liệu từ Binance API
    def validate_and_fix_api_data(self, data):
        """Kiểm tra và sửa lỗi dữ liệu từ Binance API"""
        if not data:
            return data
        
        try:
            # Kiểm tra klines data
            if 'klines' in data:
                for symbol, df in data['klines'].items():
                    if df.empty:
                        continue
                    
                    # Đảm bảo có quote_volume cho tất cả klines
                    if 'quote_volume' not in df.columns or df['quote_volume'].isnull().any():
                        data['klines'][symbol] = df.copy()
                        data['klines'][symbol]['quote_volume'] = df['volume'] * df['close']
                        logger.info(f"🔄 Đã tính toán quote_volume cho {symbol} klines")
                    
                    # Kiểm tra đặc biệt cho BTC (volume phải lớn)
                    if symbol == 'BTCUSDT' and 'quote_volume' in df.columns:
                        last_vol = df['quote_volume'].iloc[-1] if len(df) > 0 else 0
                        if 0 < last_vol < 1000000000:  # < 1 tỷ USDT
                            logger.warning(f"⚠️ BTC Volume quá nhỏ: {last_vol:,.2f} USDT, có thể sai")
                            
                            # Kiểm tra xem có phải sai ở đơn vị không
                            if 'volume' in df.columns and 'close' in df.columns:
                                expected = df['volume'].iloc[-1] * df['close'].iloc[-1]
                                if expected > 1000000000:  # > 1 tỷ USDT
                                    logger.info(f"🔄 Sửa BTC Volume: {last_vol:,.2f} → {expected:,.2f} USDT")
                                    data['klines'][symbol] = df.copy()
                                    data['klines'][symbol]['quote_volume'] = df['volume'] * df['close']
            
            # Kiểm tra open_interest data
            if 'open_interest' in data:
                for symbol, df in data['open_interest'].items():
                    if df.empty:
                        continue
                    
                    # Đảm bảo có sumOpenInterestValue cho tất cả OI
                    if 'sumOpenInterestValue' not in df.columns and 'sumOpenInterest' in df.columns:
                        # Cần tìm hoặc ước tính giá
                        price = None
                        
                        # Thử lấy giá từ klines data
                        if 'klines' in data and symbol in data['klines']:
                            klines_df = data['klines'][symbol]
                            if not klines_df.empty and 'close' in klines_df.columns:
                                price = klines_df['close'].iloc[-1]
                        
                        # Nếu không có từ klines, thử lấy từ ticker API
                        if price is None:
                            try:
                                ticker_data = self.api.get_ticker(symbol)
                                if ticker_data:
                                    price = float(ticker_data['lastPrice'])
                            except:
                                pass
                        
                        # Nếu có giá, tính sumOpenInterestValue
                        if price is not None and price > 0:
                            data['open_interest'][symbol] = df.copy()
                            data['open_interest'][symbol]['sumOpenInterestValue'] = df['sumOpenInterest'] * price
                            logger.info(f"🔄 Đã tính toán sumOpenInterestValue cho {symbol} OI")
                        else:
                            logger.warning(f"⚠️ Không thể tính sumOpenInterestValue cho {symbol}, không có giá")
                    
                    # Kiểm tra đặc biệt cho BTC (OI phải lớn)
                    if symbol == 'BTCUSDT' and 'sumOpenInterestValue' in df.columns:
                        last_oi = df['sumOpenInterestValue'].iloc[-1] if len(df) > 0 else 0
                        if 0 < last_oi < 1000000000:  # < 1 tỷ USDT
                            logger.warning(f"⚠️ BTC OI Value quá nhỏ: {last_oi:,.2f} USDT, có thể sai")
                            
                            # Kiểm tra xem có phải sai ở đơn vị không
                            if 'sumOpenInterest' in df.columns and 'price' in df.columns:
                                expected = df['sumOpenInterest'].iloc[-1] * df['price'].iloc[-1]
                                if expected > 1000000000:  # > 1 tỷ USDT
                                    logger.info(f"🔄 Sửa BTC OI Value: {last_oi:,.2f} → {expected:,.2f} USDT")
                                    data['open_interest'][symbol] = df.copy()
                                    data['open_interest'][symbol]['sumOpenInterestValue'] = df['sumOpenInterest'] * df['price']
            
            return data
        
        except Exception as e:
            logger.error(f"❌ Lỗi khi kiểm tra và sửa dữ liệu API: {str(e)}")
            return data

# Backward compatibility
HistoricalDataCollector = OptimizedHistoricalDataCollector