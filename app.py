import ccxt
from flask import Flask, render_template_string, request, jsonify
from dotenv import load_dotenv
import os
import time
import ast
import json
from datetime import datetime, timedelta
import schedule
import threading
import pytz
import sys
import math  # Thêm thư viện math để xử lý làm tròn amount
from pyngrok import ngrok

# === CẤU HÌNH ===
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    print(f"Error: .env file not found at {env_path}")
    sys.exit(1)

load_dotenv(env_path)
app = Flask(__name__)

# === BIẾN TOÀN CỤC ===
dca = 1
dca_results = []
last_run_sl_op = [-1] * 11
previous_total_balance = 0
dca_change_history = []
# === AUTO OPEN POSITIONS ===
last_auto_open_run = None
resume_auto_open_time = None
auto_open_history = [] # <--- Thêm dòng này

# === THỜI GIAN ===
time_open = {
    0: [5,25,45], 
    1: [15,35,55], 
    2: [19,39,59], 
    3: [12,32,52],
    4: [2,22,42],
    5: [14,34,54], 
    6: [7,27,47], 
    7: [9,29,49],
    8: [3,23,43], 
    9: [8,28,48], 
    10: [16,36,56],
}

time_set = {
    #0: [0,6,12,18,24,30,36,42,48,54],
    #0: [1,7,13,19,25,31,37,43,49,55],
    #0: [2,8,14,20,26,32,38,44,50,56],
    0: [3,9,15,21,27,33,39,45,51,57],
    #0: [4,10,16,22,28,34,40,46,52,58],
    #0: [5,11,17,23,29,35,41,47,53,59],
    #1: [0,6,12,18,24,30,36,42,48,54],
    #1: [1,7,13,19,25,31,37,43,49,55],
    #1: [2,8,14,20,26,32,38,44,50,56],
    #1: [3,9,15,21,27,33,39,45,51,57],
    1: [4,10,16,22,28,34,40,46,52,58],
    #1: [5,11,17,23,29,35,41,47,53,59],
    #2: [0,6,12,18,24,30,36,42,48,54],
    #2: [1,7,13,19,25,31,37,43,49,55],
    #2: [2,8,14,20,26,32,38,44,50,56],
    2: [3,9,15,21,27,33,39,45,51,57],
    #2: [4,10,16,22,28,34,40,46,52,58],
    #2: [5,11,17,23,29,35,41,47,53,59],
    #3: [0,6,12,18,24,30,36,42,48,54],
    3: [1,7,13,19,25,31,37,43,49,55],
    #3: [2,8,14,20,26,32,38,44,50,56],
    #3: [3,9,15,21,27,33,39,45,51,57],
    #3: [4,10,16,22,28,34,40,46,52,58],
    #3: [5,11,17,23,29,35,41,47,53,59],
    #4: [0,6,12,18,24,30,36,42,48,54],
    #4: [1,7,13,19,25,31,37,43,49,55],
    #4: [2,8,14,20,26,32,38,44,50,56],
    #4: [3,9,15,21,27,33,39,45,51,57],
    #4: [4,10,16,22,28,34,40,46,52,58],
    4: [5,11,17,23,29,35,41,47,53,59],
    #5: [0,6,12,18,24,30,36,42,48,54],
    #5: [1,7,13,19,25,31,37,43,49,55],
    #5: [2,8,14,20,26,32,38,44,50,56],
    #5: [3,9,15,21,27,33,39,45,51,57],
    #5: [4,10,16,22,28,34,40,46,52,58],
    5: [5,11,17,23,29,35,41,47,51,57],
    #6: [0,6,12,18,24,30,36,42,48,54],
    #6: [1,7,13,19,25,31,37,43,49,55],
    #6: [2,8,14,20,26,32,38,44,50,56],
    #6: [3,9,15,21,27,33,39,45,51,57],
    6: [4,10,16,22,28,34,40,46,52,58],
    #6: [5,11,17,23,29,35,41,47,53,59],
    #7: [0,6,12,18,24,30,36,42,48,54],
    #7: [1,7,13,19,25,31,37,43,49,55],
    #7: [2,8,14,20,26,32,38,44,50,56],
    #7: [3,9,15,21,27,33,39,45,51,57],
    #7: [4,10,16,22,28,34,40,46,52,58],
    7: [5,11,17,23,29,35,41,47,53,59],
    #8:[0,6,12,18,24,30,36,42,48,54],
    #8: [1,7,13,19,25,31,37,43,49,55],
    #8: [2,8,14,20,26,32,38,44,50,56],
    8: [3,9,15,21,27,33,39,45,51,57],
    #8: [4,10,16,22,28,34,40,46,52,58],
    #8: [5,11,17,23,29,35,41,47,53,59],
    9: [0,6,12,18,24,30,36,42,48,54],
    #9: [1,7,13,19,25,31,37,43,49,55],
    #9: [2,8,14,20,26,32,38,44,50,56],
    #9: [3,9,15,21,27,33,39,45,51,57],
    #9: [4,10,16,22,28,34,40,46,52,58],
    #9: [5,11,17,23,29,35,41,47,53,59],
    10: [0,6,12,18,24,30,36,42,48,54],
    #10: [1,7,13,19,25,31,37,43,49,55],
    #10: [2,8,14,20,26,32,38,44,50,56],
    #10: [3,9,15,21,27,33,39,45,51,57],
    #10: [4,10,16,22,28,34,40,46,52,58],
    #10: [5,11,17,23,29,35,41,47,53,59],
}


# === BIẾN TOÀN CỤC MỚI (PHỤC VỤ DAILY 18H) ===
dca_target_offset = 2  # Mặc định là 2 (tương ứng target [2,5,8...])
previous_balances_18h = {}
last_daily_check_date = None


# Cache dữ liệu positions & balance
position_cache = {}  # {account_index: {'balance': float, 'single': list, 'dual': list, 'exchange': obj, 'timestamp': datetime}}
CACHE_VALID_SECONDS = 35

# === DCA STATE ===
current_account_index = 3# Bắt đầu từ OKX_4
last_processed_minute = None
last_token = 'BIO'
processed_tokens = {'SNX', 'TURBO', 'AVNT', 'TRB', 'OKB', 'JTO', 'USELESS', 'BIO', 'ZBT', 'AUCTION', 'LINEA'}
is_first_run = False

# === TÀI KHOẢN ===
accounts = [
    {'apiKey': os.getenv('OKX_API_KEY_0'), 'secret': os.getenv('OKX_API_SECRET_0'), 'password': os.getenv('OKX_PASSWORD_0'), 'name': 'OKX_0', 'balance_want': 85, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_1'), 'secret': os.getenv('OKX_API_SECRET_1'), 'password': os.getenv('OKX_PASSWORD_1'), 'name': 'OKX_1', 'balance_want': 53, 'pos_size_usdt': 5.05},
    {'apiKey': os.getenv('OKX_API_KEY_2'), 'secret': os.getenv('OKX_API_SECRET_2'), 'password': os.getenv('OKX_PASSWORD_2'), 'name': 'OKX_2', 'balance_want': 245.5, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_3'), 'secret': os.getenv('OKX_API_SECRET_3'), 'password': os.getenv('OKX_PASSWORD_3'), 'name': 'OKX_3', 'balance_want': 342.5, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_4'), 'secret': os.getenv('OKX_API_SECRET_4'), 'password': os.getenv('OKX_PASSWORD_4'), 'name': 'OKX_4', 'balance_want': 79, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_5'), 'secret': os.getenv('OKX_API_SECRET_5'), 'password': os.getenv('OKX_PASSWORD_5'), 'name': 'OKX_5', 'balance_want': 82.5, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_6'), 'secret': os.getenv('OKX_API_SECRET_6'), 'password': os.getenv('OKX_PASSWORD_6'), 'name': 'OKX_6', 'balance_want': 82, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_7'), 'secret': os.getenv('OKX_API_SECRET_7'), 'password': os.getenv('OKX_PASSWORD_7'), 'name': 'OKX_7', 'balance_want': 276.5, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_8'), 'secret': os.getenv('OKX_API_SECRET_8'), 'password': os.getenv('OKX_PASSWORD_8'), 'name': 'OKX_8', 'balance_want': 235.5, 'pos_size_usdt': 4.0},
    {'apiKey': os.getenv('OKX_API_KEY_9'), 'secret': os.getenv('OKX_API_SECRET_9'), 'password': os.getenv('OKX_PASSWORD_9'), 'name': 'OKX_9', 'balance_want': 64, 'pos_size_usdt': 4.55},
    {'apiKey': os.getenv('OKX_API_KEY_10'), 'secret': os.getenv('OKX_API_SECRET_10'), 'password': os.getenv('OKX_PASSWORD_10'), 'name': 'OKX_10', 'balance_want': 165, 'pos_size_usdt': 4.0},
]

for i, acc in enumerate(accounts):
    if not all([acc['apiKey'], acc['secret'], acc['password']]):
        print(f"Error: Missing API credentials for {acc['name']}")
        sys.exit(1)

# === TÍNH TỔNG BALANCE_WANT (thêm vào phần đầu, sau khi load accounts) ===
total_balance_want = sum(acc['balance_want'] for acc in accounts)
#log(f"Total target balance_want across all accounts: {total_balance_want:.2f} USDT")

# === TOKEN AMOUNTS ===
token_amounts_0 = {
    ('F',): 6.0,
}
token_amounts_1 = {
    ('BZ',): 3.0,
}
token_amounts_2 = {
    ('MMT',): 2.0,
}
token_amounts_3 = {
    ('TURBO'):0.1, 
    }
token_amounts_4 = {
    ('S',): 9.0,
}
token_amounts_5 = {
    ('AR',): 22.0,
    }
token_amounts_6 = {
    ('ME',): 30.0,
}
token_amounts_7 = {
    ('FOGO',): 10.0,
    }
token_amounts_8 = {
    ('OP'): 9.0,       
}
token_amounts_9 = {
    ('H',): 0.4,
}
token_amounts_10 = {
    ('S',): 9.0,
}

token_amounts_map = {i: globals()[f'token_amounts_{i}'] for i in range(11)}

# === LƯU TRỮ VÀ ĐỌC FILE CONFIG KHI KHỞI ĐỘNG ===
CONFIG_FILE = 'token_config.txt'

# === HÀM SẮP XẾP & LƯU FILE ===
def get_sorted_unique_token_amounts(idx):
    amounts_dict = token_amounts_map.get(idx, {})
    items = []
    
    for key, amount in amounts_dict.items():
        if isinstance(key, str):
            tokens = [key]
        else:
            tokens = list(key)
            
        for token in tokens:
            items.append((token, amount))
                
    sorted_items = sorted(items, key=lambda x: (len(x[0]), x[0].upper()))
    return sorted_items

def save_normalized_config():
    """Chuẩn hóa dictionary thành cấu trúc đã sắp xếp và lưu đè ra file txt (Bao gồm cả balance_want)"""
    for i in range(11):
        sorted_items = get_sorted_unique_token_amounts(i)
        # Re-build lại dict để ép Python duy trì cấu trúc sorted
        token_amounts_map[i] = { (token,): amount for token, amount in sorted_items }

    # Lấy thời gian hiện tại theo múi giờ Việt Nam
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    current_time = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    
    # Trích xuất balance_want hiện tại của tất cả tài khoản
    balance_wants_to_save = {i: accounts[i]['balance_want'] for i in range(11)}

    # Format thời gian ngủ đông thành chuỗi chữ để lưu
    resume_time_str = resume_auto_open_time.strftime('%Y-%m-%d %H:%M:%S') if resume_auto_open_time else 'None'

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Cap nhat lan cuoi: {current_time}\n")
        f.write(f"# current_account_index: {current_account_index}\n")
        f.write(f"# processed_tokens: {list(processed_tokens)}\n")
        f.write(f"# last_token: {last_token}\n")
        f.write(f"# dca: {dca}\n")
        f.write(f"# balance_wants: {balance_wants_to_save}\n")
        f.write(f"# last_auto_open_run: {last_auto_open_run}\n")
        f.write(f"# resume_auto_open_time: {resume_time_str}\n")
        f.write(f"# dca_target_offset: {dca_target_offset}\n")
        f.write(f"# time_open: {time_open}\n")
        f.write(f"# time_set: {time_set}\n")
        f.write(f"# previous_balances_18h: {previous_balances_18h}\n")
        f.write(f"# last_daily_check_date: {last_daily_check_date}\n")
        f.write(repr(token_amounts_map))
        

def log_auto_open(msg):
    """Hàm log chuyên dụng: Vừa in ra màn hình, vừa lưu lên Web (tối đa 50 dòng mới nhất)"""
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    t = datetime.now(tz).strftime('%H:%M:%S') # Chỉ lấy giờ phút giây cho gọn
    full_msg = f"[{t}] {msg}"
    print(f"[{datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}] {msg}") # Vẫn in ra terminal đầy đủ
    
    auto_open_history.insert(0, full_msg) # Nhét lên đầu danh sách
    if len(auto_open_history) > 150:
        auto_open_history.pop() # Giữ tối đa 50 dòng log gần nhất cho nhẹ web


