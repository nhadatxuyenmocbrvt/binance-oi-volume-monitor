import os
import json
from datetime import datetime, timedelta
import shutil
import time
from config.settings import setup_logging

logger = setup_logging(__name__, 'helpers.log')

def ensure_directory_exists(directory):
    """Đảm bảo thư mục tồn tại, nếu không thì tạo mới"""
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Đảm bảo thư mục {directory} tồn tại")

def export_data_to_json(data, output_file):
    """Xuất dữ liệu sang định dạng JSON"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Đã xuất dữ liệu sang file {output_file}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi xuất dữ liệu sang JSON: {str(e)}")
        return False

def copy_files_for_github_pages(source_dir, target_dir):
    """Sao chép các file cần thiết cho GitHub Pages"""
    try:
        ensure_directory_exists(target_dir)
        
        # Sao chép tất cả các file trong source_dir sang target_dir
        for item in os.listdir(source_dir):
            s = os.path.join(source_dir, item)
            d = os.path.join(target_dir, item)
            
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        logger.info(f"Đã sao chép files từ {source_dir} sang {target_dir}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi sao chép files: {str(e)}")
        return False

def wait_for_next_minute():
    """Đợi đến phút tiếp theo để thực hiện cập nhật"""
    now = datetime.now()
    next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    wait_seconds = (next_minute - now).total_seconds()
    logger.info(f"Đợi {wait_seconds:.2f} giây đến phút tiếp theo")
    time.sleep(wait_seconds)

def format_number(number, decimal_places=2):
    """Định dạng số với dấu phẩy phân cách hàng nghìn"""
    if number is None:
        return "N/A"
    return f"{number:,.{decimal_places}f}"

def format_percent(number):
    """Định dạng số phần trăm"""
    if number is None:
        return "N/A"
    return f"{number:.2f}%"

def get_trend_emoji(value):
    """Trả về emoji xu hướng dựa trên giá trị"""
    if value is None:
        return ""
    if value > 2:
        return "🔥"  # Tăng mạnh
    elif value > 0.5:
        return "📈"  # Tăng
    elif value < -2:
        return "💧"  # Giảm mạnh
    elif value < -0.5:
        return "📉"  # Giảm
    else:
        return "➡️"  # Đi ngang