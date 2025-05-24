#!/usr/bin/env python3
"""
Script test import để kiểm tra tất cả modules
"""

def test_imports():
    """Test tất cả imports trong dự án"""
    print("🔧 Testing imports...")
    
    # Test config
    try:
        from config.settings import setup_logging, SYMBOLS
        print("✅ config.settings imported successfully")
    except Exception as e:
        print(f"❌ config.settings error: {e}")
    
    # Test data_analyzer
    try:
        from data_analyzer.metrics import OptimizedOIVolumeMetrics
        from data_analyzer.anomaly_detector import OptimizedAnomalyDetector, AnomalyDetector
        print("✅ data_analyzer imported successfully")
    except Exception as e:
        print(f"❌ data_analyzer error: {e}")
    
    # Test data_collector
    try:
        from data_collector.historical_data import HistoricalDataCollector
        from data_collector.binance_api import BinanceAPI
        print("✅ data_collector imported successfully")
    except Exception as e:
        print(f"❌ data_collector error: {e}")
    
    # Test data_storage
    try:
        from data_storage.database import Database
        print("✅ data_storage imported successfully")
    except Exception as e:
        print(f"❌ data_storage error: {e}")
    
    # Test alerting
    try:
        from alerting.telegram_bot import TelegramBot
        print("✅ alerting imported successfully")
    except Exception as e:
        print(f"❌ alerting error: {e}")
    
    # Test visualization
    try:
        from visualization.chart_generator import ChartGenerator
        from visualization.report_generator import OptimizedReportGenerator, ReportGenerator
        print("✅ visualization imported successfully")
    except Exception as e:
        print(f"❌ visualization error: {e}")
    
    # Test utils
    try:
        from utils.helpers import wait_for_next_minute
        print("✅ utils imported successfully")
    except Exception as e:
        print(f"❌ utils error: {e}")
    
    print("\n🎯 Testing main imports...")
    
    # Test main imports (những gì main.py cần)
    try:
        from config.settings import setup_logging, SYMBOLS, UPDATE_INTERVAL
        from data_collector.historical_data import HistoricalDataCollector
        from data_storage.database import Database
        from data_analyzer.anomaly_detector import OptimizedAnomalyDetector
        from alerting.telegram_bot import TelegramBot
        from visualization.chart_generator import ChartGenerator
        from visualization.report_generator import ReportGenerator
        from utils.helpers import wait_for_next_minute
        
        print("✅ All main.py imports successful!")
        return True
        
    except Exception as e:
        print(f"❌ main.py imports error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n🎉 All imports working correctly!")
        print("📋 Next steps:")
        print("   1. Copy các artifacts vào files tương ứng")
        print("   2. Tạo file .env với API keys")
        print("   3. Chạy: python main.py --collect")
    else:
        print("\n❌ Some imports failed. Check the errors above.")