# === ĐỌC FILE LÚC KHỞI ĐỘNG ===
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            dict_str = ""
            for line in f:
                line = line.strip()
                
                # 1. Khôi phục DCA
                if line.startswith("# dca:"):
                    try:
                        dca = int(line.split(":", 1)[1].strip())
                        print(f"Đã tải dca = {dca} từ file.")
                    except: pass
                
                # 2. Khôi phục Tài khoản đang chạy dở
                elif line.startswith("# current_account_index:"):
                    try:
                        current_account_index = int(line.split(":", 1)[1].strip())
                        print(f"Đã tải current_account_index = {current_account_index} từ file.")
                    except: pass
                
                # 3. Khôi phục Token mốc cuối cùng
                elif line.startswith("# last_token:"):
                    try:
                        val = line.split(":", 1)[1].strip()
                        last_token = None if val == 'None' else val
                        print(f"Đã tải last_token = {last_token} từ file.")
                    except: pass
                
                # 4. Khôi phục Danh sách token đã quét qua
                elif line.startswith("# processed_tokens:"):
                    try:
                        val = line.split(":", 1)[1].strip()
                        if val in ["set()", "[]"]:
                            processed_tokens = set()
                        else:
                            processed_tokens = set(ast.literal_eval(val))
                        print(f"Đã tải processed_tokens từ file.")
                    except: pass
                
                # 5. Khôi phục Target chốt lời
                elif line.startswith("# balance_wants:"):
                    try:
                        bw_dict = ast.literal_eval(line.split(":", 1)[1].strip())
                        for idx, bw in bw_dict.items():
                            accounts[int(idx)]['balance_want'] = float(bw)
                        print("Đã tải balance_want từ file.")
                    except Exception as e:
                        print("Lỗi load balance_wants:", e)
                
                # --- ĐOẠN THÊM MỚI ---
                # 6. Khôi phục phút chạy cuối cùng
                elif line.startswith("# last_auto_open_run:"):
                    try:
                        val = line.split(":", 1)[1].strip()
                        last_auto_open_run = int(val) if val != 'None' else None
                    except: pass
                
                # 7. Khôi phục thời gian ngủ đông (Delay)
                elif line.startswith("# resume_auto_open_time:"):
                    try:
                        val = line.split(":", 1)[1].strip()
                        if val != 'None':
                            tz_vn = pytz.timezone('Asia/Ho_Chi_Minh')
                            # Đọc chuỗi chữ thành object datetime và ép múi giờ VN
                            dt_unaware = datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                            resume_auto_open_time = tz_vn.localize(dt_unaware)
                            print(f"Đã tải thời gian ngủ đông: tới {val} mới mở lệnh lại.")
                        else:
                            resume_auto_open_time = None
                    except Exception as e:
                        print("Lỗi load resume_auto_open_time:", e)
                # --- KẾT THÚC ĐOẠN THÊM MỚI ---

                
            
                # --- ĐỌC DATA 18H TỪ FILE ---
                elif line.startswith("# dca_target_offset:"):
                    try: dca_target_offset = int(line.split(":", 1)[1].strip())
                    except: pass
                elif line.startswith("# time_open:"):
                    try: time_open = ast.literal_eval(line.split(":", 1)[1].strip())
                    except: pass
                elif line.startswith("# time_set:"):
                    try: time_set = ast.literal_eval(line.split(":", 1)[1].strip())
                    except: pass
                elif line.startswith("# previous_balances_18h:"):
                    try: previous_balances_18h = ast.literal_eval(line.split(":", 1)[1].strip())
                    except: pass
                elif line.startswith("# last_daily_check_date:"):
                    try: 
                        val = line.split(":", 1)[1].strip()
                        if val != 'None':
                            last_daily_check_date = datetime.strptime(val, '%Y-%m-%d').date()
                    except: pass


                # 8. Khôi phục Danh sách token & Amount
                elif not line.startswith("#") and line:
                    dict_str += line

            # Gán dữ liệu cho token_amounts_map
            if dict_str.strip():
                token_amounts_map = ast.literal_eval(dict_str.strip())
                print("Đã tải thành công token amounts từ file cấu hình (token_config.txt).")
                
    except Exception as e:
        print(f"Lỗi đọc file cấu hình: {e}. Đang sử dụng dữ liệu mặc định.")

# Luôn chạy hàm này khi bật Bot để dọn dẹp và sort lại file
save_normalized_config()


# === HTML ===
HTML_TEMPLATE = """
<!DOCTYPE html>
<html><head><title>OKX DCA Bot</title><meta http-equiv="refresh" content="60">
<style>
  body{font-family:Arial;margin:20px;background:#f9f9f9}
  table{border-collapse:collapse;width:100%}
  th,td{border:1px solid #ddd;padding:8px;text-align:left}
  th{background:#4CAF50;color:white}
  .single {color: blue;}
  .dual {color: green;}
  
  .update-form { background: #eef; padding: 15px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #ccc; }
  .update-form textarea { width: 100%; font-family: monospace; margin-top: 10px; }
  .update-form button { padding: 8px 15px; border: none; cursor: pointer; margin-top: 10px; font-weight:bold; border-radius:3px;}
  
  .btn-preview { background: #008CBA; color: white; }
  .btn-preview:hover { background: #007bb5; }
  
  .btn-confirm { background: #4CAF50; color: white; margin-right: 10px;}
  .btn-confirm:hover { background: #45a049; }
  
  .btn-cancel { background: #f44336; color: white; }
  .btn-cancel:hover { background: #da190b; }

  #confirmBox {
      display: none;
      background: #fff;
      border: 2px dashed #ff9800;
      padding: 15px;
      margin-top: 15px;
      border-radius: 5px;
  }
  .diff-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 15px; font-size: 15px;}
  .diff-table th, .diff-table td { border: 1px solid #ccc; padding: 8px; text-align: center; }
  .diff-table th { background: #ffe0b2; color: #333;}
  .old-val { color: #888; text-decoration: line-through; }
  .new-val { color: #2e7d32; font-weight: bold; }
  .del-val { color: red; font-weight: bold; }
  .new-token { color: blue; font-style: italic; }

  #tokenSearch {
      width: 100%;
      max-width: 300px;
      padding: 10px;
      margin-bottom: 15px;
      border: 1px solid #ccc;
      border-radius: 4px;
      font-size: 16px;
  }
  
  /* Cập nhật style cho khung Textarea custom */
  #customInput {
      resize: both;
      word-wrap: break-word;
      overflow-wrap: break-word;
      font-family: monospace;
  }
</style>
</head><body>
<h2>OKX DCA Bot</h2>

<div style="background: #e1f5fe; padding: 15px; border-radius: 5px; border: 1px solid #b3e5fc; margin-bottom: 20px;">
    <h2 style="margin-top: 0; color: #0277bd;">Sum: {{ total_balance_cached|round(2) }} USDT</h2>
    <h2 style="color: #0277bd;">Sum margin: {{ total_margin_cached|round(2) }} USDT</h2>
    <h2 style="color: #0277bd;">Total want: {{ total_balance_want|round(2) }} USDT</h2>
    
    <button onclick="toggleLogs()" style="margin-bottom: 10px; padding: 5px 10px;">Hiện/Ẩn Chi tiết Logs Tài Khoản</button>
    <pre id="passiveLogs" style="display:none; background:#fff; padding:10px; border-radius:5px; font-size: 14px; border: 1px solid #ccc; white-space: pre-wrap;">{{ passive_logs | safe }}</pre>


    <button onclick="toggleAutoLogs()" style="margin-bottom: 10px; padding: 5px 10px; background: #fff9c4; border: 1px solid #fbc02d; cursor: pointer; border-radius:3px;">Hiện/Ẩn Lịch sử Auto Open</button>
    <div id="autoLogsContainer" style="display:none; background:#fff; padding:10px; border-radius:5px; font-size: 14px; border: 1px solid #ccc; max-height: 250px; overflow-y: auto;">
        {% for log_line in auto_open_history %}
            <div style="border-bottom: 1px dashed #eee; padding: 4px 0;">{{ log_line }}</div>
        {% endfor %}
        {% if not auto_open_history %}
            <div style="color: #888; font-style: italic;">Chưa có hoạt động Auto Open nào...</div>
        {% endif %}
    </div>


    <h3 style="margin-top: 15px;">Ghi chú (Tự động lưu)</h3>
    <textarea id="customInput" style="width: 100%; height: 200px; padding: 10px; font-size: 16px;" placeholder="Nhập ghi chú vào đây..." oninput="saveTextArea()"></textarea>
</div>

<div class="update-form">
  <h3>Cập nhật số lượng Token</h3>
  <label for="accIndex">Tài khoản:</label>
  <select id="accIndex">
    {% for i in range(11) %}
      <option value="{{ i }}">{{ accounts[i].name }}</option>
    {% endfor %}
  </select>
  <br>
  <label for="tokenData">Định dạng (nhập 0 để xóa token): <i>('LINK',): 0.4,</i></label>
  <textarea id="tokenData" rows="3" placeholder="('LINK',): 0.4,"></textarea>
  <br>
  <button type="button" class="btn-preview" onclick="previewTokens()">Kiểm tra Thay đổi</button>
  <span id="updateMsg" style="margin-left: 10px; font-weight: bold;"></span>

  <div id="confirmBox">
      <h4 style="margin-top:0; color:#ff9800;">Xác nhận thông tin sắp cập nhật:</h4>
      <div id="diffContent"></div>
      <button type="button" class="btn-confirm" onclick="executeSubmit()">Xác nhận Cập nhật</button>
      <button type="button" class="btn-cancel" onclick="cancelSubmit()">Hủy bỏ</button>
  </div>
</div>

<script>
let currentPayload = null;

function saveTextArea() {
    const textAreaContent = document.getElementById('customInput').value;
    localStorage.setItem('customText', textAreaContent);
}

function loadTextArea() {
    const savedContent = localStorage.getItem('customText');
    if (savedContent) {
        document.getElementById('customInput').value = savedContent;
    }
}
document.addEventListener('DOMContentLoaded', loadTextArea);

function toggleLogs() {
    var x = document.getElementById("passiveLogs");
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}

function toggleAutoLogs() {
    var x = document.getElementById("autoLogsContainer");
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}

function previewTokens() {
    const accIndex = document.getElementById("accIndex").value;
    const tokenData = document.getElementById("tokenData").value;
    const msg = document.getElementById("updateMsg");
    const confirmBox = document.getElementById("confirmBox");
    
    if(!tokenData.trim()) {
        msg.style.color = "red";
        msg.innerText = "Vui lòng nhập dữ liệu token!";
        return;
    }

    msg.style.color = "blue";
    msg.innerText = "Đang kiểm tra...";
    confirmBox.style.display = "none";

    currentPayload = { "accIndex": accIndex, "tokenData": tokenData };

    fetch("/preview_tokens", {
        method: "POST",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(currentPayload)
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            msg.innerText = "";
            let html = "<table class='diff-table'><tr><th>Token</th><th>Số lượng mới</th><th>Số lượng cũ</th></tr>";
            data.changes.forEach(c => {
                let oldStr = c.old === null ? "<span class='new-token'>Không có (Thêm mới)</span>" : `<span class='old-val'>${c.old_display}</span>`;
                let newValStr = c.new === 0 ? "<span class='del-val'>0 (Xóa)</span>" : `<span class='new-val'>${c.new_display}</span>`;
                let rowStyle = c.old !== c.new ? "background-color: #f1f8e9;" : "";
                
                html += `<tr style="${rowStyle}">
                    <td><strong>${c.token}</strong></td>
                    <td>${newValStr}</td>
                    <td>${oldStr}</td>
                </tr>`;
            });
            html += "</table>";
            
            document.getElementById("diffContent").innerHTML = html;
            confirmBox.style.display = "block";
        } else {
            msg.style.color = "red";
            msg.innerText = "Lỗi: " + data.error;
        }
    })
    .catch(err => {
        msg.style.color = "red";
        msg.innerText = "Lỗi kết nối máy chủ!";
        console.error(err);
    });
}

function executeSubmit() {
    if (!currentPayload) return;
    const msg = document.getElementById("updateMsg");
    const confirmBox = document.getElementById("confirmBox");

    msg.style.color = "blue";
    msg.innerText = "Đang tiến hành cập nhật...";
    confirmBox.style.display = "none";

    fetch("/update_tokens", {
        method: "POST",
        headers: { "Accept": "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(currentPayload)
    })
    .then(response => response.json())
    .then(data => {
        if(data.success) {
            msg.style.color = "green";
            msg.innerText = "Cập nhật thành công! Đang tải lại...";
            setTimeout(() => location.reload(), 1000);
        } else {
            msg.style.color = "red";
            msg.innerText = "Lỗi khi lưu: " + data.error;
        }
    })
    .catch(err => {
        msg.style.color = "red";
        msg.innerText = "Lỗi kết nối máy chủ khi cập nhật!";
        console.error(err);
    });
}

function cancelSubmit() {
    document.getElementById("confirmBox").style.display = "none";
    document.getElementById("updateMsg").innerText = "";
    currentPayload = null;
}

function filterTokens() {
    let input = document.getElementById("tokenSearch").value.toUpperCase();
    let tables = document.getElementsByClassName("amount-table");

    for (let i = 0; i < tables.length; i++) {
        let tr = tables[i].getElementsByTagName("tr");
        for (let j = 1; j < tr.length; j++) {
            let td = tr[j].getElementsByClassName("token")[0];
            if (td) {
                let txtValue = td.textContent || td.innerText;
                if (txtValue === "(empty)") continue;
                if (txtValue.toUpperCase().indexOf(input) > -1) {
                    tr[j].style.display = "";
                } else {
                    tr[j].style.display = "none";
                }
            }
        }
    }
}
</script>

<p><strong>Current Account:</strong> {{current_account_name}}</p>
<p><strong>DCA:</strong> <span style="color:{{'green' if dca==1 else 'red'}};font-weight:bold">{{'ON' if dca==1 else 'OFF'}}</span></p>

<h3>DCA Actions (last 20)</h3>
<table>
<tr><th>Acc</th><th>Time</th><th>Token</th><th>Action</th><th>Price%</th><th>PNL</th><th>Order</th></tr>
{% for r in dca_results %}
<tr><td>{{r.account}}</td><td>{{r.timestamp}}</td><td><strong>{{r.token}}</strong></td><td>{{r.action}}</td><td>{{r.price_change}}</td><td>{{r.pnl}}</td><td>{{r.order_status}}</td></tr>
{% endfor %}
</table>

<h3>DCA Flip History</h3>
<table>
<tr><th>Time</th><th>Reason</th></tr>
{% for h in dca_change_history %}
<tr><td>{{h.time}}</td><td>{{h.reason}}</td></tr>
{% endfor %}
</table>

<h2>Target Amounts per Account</h2>
<input type="text" id="tokenSearch" onkeyup="filterTokens()" placeholder="Nhập tên Token để lọc (vd: LINK)...">

{% for i in range(11) %}
    <h3 class="account-title">{{ accounts[i].name }} — target: {{ accounts[i].balance_want }} USDT</h3>
    <table class="amount-table">
        <tr><th class="token">Token</th><th class="amount">Amount</th></tr>
        {% for token, amt in sorted_token_amounts[i] %}
        <tr>
            <td class="token">{{ token }}</td>
            <td class="amount">{{ amt }}</td>
        </tr>
        {% endfor %}
        {% if not sorted_token_amounts[i] %}
        <tr><td colspan="2" style="text-align:center;color:#888;">(empty)</td></tr>
        {% endif %}
    </table>
{% endfor %}

</body></html>
"""

# === UTILS ===
def log(msg):
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    t = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{t}] {msg}")

def add_dca_result(account, action, token='—', price_change='—', pnl='—', order_status='—'):
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    result = {
        'account': account,
        'timestamp': datetime.now(tz).strftime('%H:%M:%S'),
        'token': token,
        'action': action,
        'price_change': price_change,
        'pnl': pnl,
        'order_status': order_status
    }
    dca_results.append(result)
    if len(dca_results) > 20:
        dca_results.pop(0)

def extract_token(symbol):
    return symbol.split('/')[0]

def get_token_amount(token, idx):
    amounts = token_amounts_map.get(idx, {})
    for key, val in amounts.items():
        if isinstance(key, tuple) and token in key:
            return val
        if token == key:
            return val
        
    print(f"get_token_amount {token} thất bại")
    return 0

# === CACHE MANAGEMENT ===
def is_cache_valid(cached):
    if not cached or 'timestamp' not in cached:
        return False
    age = (datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')) - cached['timestamp']).total_seconds()
    return age < CACHE_VALID_SECONDS

def fetch_fresh_data(account, account_index):
    """Fetch balance + positions một lần, lưu vào cache"""
    try:
        exchange = ccxt.okx({
            'apiKey': account['apiKey'],
            'secret': account['secret'],
            'password': account['password'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap', 
                'adjustForTimeDifference': True  # <--- BỔ SUNG DÒNG NÀY ĐỂ FIX LỖI 50102
            }
        })

        balance_resp = exchange.fetch_balance(params={'type': 'swap'})
        usdt_info = balance_resp.get('USDT', {})
        usdt_balance = float(usdt_info.get('total', 0))
        usdt_used = float(usdt_info.get('used', 0)) if usdt_info.get('used') else 0.0
        usdt_available = usdt_balance - usdt_used

        positions = exchange.fetch_positions(None, params={'type': 'swap'})

        token_positions = {}
        for pos in positions:
            if float(pos.get('contracts', 0)) > 0:
                token = extract_token(pos['symbol'])
                # Bổ sung lưu contractSize trực tiếp từ API Response vào bộ nhớ
                contract_size = float(pos.get('contractSize') or pos.get('info', {}).get('ctVal', 1))

                token_positions.setdefault(token, []).append({
                    'side': pos['side'],
                    'entryPrice': float(pos['entryPrice']),
                    'markPrice': float(pos.get('markPrice', pos['entryPrice'])),
                    'pnl': float(pos.get('unrealizedPnl', 0)),
                    'contracts': float(pos['contracts']),
                    'contractSize': contract_size, # <-- Thêm dòng này để lưu vào cache
                    'symbol': pos['symbol']
                })

        single = [(t, poss) for t, poss in token_positions.items() if len({p['side'] for p in poss}) == 1]
        dual   = [(t, poss) for t, poss in token_positions.items() if len({p['side'] for p in poss}) == 2]

        data = {
            'balance': usdt_balance,
            'available_balance': usdt_available,  # <--- BỔ SUNG DÒNG NÀY
            'single': single,
            'dual': dual,
            'exchange': exchange,
            'timestamp': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        }
        position_cache[account_index] = data
        return data
    except Exception as e:
        log(f"Fetch fresh data failed {account['name']}: {e}")
        return None

def get_cached_or_fresh(account, idx, force=False):
    cached = position_cache.get(idx)
    if not force and is_cache_valid(cached):
        return cached['balance'], cached['single'], cached['dual'], cached['exchange']
    
    fresh = fetch_fresh_data(account, idx)
    if fresh:
        return fresh['balance'], fresh['single'], fresh['dual'], fresh['exchange']
    
    return 0.0, [], [], None

# === HÀM SINH LOG THÔNG KÊ THỤ ĐỘNG ===
# === HÀM SINH LOG THÔNG KÊ THỤ ĐỘNG ===
def generate_passive_stats():
    """Hàm này chỉ đọc dữ liệu từ position_cache, không gọi thêm API nào"""
    total_balance = 0
    total_margin = 0
    logs = []

    for i, acc in enumerate(accounts):
        cached = position_cache.get(i)
        if not cached:
            logs.append(f"--- {acc['name']} ---")
            logs.append("No data in cache yet (chờ bot cycle quét qua).")
            logs.append("")
            continue

        balance = cached['balance']
        total_balance += balance
        single = cached['single']
        dual = cached['dual']

        qty = 0
        acc_long = 0   # Tính tổng USDT vị thế Long của tài khoản này
        acc_short = 0  # Tính tổng USDT vị thế Short của tài khoản này
        
        hedge_positions = [t for t, _ in dual]
        non_hedge_less_1 = []
        non_hedge_greater_1 = []
        non_hedge_99 = []
        hedge_positions_with_stop_loss = []
        
        max_change_percent = 0
        max_change_token = None

        def process_pct(pct, token, side):
            nonlocal max_change_percent, max_change_token
            if side == 'long':
                if pct > 2: non_hedge_greater_1.append(token)
                else: non_hedge_less_1.append(token)
            else: # short
                if pct < -2: non_hedge_greater_1.append(token)
                else: non_hedge_less_1.append(token)

            if abs(pct) > abs(max_change_percent):
                max_change_percent = pct
                max_change_token = token

        # Phân tích Single (Non-Hedge)
        for token, poss in single:
            for pos in poss:
                mark = pos['markPrice']
                entry = pos['entryPrice']
                # Tính Qty chuẩn: Contracts * ContractSize * MarkPrice
                pos_value = pos['contracts'] * pos.get('contractSize', 1) * mark
                qty += pos_value
                
                # Cộng dồn vào Long hoặc Short của tài khoản
                if pos['side'] == 'long':
                    acc_long += pos_value
                elif pos['side'] == 'short':
                    acc_short += pos_value

                if entry != 0:
                    pct = ((mark - entry) / entry) * 100
                    process_pct(pct, token, pos['side'])
                    
                    if pos['side'] == 'long' and mark < entry * 0.9:
                        non_hedge_99.append(token)
                    elif pos['side'] == 'short' and mark > entry * 1.1:
                        non_hedge_99.append(token)

        # Phân tích Dual (Hedge)
        for token, poss in dual:
            for pos in poss:
                mark = pos['markPrice']
                entry = pos['entryPrice']
                pos_value = pos['contracts'] * pos.get('contractSize', 1) * mark
                qty += pos_value
                
                # Cộng dồn vào Long hoặc Short của tài khoản
                if pos['side'] == 'long':
                    acc_long += pos_value
                elif pos['side'] == 'short':
                    acc_short += pos_value

                if entry != 0:
                    pct = ((mark - entry) / entry) * 100
                    if abs(pct) > abs(max_change_percent):
                        max_change_percent = pct
                        max_change_token = token
                        
                    if (pos['side'] == 'long' and pct > 1) or (pos['side'] == 'short' and pct < -1):
                        if token not in hedge_positions_with_stop_loss:
                            hedge_positions_with_stop_loss.append(token)

        total_margin += qty
        has_pos = len(single) > 0 or len(dual) > 0
        balance_style = 'background-color: grey' if not has_pos else ''

        available = cached.get('available_balance', 0)
        logs.append(f"--- {acc['name']} ---")
        
        # === HIỂN THỊ LONG / SHORT NGAY CẠNH QTY ===
        logs.append(f"qty: {round(qty, 2)}, {round(available, 2)} | L: <span style='color:green'>{round(acc_long, 2)}</span> | S: <span style='color:red'>{round(acc_short, 2)}</span>")
        
        # Format đầu ra giống chuẩn của Script 2
        line2 = f"{len(non_hedge_less_1)},{len(hedge_positions)},{len(hedge_positions) + len(non_hedge_greater_1) + len(non_hedge_less_1)},<span style='{balance_style}'>{round(balance, 2)}</span>, {acc['balance_want']}, {hedge_positions}"
        logs.append(line2)
        logs.append(f"             {non_hedge_less_1},{non_hedge_greater_1},\n             {hedge_positions_with_stop_loss}")
        logs.append(f"             {non_hedge_99}")
        max_change_output = f"{max_change_token}: {round(max_change_percent, 2)}%" if max_change_token else "None: 0%"
        logs.append(f"             Max Change Token: {max_change_output}")
        logs.append("")

    return total_balance, total_margin, "\n".join(logs)


# === STOP LOSS ===
def set_stop_loss(exchange, symbol, position_side, amount, stop_price, acc_name, diff_pct):
    side = 'buy' if position_side == 'short' else 'sell'
    token = extract_token(symbol)
    try:
        exchange.create_order(
            symbol=symbol,
            type='stop_market',
            side=side,
            amount=amount,
            params={'stopLossPrice': stop_price, 'posSide': position_side}
        )
        log(f"{acc_name} | Set SL {token} {position_side.upper()} → {diff_pct:.1f}%")
        return True
    except Exception as e:
        log(f"{acc_name} | SL Error {token}: {str(e)}")
        return False

def check_and_set_stop_loss(exchange, symbol, pos, acc_name):
    side = pos['side']
    ep = pos['entryPrice']
    mp = pos['markPrice']
    diff_pct = ((mp - ep) / ep * 100) if side == 'long' else ((ep - mp) / ep * 100)
    if diff_pct < 2:
        return False

    token = extract_token(symbol)
    stop_price = ep * (1 + diff_pct/200 if side == 'long' else 1 - diff_pct/200) if diff_pct <= 6 else mp * (0.98 if side == 'long' else 1.02)

    try:
        #open_orders = exchange.fetch_open_orders(symbol)
        #existing_sl = next((float(o['info']['stopLossPrice']) for o in open_orders 
                           #if o['type'] == 'stop_market' and o['info'].get('posSide') == side), None)
        
        #if existing_sl and ((side == 'long' and stop_price <= existing_sl) or (side == 'short' and stop_price >= existing_sl)):
            #return True
        
        return set_stop_loss(exchange, symbol, side, pos['contracts'], stop_price, acc_name, diff_pct)
    except Exception as e:
        log(f"{acc_name} | Check SL Error {token}: {e}")
        return False



# === OPEN OPPOSITE (chỉ khi single position) ===
def open_opposite(exchange, symbol, side, mp, ep, pos, acc_name, idx, all_positions):
    token = extract_token(symbol)
    positions_for_token = [p for p in all_positions if extract_token(p['symbol']) == token and p['contracts'] > 0]
    
    if len(positions_for_token) != 1:
        return False

    has_opposite = any(extract_token(p['symbol']) == token and p['side'] != side for p in all_positions)
    if has_opposite:
        return False

    if (side == 'long' and mp >= ep * 0.9) or (side == 'short' and mp <= ep * 1.1):
        return False

    base_amount = get_token_amount(token, idx)
    if base_amount <= 0:
        return False

    current_contracts = pos['contracts']
    # Quyết định size mở opposite
    # if current_contracts < 4 * base_amount:
    #     open_amount = base_amount 
    #     reason = f"contracts {current_contracts:.2f} < 4×{base_amount} → open 4x"
    # else:
    #     open_amount = base_amount
    #     reason = f"contracts {current_contracts:.2f} ≥ 4×{base_amount} → open 1x"

    opposite_side = 'short' if side == 'long' else 'long'
    order_side = 'sell' if side == 'long' else 'buy'
    if order_side=='buy':
        open_amount = base_amount *2
        reason = f"side buy → open 2x"
    else:
        open_amount = base_amount
        reason = f"side sell → open 1x"
 
    try:
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=order_side,
            amount=open_amount,
            params={'posSide': opposite_side, 'leverage': 20}
        )
        log_auto_open(f"{acc_name} | 🚀🚀🚀 Opened {order_side.upper()} {token} {opposite_side.upper()} | "
                f"amount={open_amount:.2f} | {reason} | Order: {order['id']}")
        return True
    except Exception as e:
        log(f"{acc_name} | Open opposite failed {token}: {str(e)}")
        return False

# === CLOSE ALL ===
def close_all_token(exchange, acc_name):
    try:
        positions = exchange.fetch_positions(None, params={'type': 'swap'})
        active = [p for p in positions if float(p['contracts']) > 0]
        for p in active:
            symbol = p['symbol']
            side = 'sell' if p['side'] == 'long' else 'buy'
            amount = float(p['contracts'])
            try:
                order = exchange.create_order(symbol, 'market', side, amount, params={'posSide': p['side']})
                log(f"{acc_name} | Close ALL {extract_token(symbol)} {p['side'].upper()} | Order: {order['id']}")
                
            except Exception as e:
                log(f"{acc_name} | Close Error {extract_token(symbol)}: {e}")
    except Exception as e:
        log(f"{acc_name} | Close All Error: {e}")

# === CHECK DCA CONDITIONS ===
def check_token_conditions(token, position_data, account_index, exchange, symbol):
    """
    Kiểm tra điều kiện và thực hiện DCA nếu thỏa mãn.
    Trả về tuple: (valid: bool, action: str, price_change: str, pnl: str, order_status: str)
    """
    token_amount = get_token_amount(token, account_index)
    if token_amount <= 0:
        return False, None, None, None, "No amount config"

    try:
        if len(position_data) == 1:
            pos = position_data[0]
            side = pos['side']
            ep = pos['entryPrice']
            mp = pos['markPrice']
            pnl = pos['pnl']
            price_change = round(((mp - ep) / ep * 100), 2) if ep != 0 else 0

            order_side = None
            pos_side = None
            amount_to_trade = token_amount

            if side == 'long' and mp < ep * 0.1:
                order_side = 'buy'
                pos_side = 'long'
            elif side == 'short' and mp > ep * 1.9:
                order_side = 'sell'
                pos_side = 'short'

            if order_side:
                order = exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side=order_side,
                    amount=amount_to_trade,
                    params={'posSide': pos_side, 'leverage': 20}
                )

                # Lấy thông tin từ response để tính USDT value
                info = order.get('info', {})
                notional_usd_str = info.get('notional') or info.get('fillNotionalUsd') or info.get('notionalUsd') or '0'
                notional_usd = float(notional_usd_str)

                if notional_usd > 0:
                    usdt_value = round(notional_usd, 2)
                    order_status = f"~{usdt_value} USDT"
                else:
                    # Fallback: Tính chuẩn theo amount (số hợp đồng) * contract size * giá
                    try:
                        market_info = exchange.market(symbol)
                        contract_size = float(market_info.get('contractSize', 1))
                    except Exception:
                        contract_size = 1
                    
                    avg_px_str = info.get('avgPx') or order.get('average') or 0
                    avg_px = float(avg_px_str) if float(avg_px_str) > 0 else float(pos['markPrice'])
                    
                    filled_str = order.get('filled') or info.get('accFillSz') or info.get('sz') or amount_to_trade
                    filled = float(filled_str)
                    
                    usdt_value = round(filled * contract_size * avg_px, 2)
                    order_status = f"~{usdt_value} USDT (calc)"

                action_str = f"{pos_side.capitalize()} {amount_to_trade}"
                return True, action_str, f"{price_change:+.2f}%", f"{pnl:+.2f}", order_status

            return False, None, None, None, "Skip"

        elif len(position_data) == 2:
            long_pos = next((p for p in position_data if p['side'] == 'long'), None)
            short_pos = next((p for p in position_data if p['side'] == 'short'), None)
            if not (long_pos and short_pos):
                return False, None, None, None, "Invalid dual"

            if long_pos['pnl'] < 0 and short_pos['pnl'] < 0:
                long_change = round(((long_pos['markPrice'] - long_pos['entryPrice']) / long_pos['entryPrice'] * 100), 2)
                short_change = round(((short_pos['markPrice'] - short_pos['entryPrice']) / short_pos['entryPrice'] * 100), 2)

                order_side = None
                pos_side = None
                multiplier = 1

                if long_pos['pnl'] > short_pos['pnl'] and long_change < 0:
                    order_side = 'buy'
                    pos_side = 'long'
                    multiplier = 2
                elif short_pos['pnl'] > long_pos['pnl'] and short_change > 0:
                    order_side = 'sell'
                    pos_side = 'short'
                    multiplier = 1

                if order_side:
                    amount_to_trade = token_amount * multiplier

                    order = exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=order_side,
                        amount=amount_to_trade,
                        params={'posSide': pos_side, 'leverage': 20}
                    )
                    #log(f"order: {order}")

                    # Lấy thông tin từ response
                    info = order.get('info', {})
                    #log(f"info: {info}")
                    notional_usd_str = info.get('notional') or info.get('fillNotionalUsd') or info.get('notionalUsd') or '0'
                    notional_usd = float(notional_usd_str)

                    if notional_usd > 0:
                        usdt_value = round(notional_usd, 2)
                        order_status = f"~{usdt_value} USDT"
                    else:
                        # Fallback: Tính chuẩn theo amount (số hợp đồng) * contract size * giá
                        try:
                            market_info = exchange.market(symbol)
                            contract_size = float(market_info.get('contractSize', 1))
                        except Exception:
                            contract_size = 1
                        
                        avg_px_str = info.get('avgPx') or order.get('average') or 0
                        avg_px = float(avg_px_str) if float(avg_px_str) > 0 else float(long_pos['markPrice'])
                        
                        filled_str = order.get('filled') or info.get('accFillSz') or info.get('sz') or amount_to_trade
                        filled = float(filled_str)
                        
                        usdt_value = round(filled * contract_size * avg_px, 2)
                        order_status = f"~{usdt_value} USDT (calc)"

                    pnl_str = f"L:{long_pos['pnl']:+.2f} S:{short_pos['pnl']:+.2f}"
                    action_str = f"{pos_side.capitalize()} {amount_to_trade}"

                    return True, action_str, f"L:{long_change}% S:{short_change}%", pnl_str, order_status

        return False, None, None, None, "Skip"

    except Exception as e:
        log(f"Order failed {token}: {e}")
        return False, None, None, None, f"Error: {str(e)[:30]}"
# === CHECK DCA CONDITIONS ===


# === GET NEXT TOKEN TO DCA ===
def get_next_token(single_position_tokens, dual_position_tokens, account_name, account_index, exchange):
    global last_token, processed_tokens

    if last_token is None:
        processed_tokens.clear()

    # Single positions (reverse)
    for i in range(len(single_position_tokens) - 1, -1, -1):
        token, pos_data = single_position_tokens[i]
        if token in processed_tokens:
            continue
        symbol = f"{token}/USDT:USDT"
        valid, action, price_change, pnl, order_status = check_token_conditions(token, pos_data, account_index, exchange, symbol)
        if valid:
            processed_tokens.add(token)
            last_token = token
            save_normalized_config()
            return token, action, price_change, pnl, order_status, False
        processed_tokens.add(token)
        save_normalized_config()

    # Dual positions (reverse)
    for i in range(len(dual_position_tokens) - 1, -1, -1):
        token, pos_data = dual_position_tokens[i]
        if token in processed_tokens:
            continue
        symbol = f"{token}/USDT:USDT"
        valid, action, price_change, pnl, order_status = check_token_conditions(token, pos_data, account_index, exchange, symbol)
        if valid:
            processed_tokens.add(token)
            last_token = token
            save_normalized_config()
            return token, action, price_change, pnl, order_status, False
        processed_tokens.add(token)
        save_normalized_config()

    return None, None, None, None, "None", True


# === PROCESS SL & OPEN OPPOSITE ===
def process_account_sl_op(idx, acc):
    global last_run_sl_op
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    minute = now.minute

    if minute == last_run_sl_op[idx]:
        return

    if minute not in time_set.get(idx, []) and minute not in time_open.get(idx, []):
        return

    balance, single, dual, exchange = get_cached_or_fresh(acc, idx, force=False)
    all_pos_tuples = single + dual
    active_pos = [p for _, poss in all_pos_tuples for p in poss]

    if balance > acc['balance_want'] and minute in time_open.get(idx, []): 
        balance, _, _, exchange = get_cached_or_fresh(acc, idx, force=True)
        if exchange and balance > acc['balance_want']:
            close_all_token(exchange, acc['name'])
            
            # Đợi sàn khớp lệnh và lấy balance THỰC TẾ sau khi đóng
            time.sleep(1)
            fresh_balance, _, _, _ = get_cached_or_fresh(acc, idx, force=True)
            
            # Thuật toán nhảy bậc Target (Tự động tìm mốc 0.5 tiếp theo)
            old_want = acc['balance_want']
            new_want = math.floor(fresh_balance * 2) / 2 + 0.5
            
            # Đảm bảo target mới luôn tăng ít nhất 0.5 (phòng trường hợp trượt giá)
            acc['balance_want'] = max(old_want + 0.5, new_want)
            save_normalized_config()
            
            add_dca_result(acc['name'], "CLOSED ALL", "—", "—", f"{fresh_balance:.2f}", f"> {old_want} (Target mới: {acc['balance_want']})")
            log(f"💰 {acc['name']} ĐÃ ĐÓNG TOÀN BỘ VỊ THẾ! Đã nâng Balance_want lên {acc['balance_want']} USDT và lưu vào file.")
            
        last_run_sl_op[idx] = minute
        return

    if not active_pos:
        last_run_sl_op[idx] = minute
        return

    force_done = False

    for pos in active_pos:
        symbol = pos['symbol']

        # === KIỂM TRA ĐÓNG LỆNH SHORT KHẨN CẤP NẾU GIÁ X3 ===
        if pos['side'] == 'short' and pos['markPrice'] >= pos['entryPrice'] * 4:
            try:
                amount = pos['contracts']
                # Đóng lệnh short bằng lệnh market buy
                order = exchange.create_order(
                    symbol=symbol,
                    type='market',
                    side='buy',
                    amount=amount,
                    params={'posSide': 'short'}
                )
                log(f"🚨 EMERGENCY CLOSE | {acc['name']} | {symbol} SHORT đóng gấp vì giá x3! (Entry: {pos['entryPrice']} -> Mark: {pos['markPrice']})")
                continue  # Đã đóng thì bỏ qua luôn các lệnh cài SL/Mở Opposite bên dưới
            except Exception as e:
                log(f"❌ Lỗi khi đóng gấp {acc['name']} {pos['symbol']}: {e}")
                continue  # Nếu lỗi cũng bỏ qua để tránh văng bot

        if minute in time_set.get(idx, []):
            check_and_set_stop_loss(exchange, symbol, pos, acc['name'])

        if minute in time_open.get(idx, []):
            if not force_done:
                _, _, _, exchange = get_cached_or_fresh(acc, idx, force=True)
                force_done = True
            open_opposite(exchange, symbol, pos['side'], pos['markPrice'], pos['entryPrice'], pos, acc['name'], idx, active_pos)

    last_run_sl_op[idx] = minute

# def get_sorted_unique_token_amounts(idx):
    amounts_dict = token_amounts_map.get(idx, {})
    items = []
    seen = set()
    
    for key, amount in amounts_dict.items():
        if isinstance(key, str):
            tokens = [key]
        else:
            tokens = list(key)
            
        for token in tokens:
            if token not in seen:
                items.append((token, amount))
                seen.add(token)
                
    sorted_items = sorted(items, key=lambda x: (len(x[0]), x[0].upper()))
    return sorted_items





# === DCA CHECK ===
def run_dca_check():
    global current_account_index, last_processed_minute, processed_tokens, last_token, dca
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    current_minute = now.minute

    #target = [0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,51,54,57]
    #target =[1,4,7,10,13,16,19,22,25,28,31,34,37,40,43,46,49,52,55,58]
    #target =[2,5,8,11,14,17,20,23,26,29,32,35,38,41,44,47,50,53,56,59]
    # Tạo target tự động dựa vào dca_target_offset hiện tại
    target = [i * 3 + dca_target_offset for i in range(20)]
        
    if current_minute not in target or last_processed_minute == current_minute:
        return

    last_processed_minute = current_minute

    action_found = False
    accounts_checked = 0
    max_checks = len(accounts)

    while accounts_checked < max_checks and not action_found:
        account = accounts[current_account_index]
        balance, single_position_tokens, dual_position_tokens, exchange = get_cached_or_fresh(
            account, current_account_index, force=False
        )

        # Kiểm tra vượt balance (cần fresh data nếu vượt)
        if balance > account['balance_want'] :
            balance, _, _, exchange = get_cached_or_fresh(account, current_account_index, force=True)
            if exchange and balance > account['balance_want']:
                close_all_token(exchange, account['name'])
                
                # Đợi sàn khớp lệnh và lấy balance THỰC TẾ sau khi đóng
                time.sleep(1)
                fresh_balance, _, _, _ = get_cached_or_fresh(account, current_account_index, force=True)
                
                # Thuật toán nhảy bậc Target (Tự động tìm mốc 0.5 tiếp theo)
                old_want = account['balance_want']
                new_want = math.floor(fresh_balance * 2) / 2 + 0.5
                
                # Đảm bảo target mới luôn tăng ít nhất 0.5 (phòng trường hợp trượt giá)
                account['balance_want'] = max(old_want + 0.5, new_want)
                save_normalized_config()
                
                add_dca_result(account['name'], "CLOSED ALL", "—", "—", f"{fresh_balance:.2f}", f"> {old_want} (Target mới: {account['balance_want']})")
                log(f"💰 {account['name']} ĐÃ ĐÓNG TOÀN BỘ VỊ THẾ! Đã nâng Balance_want lên {account['balance_want']} USDT và lưu vào file.")
                
                current_account_index = (current_account_index + 1) % len(accounts)
                accounts_checked += 1
                continue

        if dca == 0:
            break

        if exchange is None:
                break

        # Tìm token tiếp theo (giữ nguyên logic get_next_token gốc)
        next_token, action, price_change, pnl, order_status, switch = get_next_token(
            single_position_tokens, dual_position_tokens, account['name'], current_account_index, exchange
        )

        single_names = ', '.join([t[0] for t in single_position_tokens]) or 'None'
        dual_names = ', '.join([t[0] for t in dual_position_tokens]) or 'None'

        if next_token:
            # Refresh trước khi thực hiện lệnh thật (an toàn hơn)
            _, _, _, exchange = get_cached_or_fresh(account, current_account_index, force=True)
            if exchange:
                add_dca_result(account['name'], action, next_token, price_change, pnl, order_status)
                log(f"DCA {account['name']} | {next_token} | {action} | {price_change} | {pnl} | {order_status}")

            # KHÔNG clear processed_tokens & last_token ở đây → để tiếp tục check token tiếp theo trong account này
            # Chỉ clear khi switch account (ở else bên dưới)
            action_found = True
            # KHÔNG break → cho phép DCA tiếp nếu còn token khác trong account

        else:
            log(f"No valid token for {account['name']} ({single_names} | {dual_names}), switching...")
            current_account_index = (current_account_index + 1) % len(accounts)
            processed_tokens.clear()
            last_token = None
            accounts_checked += 1
            save_normalized_config()
            continue

    if not action_found:
        log("Checked all accounts in this cycle, no valid DCA found")

# === FLIP DCA ===
def check_and_flip_dca():
    global previous_total_balance, dca, dca_change_history

    total_balance = sum(get_cached_or_fresh(acc, i, force=False)[0] for i, acc in enumerate(accounts))
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now_str = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

    if previous_total_balance is None:
        reason = f"Initial check: {total_balance:.2f}"
    else:
        if total_balance < previous_total_balance * 0.995 and total_balance > previous_total_balance * 0.95: 
            dca = 1 - dca
            reason = f"Flipped to {dca} | total {total_balance:.2f} < prev {previous_total_balance:.2f}"
            save_normalized_config()
        else:
            reason = f"Kept {dca} | total {total_balance:.2f} >= prev {previous_total_balance:.2f}"

    dca_change_history.append({'time': now_str, 'reason': reason})
    if len(dca_change_history) > 10:
        dca_change_history.pop(0)

    previous_total_balance = total_balance
    log(reason)




def get_acc_pos_stats(idx):
    """Tính tổng len(non_hedge_less_1) + len(hedge) từ cache"""
    cached = position_cache.get(idx)
    if not cached: return 10, [], [] # Max out nếu chưa có data cache
    
    single = cached['single']
    dual = cached['dual']
    non_hedge_less_1 = []
    hedge_positions = [t for t, _ in dual]

    for token, poss in single:
        for pos in poss:
            mark = pos['markPrice']
            entry = pos['entryPrice']
            if entry == 0: continue
            pct = ((mark - entry) / entry) * 100
            
            # Logic: < 1% profit thì đưa vào less_1
            if pos['side'] == 'long' and pct <= 2:
                non_hedge_less_1.append(token)
            elif pos['side'] == 'short' and pct >= -2: 
                non_hedge_less_1.append(token)

    return len(non_hedge_less_1) + len(hedge_positions), non_hedge_less_1, hedge_positions

def get_utc0_change(symbol, tickers):
    """Tính % biến động dựa trên mốc 0h UTC (7h sáng VN)"""
    tick = tickers.get(symbol)
    if not tick: return 999
    info = tick.get('info', {})
    
    sodUtc0_raw = info.get('sodUtc0')
    
    # Xử lý an toàn nếu API OKX trả về chuỗi rỗng '' hoặc None
    if not sodUtc0_raw:
        sodUtc0 = float(tick['last'])
    else:
        try:
            sodUtc0 = float(sodUtc0_raw)
        except ValueError:
            sodUtc0 = float(tick['last'])
            
    if sodUtc0 == 0: return 999
    return ((tick['last'] - sodUtc0) / sodUtc0) * 100

# def find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates):
#     ref_symbol = f"{ref_token}/USDT:USDT" if ref_token != 'BTC' else 'BTC/USDT:USDT'
#     ref_change = get_utc0_change(ref_symbol, tickers)
    
#     # 📝 DANH SÁCH THEO DÕI: Gõ tên các token bạn thấy trên Dashboard vào đây để bot in lý do bỏ qua
#     TRACKED_TOKENS = ['ADA', 'CRV', 'DOGE', 'SOL', 'MERL']

#     for symbol, ticker in tickers.items():
#         if not symbol.endswith('/USDT:USDT'): continue

#         token_name = extract_token(symbol)
#         if token_name == ref_token: continue

#         is_tracking = token_name in TRACKED_TOKENS

#         change = get_utc0_change(symbol, tickers)
        
#         # 1. So sánh % Change 24h
#         if change >= ref_change: 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua vì % Change ({change:.2f}%) KHÔNG THẤP HƠN mốc {ref_token} ({ref_change:.2f}%)")
#             continue 

#         market = exchange.markets.get(symbol)
#         if not market: 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua vì không lấy được thông tin market OKX.")
#             continue

#         # --- BẮT ĐẦU SỬA LỖI ĐÒN BẨY TẠI ĐÂY ---
#         market_info = market.get('info', {})
#         # Quét cả 'maxLvg' và 'lever' đề phòng OKX đổi tên field
#         max_lvg_raw = market_info.get('maxLvg') or market_info.get('lever') or market_info.get('leverage')
        
#         try:
#             # Nếu sàn không trả về data, ngầm định các cặp Swap USDT đều hỗ trợ >= 20x
#             max_lvg = float(max_lvg_raw) if max_lvg_raw else 20.0 
#         except ValueError:
#             max_lvg = 20.0

#         # 2. Kiểm tra Đòn bẩy tối đa
#         if max_lvg < 20: 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua vì Max Leverage ({max_lvg}x) nhỏ hơn 20x.")
#             continue
#         # --- KẾT THÚC SỬA LỖI ĐÒN BẨY ---

#         fr_data = funding_rates.get(symbol)
#         if not fr_data: 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua vì không lấy được Funding Rate.")
#             continue
            
#         try:
#             fr = float(fr_data.get('info', {}).get('fundingRate', fr_data.get('fundingRate', 0)))
#         except:
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua do lỗi parse Funding Rate.")
#             continue

#         # 3. Kiểm tra Funding Rate (sai số 1e-5)
#         is_005 = abs(fr - 0.00005) <= 1e-5 
#         if direction == 'long' and not (is_005 or fr < 0): 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua (LONG) vì Funding Rate ({fr:.6f}) không phải 0.0050% hoặc âm.")
#             continue
#         if direction == 'short' and not (is_005 or fr > 0): 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua (SHORT) vì Funding Rate ({fr:.6f}) không phải 0.0050% hoặc dương.")
#             continue

#         # --- BẮT ĐẦU TÍNH TOÁN AMOUNT CHUẨN ---
#         last_price = ticker['last']
#         contract_size = float(market.get('contractSize', 1))
        
#         # Giá trị thực tế của 1 hợp đồng (USDT)
#         one_contract_value = last_price * contract_size
        
#         # Số lượng hợp đồng theo lý thuyết với pos_size_usdt
#         raw_amount = pos_size_usdt / one_contract_value
        
#         # Lấy bước nhảy số lượng của OKX (thường là 1, 0.1, hoặc 0.01)
#         amount_step = float(market.get('precision', {}).get('amount', 1))
        
#         # Làm tròn xuống theo bước nhảy để đảm bảo không bao giờ vượt quá pos_size_usdt
#         # Cộng thêm 1e-9 để tránh lỗi sai số thập phân của Python
#         amount = math.floor((raw_amount + 1e-9) / amount_step) * amount_step
        
#         # Cắt gọt rác thập phân thừa của Python sau phép nhân
#         amount = round(amount, 8)
            
#         # 4. Kiểm tra sức mua
#         if amount <= 0: 
#             if is_tracking: log(f"🔎 [DEBUG {token_name}] Bị bỏ qua vì 4 USDT không đủ mua mức tối thiểu (1 Hợp đồng cần {amount_step * one_contract_value:.2f} USDT).")
#             continue

#         # Độ lớn vị thế thực tế
#         actual_usdt = amount * one_contract_value

#         try:
#             order_side = 'buy' if direction == 'long' else 'sell'
            
#             # === TEST MODE: Tạm vô hiệu hóa lệnh gọi mở thật ===
#             # order = exchange.create_order(
#             #     symbol=symbol,
#             #     type='market',
#             #     side=order_side,
#             #     amount=amount,
#             #     params={'posSide': direction, 'tdMode': 'cross', 'leverage': 20} 
#             # )
#             # IN LOG GIẢ LẬP ĐỂ TEST:
#             log(f"[DRY-RUN LỆNH 1] Giả lập mở {order_side.upper()} {symbol} | Amount: {amount} | posSide: {direction}")
            
#             return token_name, amount, actual_usdt, ref_change, change
#         except Exception as e:
#             log(f"Auto Open | Bỏ qua {symbol} do lỗi API mở lệnh: {e}")
#             continue

#     return None, 0, 0, ref_change, 0

# def find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates):
#     ref_symbol = f"{ref_token}/USDT:USDT" if ref_token != 'BTC' else 'BTC/USDT:USDT'
#     ref_change = get_utc0_change(ref_symbol, tickers)
    
#     # 1. Tạo danh sách tất cả các token và Sắp xếp % Change GIẢM DẦN
#     all_tokens = []
#     for symbol, ticker in tickers.items():
#         if not symbol.endswith('/USDT:USDT'): continue
#         change = get_utc0_change(symbol, tickers)
#         if change == 999: continue # Bỏ qua các token bị lỗi API
#         all_tokens.append((symbol, change))
        
#     # Sort giảm dần (Token tăng mạnh nhất ở trên cùng, giảm sâu nhất ở dưới cùng)
#     all_tokens.sort(key=lambda x: x[1], reverse=True)

#     # 2. Quét từ trên xuống dưới. Chỉ xét các token thấp hơn mốc
#     for symbol, change in all_tokens:
#         if change >= ref_change: 
#             continue # Im lặng bỏ qua tất cả các token nằm trên mốc

#         token_name = extract_token(symbol)
#         if token_name == ref_token: continue

#         # --- TỪ ĐÂY BẮT ĐẦU XÉT CÁC TOKEN DƯỚI MỐC VÀ IN LOG NẾU TRƯỢT ---
#         market = exchange.markets.get(symbol)
#         if not market: 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Không có thông tin Market.")
#             continue

#         # Kiểm tra Đòn bẩy
#         market_info = market.get('info', {})
#         max_lvg_raw = market_info.get('maxLvg') or market_info.get('lever')
#         try:
#             max_lvg = float(max_lvg_raw) if max_lvg_raw else 20.0 
#         except ValueError:
#             max_lvg = 20.0

#         if max_lvg < 20: 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Max Leverage ({max_lvg}x) < 20x.")
#             continue

#         # Kiểm tra Funding Rate
#         fr_data = funding_rates.get(symbol)
#         if not fr_data: 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Không lấy được Funding Rate.")
#             continue
            
#         try:
#             fr = float(fr_data.get('info', {}).get('fundingRate', fr_data.get('fundingRate', 0)))
#         except:
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi parse Funding Rate.")
#             continue

#         is_005 = abs(fr - 0.00005) <= 1e-5 
#         if direction == 'long' and not (is_005 or fr < 0): 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Tìm LONG nhưng Funding ({fr:.6f}) không hợp lệ.")
#             continue
#         if direction == 'short' and not (is_005 or fr > 0): 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Tìm SHORT nhưng Funding ({fr:.6f}) không hợp lệ.")
#             continue

#         # Tính toán sức mua
#         ticker = tickers[symbol]
#         last_price = ticker['last']
#         contract_size = float(market.get('contractSize', 1))
        
#         one_contract_value = last_price * contract_size
#         raw_amount = pos_size_usdt / one_contract_value
#         amount_step = float(market.get('precision', {}).get('amount', 1))
        
#         amount = math.floor((raw_amount + 1e-9) / amount_step) * amount_step
#         amount = round(amount, 8)
            
#         if amount <= 0: 
#             log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: {pos_size_usdt} USDT không đủ mua mức tối thiểu 1 Step.")
#             continue

#         # Vượt qua mọi bài test -> CHỌN TOKEN NÀY VÀ DỪNG QUÉT!
#         actual_usdt = amount * one_contract_value

#         try:
#             order_side = 'buy' if direction == 'long' else 'sell'
            
#             # GIẢ LẬP LỆNH:
#             log(f"✅ [CHỌN {token_name} | {change:.2f}%] Thỏa mãn toàn bộ! Giả lập mở {order_side.upper()} | Amount: {amount} | posSide: {direction}")
            
#             return token_name, amount, actual_usdt, ref_change, change
#         except Exception as e:
#             log(f"Auto Open | Lỗi API mở lệnh với {symbol}: {e}")
#             continue

#     return None, 0, 0, ref_change, 0

# def auto_open_positions_job():
#     global last_auto_open_run, skip_next_15m
#     tz = pytz.timezone('Asia/Ho_Chi_Minh')
#     minute = datetime.now(tz).minute

#     if minute not in [0, 15, 30, 45] or last_auto_open_run == minute:
#         return
        
#     last_auto_open_run = minute

#     if skip_next_15m:
#         log(f"Auto Open | Bỏ qua mốc {minute}' vì đã mở x2 ở chu kỳ trước.")
#         skip_next_15m = False
#         return

#     # 1. Tìm tài khoản có tổng < nhất
#     best_acc_idx = -1
#     min_sum = 9999
#     ref_lists = ([], [])

#     for i in range(11):
#         s, nh_less, h_pos = get_acc_pos_stats(i)
#         if s < min_sum: # Dấu < đảm bảo nếu trùng nhau sẽ ưu tiên tài khoản trước (nhỏ hơn)
#             min_sum = s
#             best_acc_idx = i
#             ref_lists = (nh_less, h_pos)

#     if best_acc_idx == -1: return

#     acc = accounts[best_acc_idx]
#     _, _, _, exchange = get_cached_or_fresh(acc, best_acc_idx, force=False)
#     if not exchange: return

#     direction = 'long' if best_acc_idx % 2 == 0 else 'short'
#     pos_size_usdt = acc.get('pos_size_usdt', 4.0)
    
#     nh_less, h_pos = ref_lists
#     ref_token = nh_less[0] if nh_less else (h_pos[0] if h_pos else 'BTC')

#     try:
#         exchange.load_markets()
#         tickers = exchange.fetch_tickers(params={'instType': 'SWAP'})
#         funding_rates = exchange.fetch_funding_rates(params={'instType': 'SWAP'})
#     except Exception as e:
#         log(f"Auto Open | Lỗi lấy data thị trường OKX: {e}")
#         return

#     log(f"Auto Open | OKX_{best_acc_idx} đc chọn (Tổng={min_sum}) | Hướng: {direction.upper()} | Mốc: {ref_token}")

#     if min_sum < 10:
#         current_ref = ref_token
#         for step in range(3):
#             new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, current_ref, pos_size_usdt, tickers, funding_rates)
#             if new_token:
#                 log(f"Auto Open [{step+1}/3] OKX_{best_acc_idx} | Giả lập mở {direction.upper()} {new_token} ({amount} = ~{actual_usdt:.2f} USDT) | Mốc: {current_ref} ({ref_chg:.2f}%) -> Lấy {new_token} ({new_chg:.2f}%)")
#                 current_ref = new_token 
#                 time.sleep(1)
#             else:
#                 log(f"Auto Open [{step+1}/3] OKX_{best_acc_idx} | Không tìm thấy token thỏa điều kiện so với {current_ref}.")
#                 break
#     else:
#         new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates)
#         if new_token:
#             log(f"Auto Open [1/2] OKX_{best_acc_idx} | Giả lập mở {direction.upper()} {new_token} ({amount} = ~{actual_usdt:.2f} USDT) | Mốc: {ref_token} ({ref_chg:.2f}%) -> Lấy {new_token} ({new_chg:.2f}%)")
#             time.sleep(1)
#             try:
#                 # === TEST MODE: Tạm vô hiệu hóa lệnh x2 thật ===
#                 # exchange.create_order(
#                 #     symbol=f"{new_token}/USDT:USDT", type='market', side='buy' if direction == 'long' else 'sell',
#                 #     amount=amount, params={'posSide': direction, 'tdMode': 'cross', 'leverage': 20}
#                 # )
#                 log(f"[DRY-RUN LỆNH 2] Giả lập mở x2 thêm {new_token} | Amount: {amount} | posSide: {direction}")
                
#                 log(f"Auto Open [2/2] OKX_{best_acc_idx} | Đã MỞ GIẢ LẬP thêm lệnh thứ 2 cho {new_token} với cùng độ lớn.")
#             except Exception as e:
#                 log(f"Auto Open [2/2] OKX_{best_acc_idx} | Lỗi khi mở lệnh thứ 2 cho {new_token}: {e}")
            
#             skip_next_15m = True
#             log(f"Auto Open | Tổng={min_sum} >= 10 -> Kích hoạt bỏ qua mốc thời gian tiếp theo.")
#         else:
#             log(f"Auto Open | OKX_{best_acc_idx} | Không tìm thấy token thỏa điều kiện so với {ref_token}.")


# 

def find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates, existing_tokens):
    # Nếu ref_token là 'HIGHEST' -> Không so sánh mốc, chỉ tìm token có % giảm/tăng mạnh nhất hợp lệ
    if ref_token == 'HIGHEST':
        ref_change = float('inf')  # Để tất cả các token đều nhỏ hơn mức này ban đầu
    else:
        ref_symbol = f"{ref_token}/USDT:USDT" if ref_token != 'BTC' else 'BTC/USDT:USDT'
        ref_change = get_utc0_change(ref_symbol, tickers)
    
    # 1. Tạo danh sách tất cả các token và Sắp xếp % Change GIẢM DẦN
    all_tokens = []
    for symbol, ticker in tickers.items():
        if not symbol.endswith('/USDT:USDT'): continue
        change = get_utc0_change(symbol, tickers)
        if change == 999: continue 
        all_tokens.append((symbol, change))
        
    all_tokens.sort(key=lambda x: x[1], reverse=True)

    # 2. Xử lý logic vòng lặp Wrap-around (Nếu chạm đáy bảng thì vòng lên đỉnh tìm lại)
    start_idx = 0
    if ref_token != 'HIGHEST':
        for i, (sym, chg) in enumerate(all_tokens):
            if chg < ref_change:
                start_idx = i
                break
                
    # Nối mảng để tạo hiệu ứng vòng lặp (Tìm từ mốc xuống đáy, không thấy thì tìm từ đỉnh về lại mốc)
    wrapped_tokens = all_tokens[start_idx:] + all_tokens[:start_idx]

    for symbol, change in wrapped_tokens:
        # Nếu đang ở chế độ dò tịnh tiến (không phải TÀI KHOẢN TRỐNG), không được dò các token cao hơn mốc
        # Đã xử lý bằng mảng wrapped_tokens, nên nếu nó vòng lại gặp change >= ref_change thì cứ lặng lẽ bỏ qua
        if ref_token != 'HIGHEST' and change >= ref_change: 
            continue 

        token_name = extract_token(symbol)
        if token_name == ref_token: continue

        if token_name in existing_tokens:
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Tài khoản ĐÃ CÓ SẴN token này.")
            continue

        market = exchange.markets.get(symbol)
        if not market: 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Không có thông tin Market.")
            continue

        market_info = market.get('info', {})
        max_lvg_raw = market_info.get('maxLvg') or market_info.get('lever')
        try:
            max_lvg = float(max_lvg_raw) if max_lvg_raw else 20.0 
        except ValueError:
            max_lvg = 20.0

        if max_lvg < 20: 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Max Leverage ({max_lvg}x) < 20x.")
            continue

        fr_data = funding_rates.get(symbol)
        if not fr_data: 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Không lấy được Funding Rate.")
            continue
            
        try:
            fr = float(fr_data.get('info', {}).get('fundingRate', fr_data.get('fundingRate', 0)))
        except:
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi parse Funding Rate.")
            continue

        is_005 = abs(fr - 0.00005) <= 1e-5 
        if direction == 'long' and not (is_005 or fr < 0): 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Tìm LONG nhưng Funding ({fr:.6f}) không hợp lệ.")
            continue
        if direction == 'short' and not (is_005 or fr > 0): 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: Tìm SHORT nhưng Funding ({fr:.6f}) không hợp lệ.")
            continue

        ticker = tickers[symbol]
        last_price = ticker['last']
        contract_size = float(market.get('contractSize', 1))
        
        one_contract_value = last_price * contract_size
        raw_amount = pos_size_usdt / one_contract_value
        amount_step = float(market.get('precision', {}).get('amount', 1))
        
        amount = math.floor((raw_amount + 1e-9) / amount_step) * amount_step
        amount = round(amount, 8)
            
        if amount <= 0: 
            log(f"🔎 [Skip {token_name} | {change:.2f}%] Lỗi: {pos_size_usdt} USDT không đủ mua mức tối thiểu 1 Step.")
            continue

        actual_usdt = amount * one_contract_value

        # === THỰC THI MỞ LỆNH THẬT ===
                # === THỰC THI MỞ LỆNH THẬT ===
        try:
            order_side = 'buy' if direction == 'long' else 'sell'
            
            # --- THÊM MỚI: BẮT BUỘC SÀN SET ĐÒN BẨY LÊN 20X TRƯỚC KHI VÀO LỆNH ---
            try:
                exchange.set_leverage(20, symbol, params={'mgnMode': 'cross', 'posSide': direction})
            except Exception as e:
                # Nếu API báo lỗi (ví dụ: đòn bẩy đã là 20x sẵn rồi), ta cứ im lặng bỏ qua
                pass 
                
            order = exchange.create_order(
                symbol=symbol,
                type='market',
                side=order_side,
                amount=amount,
                params={'posSide': direction, 'tdMode': 'cross'} 
            )

            
            log(f"✅ [CHỌN {token_name} | {change:.2f}%] ĐÃ MỞ LỆNH THẬT {order_side.upper()} | Amount: {amount} | OrderID: {order['id']}")
            
            return token_name, amount, actual_usdt, ref_change, change
        except Exception as e:
            log(f"❌ LỖI API MỞ LỆNH VỚI {symbol}: {e}")
            continue

    return None, 0, 0, ref_change, 0

# def auto_open_positions_job():
#     global last_auto_open_run, skip_next_15m
#     tz = pytz.timezone('Asia/Ho_Chi_Minh')
#     minute = datetime.now(tz).minute

#     if minute not in [0, 15, 30, 45] or last_auto_open_run == minute:
#         return
        
#     last_auto_open_run = minute

#     if skip_next_15m:
#         log(f"Auto Open | Bỏ qua mốc {minute}' vì đã mở x2 ở chu kỳ trước.")
#         skip_next_15m = False
#         return

#     # 1. Tìm tài khoản có tổng < nhất
#     best_acc_idx = -1
#     min_sum = 9999
#     ref_lists = ([], [])

#     for i in range(11):
#         s, nh_less, h_pos = get_acc_pos_stats(i)
#         if s < min_sum: # Dấu < đảm bảo nếu trùng nhau sẽ ưu tiên tài khoản trước (nhỏ hơn)
#             min_sum = s
#             best_acc_idx = i
#             ref_lists = (nh_less, h_pos)

#     if best_acc_idx == -1: return

#     acc = accounts[best_acc_idx]
#     # Lấy thêm danh sách single và dual để kiểm tra trùng token
#     _, single_pos, dual_pos, exchange = get_cached_or_fresh(acc, best_acc_idx, force=False)
#     if not exchange: return

#     # Lấy tất cả tên token đang có sẵn trong tài khoản
#     existing_tokens = set([t[0] for t in single_pos] + [t[0] for t in dual_pos])

#     direction = 'long' if best_acc_idx % 2 == 0 else 'short'
#     pos_size_usdt = acc.get('pos_size_usdt', 4.0)
    
#     nh_less, h_pos = ref_lists
#     ref_token = nh_less[0] if nh_less else (h_pos[0] if h_pos else 'BTC')

#     try:
#         exchange.load_markets()
#         tickers = exchange.fetch_tickers(params={'instType': 'SWAP'})
#         funding_rates = exchange.fetch_funding_rates(params={'instType': 'SWAP'})
#     except Exception as e:
#         log(f"Auto Open | Lỗi lấy data thị trường OKX: {e}")
#         return

#     log(f"Auto Open | OKX_{best_acc_idx} đc chọn (Tổng={min_sum}) | Hướng: {direction.upper()} | Mốc: {ref_token}")

#     if min_sum < 10:
#         current_ref = ref_token
#         for step in range(3):
#             # Truyền existing_tokens vào hàm để né
#             new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, current_ref, pos_size_usdt, tickers, funding_rates, existing_tokens)
#             if new_token:
#                 log(f"Auto Open [{step+1}/3] OKX_{best_acc_idx} | Giả lập mở {direction.upper()} {new_token} ({amount} = ~{actual_usdt:.2f} USDT) | Mốc: {current_ref} ({ref_chg:.2f}%) -> Lấy {new_token} ({new_chg:.2f}%)")
#                 current_ref = new_token 
                
#                 # THÊM TOKEN VỪA MỞ VÀO DANH SÁCH CẤM ĐỂ LỆNH SAU KHÔNG BỊ TRÙNG
#                 existing_tokens.add(new_token)
                
#                 time.sleep(1)
#             else:
#                 log(f"Auto Open [{step+1}/3] OKX_{best_acc_idx} | Không tìm thấy token thỏa điều kiện so với {current_ref}.")
#                 break
#     else:
#         new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates, existing_tokens)
#         if new_token:
#             log(f"Auto Open [1/2] OKX_{best_acc_idx} | Giả lập mở {direction.upper()} {new_token} ({amount} = ~{actual_usdt:.2f} USDT) | Mốc: {ref_token} ({ref_chg:.2f}%) -> Lấy {new_token} ({new_chg:.2f}%)")
#             time.sleep(1)
#             try:
#                 # === TEST MODE: Tạm vô hiệu hóa lệnh x2 thật ===
#                 # exchange.create_order(
#                 #     symbol=f"{new_token}/USDT:USDT", type='market', side='buy' if direction == 'long' else 'sell',
#                 #     amount=amount, params={'posSide': direction, 'tdMode': 'cross', 'leverage': 20}
#                 # )
#                 log(f"[DRY-RUN LỆNH 2] Giả lập mở x2 thêm {new_token} | Amount: {amount} | posSide: {direction}")
                
#                 log(f"Auto Open [2/2] OKX_{best_acc_idx} | Đã MỞ GIẢ LẬP thêm lệnh thứ 2 cho {new_token} với cùng độ lớn.")
#             except Exception as e:
#                 log(f"Auto Open [2/2] OKX_{best_acc_idx} | Lỗi khi mở lệnh thứ 2 cho {new_token}: {e}")
            
#             skip_next_15m = True
#             log(f"Auto Open | Tổng={min_sum} >= 10 -> Kích hoạt bỏ qua mốc thời gian tiếp theo.")
#         else:
#             log(f"Auto Open | OKX_{best_acc_idx} | Không tìm thấy token thỏa điều kiện so với {ref_token}.")

def auto_open_positions_job():
    global last_auto_open_run, resume_auto_open_time
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)
    minute = now.minute

    # Chia 1 giờ thành 4 khung (Slot 0, 1, 2, 3) đại diện cho các mốc 0', 15', 30', 45'
    current_slot = minute // 15
    
    # Cho phép bot đến trễ tối đa 5 phút do nghẽn API (ví dụ: mốc 15' được quét đến tận phút 20')
    valid_window = (minute % 15) <= 2

    # Chặn nếu không nằm trong khung giờ hợp lệ, hoặc slot này đã được xử lý rồi
    if not valid_window or last_auto_open_run == current_slot:
        return
        
    last_auto_open_run = current_slot


    # Chặn đứng bot nếu chưa hết thời gian Delay
    if resume_auto_open_time:
        if now < resume_auto_open_time:
            #log(f"Auto Open | Bỏ qua mốc {minute}' do đang Delay. Quét lại vào lúc: {resume_auto_open_time.strftime('%H:%M:%S')}")
            log_auto_open(f"💤 Bỏ qua mốc {minute}' do đang Delay. Quét lại vào lúc: {resume_auto_open_time.strftime('%H:%M:%S')}")
            return
        else:
            resume_auto_open_time = None # Đã qua thời gian nghỉ, reset lại bình thường

    best_acc_idx = -1
    min_sum = 9999
    ref_lists = ([], [])

    for i in range(11):
        s, nh_less, h_pos = get_acc_pos_stats(i)
        if s < min_sum: 
            min_sum = s
            best_acc_idx = i
            ref_lists = (nh_less, h_pos)

    if best_acc_idx == -1: return

    acc = accounts[best_acc_idx]
    _, single_pos, dual_pos, exchange = get_cached_or_fresh(acc, best_acc_idx, force=False)
    if not exchange: return

    existing_tokens = set([t[0] for t in single_pos] + [t[0] for t in dual_pos])

    direction = 'long' if best_acc_idx % 2 == 0 else 'short'
    pos_size_usdt = acc.get('pos_size_usdt', 4.0)
    
    nh_less, h_pos = ref_lists
    ref_token = nh_less[0] if nh_less else (h_pos[0] if h_pos else 'BTC')

    try:
        exchange.load_markets()
        tickers = exchange.fetch_tickers(params={'instType': 'SWAP'})
        funding_rates = exchange.fetch_funding_rates(params={'instType': 'SWAP'})
    except Exception as e:
        log(f"Auto Open | Lỗi lấy data thị trường OKX: {e}")
        return

    # Xác định số lượng lệnh cần mở dựa trên trạng thái tài khoản
    if min_sum == 0:
        #log(f"🚀 [TÀI KHOẢN TRỐNG] OKX_{best_acc_idx} | Bắt đầu chu kỳ MỚI 10 LỆNH | Hướng: {direction.upper()} | Mốc: Token cao nhất")
        log_auto_open(f"🚀 [TÀI KHOẢN TRỐNG] OKX_{best_acc_idx} | Bắt đầu chu kỳ MỚI 10 LỆNH | Hướng: {direction.upper()} | Mốc: Token cao nhất")
        current_ref = 'HIGHEST'
        loop_count = 10
    elif min_sum < 10:
        log_auto_open(f"Auto Open | OKX_{best_acc_idx} đc chọn (Tổng={min_sum}) | Mở 3 Lệnh | Hướng: {direction.upper()} | Mốc: {ref_token}")
        current_ref = ref_token
        loop_count = 3
    else:
        log_auto_open(f"Auto Open | OKX_{best_acc_idx} đc chọn (Tổng={min_sum}) | Mở x2 Lệnh | Hướng: {direction.upper()} | Mốc: {ref_token}")
        current_ref = ref_token
        loop_count = 1 

    # --- TIẾN HÀNH MỞ LỆNH LIÊN TIẾP ---
    if min_sum < 10: # (Bao gồm cả min_sum == 0)
        for step in range(loop_count):
            new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, current_ref, pos_size_usdt, tickers, funding_rates, existing_tokens)
            
            if new_token:
                #log(f"👉 [{step+1}/{loop_count}] OKX_{best_acc_idx} ĐÃ MỞ {direction.upper()} {new_token} (~{actual_usdt:.2f}$) | Mốc: {current_ref} -> {new_token} ({new_chg:.2f}%)")
                log_auto_open(f"👉 [{step+1}/{loop_count}] OKX_{best_acc_idx} ĐÃ MỞ {direction.upper()} {new_token} (~{actual_usdt:.2f}$) | Mốc: {current_ref} -> {new_token} ({new_chg:.2f}%)")
                current_ref = new_token 
                existing_tokens.add(new_token)
                
                # === LƯU/CẬP NHẬT SỐ LƯỢNG VÀO CẤU HÌNH NGAY LẬP TỨC ===
                token_tuple = (new_token,)
                token_amounts_map[best_acc_idx][token_tuple] = amount
                save_normalized_config()
                log(f"💾 Đã cập nhật token {new_token} = {amount} vào file token_config.txt.")
                
                time.sleep(1)
            else:
                log(f"⚠️ [{step+1}/{loop_count}] OKX_{best_acc_idx} | Hết chuỗi tìm kiếm, không tìm được token nào thêm so với {current_ref}.")
                break
    
    # --- TIẾN HÀNH MỞ LỆNH X2 (Khi tài khoản đã >= 10 vị thế) ---
    else:
        new_token, amount, actual_usdt, ref_chg, new_chg = find_and_open(exchange, direction, ref_token, pos_size_usdt, tickers, funding_rates, existing_tokens)
        if new_token:
            log_auto_open(f"👉 [1/2] OKX_{best_acc_idx} ĐÃ MỞ {direction.upper()} {new_token} (~{actual_usdt:.2f}$) | Mốc: {ref_token} ({ref_chg:.2f}%) -> Lấy {new_token} ({new_chg:.2f}%)")
            
            # === CẬP NHẬT AMOUNT TỪ LẦN ĐẦU (Không cập nhật lại khi nhồi x2) ===
            token_tuple = (new_token,)
            token_amounts_map[best_acc_idx][token_tuple] = amount
            save_normalized_config()
            log(f"💾 Đã cập nhật token {new_token} = {amount} vào file token_config.txt.")

            time.sleep(1)
            try:
                # --- THÊM MỚI: SET ĐÒN BẨY CHO LỆNH NHỒI ---
                try:
                    exchange.set_leverage(20, f"{new_token}/USDT:USDT", params={'mgnMode': 'cross', 'posSide': direction})
                except:
                    pass

                # LỆNH THẬT LẦN 2: Mở nhồi y hệt vị thế vừa rồi
                order2 = exchange.create_order(
                    symbol=f"{new_token}/USDT:USDT", type='market', side='buy' if direction == 'long' else 'sell',
                    amount=amount, params={'posSide': direction, 'tdMode': 'cross'}
                )

                #log(f"👉 [2/2] OKX_{best_acc_idx} ĐÃ MỞ NHỒI x2 THÊM {new_token} | OrderID: {order2['id']}")
                log_auto_open(f"👉 [2/2] OKX_{best_acc_idx} ĐÃ MỞ NHỒI x2 THÊM {new_token} | OrderID: {order2['id']}")
            except Exception as e:
                log(f"❌ [2/2] OKX_{best_acc_idx} Lỗi khi nhồi thêm lệnh {new_token}: {e}")
            
                        # Tạo MỐC THỜI GIAN CHUẨN (Khử độ trễ của API). VD: 9:19 -> 9:15
            base_minute = (now.minute // 15) * 15
            base_time = now.replace(minute=base_minute, second=0, microsecond=0)

            # --- CÀI ĐẶT THỜI GIAN DELAY THEO TỔNG LỆNH (Cộng từ mốc chuẩn) ---
            if min_sum > 30:
                resume_auto_open_time = base_time + timedelta(hours=2)
                delay_msg = "2 tiếng"
            elif min_sum > 20:
                resume_auto_open_time = base_time + timedelta(hours=1)
                delay_msg = "1 tiếng"
            else: # Từ 10 đến 20 lệnh
                resume_auto_open_time = base_time + timedelta(minutes=30)
                delay_msg = "30 phút"

                
            #log(f"💤 Tổng={min_sum} -> Bot sẽ ngủ đông Auto Open {delay_msg} và hoạt động lại lúc {resume_auto_open_time.strftime('%H:%M:%S')}.")
            log_auto_open(f"🛑 Tổng lệnh đã là {min_sum} -> Bot ngủ đông {delay_msg} (hoạt động lại lúc {resume_auto_open_time.strftime('%H:%M:%S')}).")
        else:
            log(f"⚠️ OKX_{best_acc_idx} | Không tìm thấy token thỏa điều kiện so với mốc {ref_token}.")

# === KHỞI TẠO DỮ LIỆU BAN ĐẦU (CACHE WARMING) ===
def preload_all_account_data():
    log("🔄 Đang tải dữ liệu khởi tạo cho tất cả tài khoản (Cache Warming)...")
    for i, acc in enumerate(accounts):
        try:
            # Ép lấy fresh data và lưu vào position_cache
            fetch_fresh_data(acc, i)
            time.sleep(1)  # Nghỉ nửa giây giữa mỗi tài khoản để tránh bị OKX block IP (Rate Limit)
        except Exception as e:
            log(f"⚠️ Lỗi khởi tạo data OKX_{i}: {e}")
    log("✅ Hoàn tất tải dữ liệu toàn bộ hệ thống! Bot đã sẵn sàng chạy lịch trình.")

# === SCHEDULER ===
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)
        
def run_sl_op():
    for idx, acc in enumerate(accounts):
        process_account_sl_op(idx, acc)


# === HÀM KIỂM TRA BALANCE 18H ===
def check_daily_18h_job():
    global last_daily_check_date, dca_target_offset, time_open, time_set, previous_balances_18h
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    now = datetime.now(tz)

    # Chạy duy nhất vào đúng 18:00
    if now.hour == 18 and now.minute == 0:
        current_date = now.date()
        if last_daily_check_date != current_date:
            last_daily_check_date = current_date
            log("⏳ Bắt đầu đối chiếu Balance 18h hàng ngày...")

            current_balances = {}
            for i, acc in enumerate(accounts):
                # Ép lấy fresh balance
                bal, _, _, _ = get_cached_or_fresh(acc, i, force=True)
                current_balances[i] = bal

            # Lần chạy đầu tiên chưa có lịch sử, chỉ lưu lại gốc
            if not previous_balances_18h:
                previous_balances_18h = current_balances
                save_normalized_config()
                log("✅ Chạy 18h lần đầu: Đã lưu balance làm mốc so sánh cho ngày mai.")
                return

            lower_count = 0
            for i in range(11):
                old_bal = previous_balances_18h.get(i, 0)
                cur_bal = current_balances.get(i, 0)

                # Nếu bị sụt balance
                if cur_bal < old_bal:
                    lower_count += 1
                    # Tăng vòng xoay phút cho time_open (Xoay từ 59 về 0)
                    if i in time_open:
                        time_open[i] = sorted([(x + 1) % 60 for x in time_open[i]])
                    # Tăng vòng xoay phút cho time_set (Xoay từ 59 về 0)
                    if i in time_set:
                        time_set[i] = sorted([(x + 1) % 60 for x in time_set[i]])

                    log(f"🔻 OKX_{i}: Sụt giảm (mốc mới {cur_bal:.2f} < mốc cũ {old_bal:.2f}) -> Đã dịch time_open & time_set lên 1 nhịp.")
                else:
                    # Nếu mốc mới lớn hơn hoặc bằng mốc cũ
                    log(f"🟢 OKX_{i}: Không thay đổi do mốc mới ({cur_bal:.2f}) >= mốc cũ ({old_bal:.2f}).")

            # Kiểm tra số lượng tài khoản (vị thế account) bị sụt giảm
            if lower_count >= 6:
                old_offset = dca_target_offset
                # Lùi xuống 1 mức (offset 2 -> 1 -> 0 -> quay về 2)
                dca_target_offset = (dca_target_offset - 1) % 3
                log(f"📉 Có {lower_count}/11 tài khoản giảm balance -> Dịch lùi Target DCA từ mốc {old_offset} xuống {dca_target_offset}.")
            else:
                log(f"📊 Có {lower_count}/11 tài khoản giảm balance (Chưa đủ >=6 để dịch Target DCA).")

            # Ghi đè balance mới để hôm sau so sánh tiếp
            previous_balances_18h = current_balances
            save_normalized_config()


schedule.every().minute.at(":00").do(run_sl_op)
schedule.every().minute.at(":00").do(run_dca_check)
schedule.every().minute.at(":05").do(auto_open_positions_job) # Khởi chạy hàm mở auto sau giây 05 để tránh nghẽn API
schedule.every(6).minutes.at(":00").do(check_and_flip_dca)
schedule.every().minute.at(":00").do(check_daily_18h_job)  # Thêm Task check 18h

# --- THÊM LỆNH GỌI HÀM VÀO ĐÂY ---
preload_all_account_data()
# ---------------------------------

threading.Thread(target=run_scheduler, daemon=True).start()

# === WEB ===

# API Kiểm tra trước khi lưu (Preview)
@app.route('/preview_tokens', methods=['POST'])
def preview_tokens():
    try:
        data = request.get_json(silent=True) or {}
        acc_idx = int(data.get('accIndex', -1))
        token_data_str = data.get('tokenData', '').strip()

        if acc_idx == -1 or not token_data_str:
            return jsonify({"success": False, "error": "Thiếu dữ liệu (Tài khoản hoặc Token)."})

        dict_string = f"{{{token_data_str}}}"
        new_tokens = ast.literal_eval(dict_string)
        
        if not isinstance(new_tokens, dict):
            return jsonify({"success": False, "error": "Định dạng dữ liệu không phải Dictionary."})

        # Lấy dữ liệu cũ trong RAM
        current_amounts = {}
        for key, val in token_amounts_map.get(acc_idx, {}).items():
            if isinstance(key, str):
                current_amounts[key] = val
            elif isinstance(key, tuple):
                for t in key:
                    current_amounts[t] = val

        # Lấy exchange từ cache để tính ra giá USDT hiện tại
        account = accounts[acc_idx]
        _, _, _, exchange = get_cached_or_fresh(account, acc_idx, force=False)

        changes = []
        for key, val in new_tokens.items():
            if isinstance(key, str):
                tokens = [key]
            elif isinstance(key, tuple):
                tokens = list(key)
            else:
                continue

            for t in tokens:
                old_val = current_amounts.get(t, None)
                symbol = f"{t}/USDT:USDT"
                
                old_str_display = ""
                new_str_display = ""

                # Truy xuất giá trị USDT nếu lấy được Exchange
                if exchange:
                    try:
                        exchange.load_markets() # Load thông tin contract size từ cache
                        market_info = exchange.market(symbol)
                        contract_size = float(market_info.get('contractSize', 1))
                        
                        # Gọi api lấy giá market mới nhất
                        ticker = exchange.fetch_ticker(symbol)
                        last_price = float(ticker['last'])
                        
                        if old_val is not None and float(old_val) > 0:
                            old_usdt = round(float(old_val) * contract_size * last_price, 2)
                            old_str_display = f" - ({old_usdt} USDT)"
                            
                        if float(val) > 0:
                            new_usdt = round(float(val) * contract_size * last_price, 2)
                            new_str_display = f" - ({new_usdt} USDT)"
                    except Exception as e:
                        log(f"Lỗi tính giá USDT cho preview {symbol}: {e}")

                # Nạp vào list trả về cho Frontend
                changes.append({
                    "token": t,
                    "old": old_val,
                    "new": val,
                    "old_display": f"{old_val}{old_str_display}" if old_val is not None else None,
                    "new_display": f"{val}{new_str_display}" if val != 0 else 0
                })

        return jsonify({"success": True, "changes": changes})

    except SyntaxError:
        return jsonify({"success": False, "error": "Lỗi cú pháp. Hãy chắc chắn có dấu phẩy ở cuối: ('LINK',): 0.4,"})
    except ValueError:
        return jsonify({"success": False, "error": "Lỗi giá trị nhập vào."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# === API ROUTE ĐỂ NHẬN DỮ LIỆU CẬP NHẬT TỪ GIAO DIỆN ===
@app.route('/update_tokens', methods=['POST'])
def update_tokens():
    try:
        if request.is_json:
            data = request.get_json(silent=True)
        else:
            data = request.form.to_dict()
            if not data and request.data:
                data = json.loads(request.data.decode('utf-8'))

        if not data:
            return jsonify({"success": False, "error": "Máy chủ không nhận được dữ liệu (Payload rỗng)."})

        acc_idx = int(data.get('accIndex', -1))
        token_data_str = data.get('tokenData', '').strip()

        if acc_idx == -1 or not token_data_str:
            return jsonify({"success": False, "error": "Dữ liệu gửi lên bị thiếu Tài khoản hoặc Token."})

        dict_string = f"{{{token_data_str}}}"
        new_tokens = ast.literal_eval(dict_string)
        
        if isinstance(new_tokens, dict):
            # Cập nhật dữ liệu vào bộ nhớ (RAM)
            token_amounts_map[acc_idx].update(new_tokens)
            
            # CHUẨN HÓA LẠI THEO HÀM SORT & XÓA TRÙNG RỒI MỚI GHI FILE
            save_normalized_config()
                
            log(f"WEB UPDATE & SAVED | OKX_{acc_idx} received new tokens: {new_tokens}")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Sai định dạng, vui lòng kiểm tra lại cấu trúc."})

    except SyntaxError:
        return jsonify({"success": False, "error": "Lỗi cú pháp (thiếu dấu phẩy, ngoặc). Định dạng chuẩn: ('LINK',): 0.4,"})
    except ValueError:
         return jsonify({"success": False, "error": "Lỗi giá trị (Ví dụ: Số lượng không hợp lệ)."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# === WEB ROUTES ===
@app.route('/')
def index():
    current_name = accounts[current_account_index]['name']

    sorted_token_amounts = []
    for i in range(11):
        sorted_token_amounts.append(get_sorted_unique_token_amounts(i))

    # GỌI HÀM LẤY DATA THỤ ĐỘNG (Không gọi lại API sàn)
    total_balance_cached, total_margin_cached, passive_logs = generate_passive_stats()

    # --- THÊM DÒNG NÀY: Tính toán lại tổng want động mỗi khi tải trang ---
    dynamic_total_want = sum(acc['balance_want'] for acc in accounts)

    return render_template_string(
        HTML_TEMPLATE,
        dca_results=dca_results,
        dca=dca,
        current_account_name=current_name,
        dca_change_history=dca_change_history,
        total_balance_want=dynamic_total_want,  # <-- Đổi biến truyền vào ở đây
        accounts=accounts,  
        sorted_token_amounts=sorted_token_amounts,
        total_balance_cached=total_balance_cached,
        total_margin_cached=total_margin_cached,
        passive_logs=passive_logs,
        auto_open_history=auto_open_history   # <--- Thêm dòng này vào cuối cùng

    )

if __name__ == '__main__':
    log("Starting Flask Web Server on Port 5008...")
    # app.run(port=5008, debug=False)
    # === BẮT ĐẦU ĐOẠN TÍCH HỢP NGROK ===
    # try:
    #     # 1. Điền Authtoken bạn vừa lấy trên trang chủ Ngrok vào đây
    #     ngrok.set_auth_token("3FUZZcZswVx3SSYu0f7nnybqUpe_4jbcD61u7b5zaKPC8e4NQ")
        
    #     # 2. Tạo đường hầm (tunnel) trỏ vào đúng port 5008 của Flask
    #     public_url = ngrok.connect(5008)
        
    #     # 3. In link ra màn hình điện thoại để bạn thấy
    #     log(f"🌍 NGROK PUBLIC URL: {public_url.public_url}")
    #     print("\n" + "="*50)
    #     print(f"🚀 TRUY CẬP TRÊN MÁY TÍNH BẰNG LINK NÀY: {public_url.public_url}")
    #     print("="*50 + "\n")
    # except Exception as e:
    #     log(f"❌ Lỗi khởi chạy Ngrok: {e}")
    # === KẾT THÚC ĐOẠN TÍCH HỢP NGROK ===

    # Đổi tham số host thành '0.0.0.0' để Flask chấp nhận kết nối từ bên ngoài localhost
    app.run(host='0.0.0.0', port=5008, debug=False)
