import os
import json
import telegram
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- Lấy thông tin từ Biến Môi Trường (An toàn hơn) ---
# Thay vì hardcode, ta sẽ đọc từ Environment Variables trên server
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GOOGLE_SHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME')
WORKSHEET_NAME = "vol_t7" # Bạn có thể để cố định hoặc cũng đưa vào biến môi trường

# --- Thông tin cấu hình khác ---
TEAM_MEMBERS = ["Khoa Dao", "Hung Luu", "Thao Vy", "Thành Viên 4", "Thành Viên 5"]
USER_ID_TO_MEMBER_MAP = {
    7626921008: "Khoa Dao", 515315411: "Hung Luu",
    5939326062: "Thao Vy", 444555666: "Thành Viên 4", 777888999: "Thành Viên 5",
}

# --- Thiết lập Flask và Bot ---
app = Flask(__name__)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Bỏ 'import json' nếu có, không cần nữa
# import os cũng không cần cho hàm này

def get_worksheet():
    """Hàm kết nối và lấy worksheet - Đọc từ Secret File."""
    # Render sẽ đặt Secret File của bạn tại đường dẫn này
    # Hàm này sẽ tìm file credentials.json mà bạn đã tạo ở Bước A
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json',
        ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    )
    client = gspread.authorize(creds)
    
    # Lấy GOOGLE_SHEET_NAME từ biến môi trường
    sheet_name = os.environ.get('GOOGLE_SHEET_NAME')
    spreadsheet = client.open(sheet_name)
    
    return spreadsheet.worksheet(WORKSHEET_NAME)

# --- Endpoint chính để nhận Webhook từ Telegram ---
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    if request.is_json:
        update_data = request.get_json()
        update = telegram.Update.de_json(update_data, bot)
        
        # Xử lý tin nhắn
        process_message(update.message)

    return 'OK', 200

def process_message(msg):
    """Hàm xử lý logic chính của bot (tách ra từ vòng lặp cũ)."""
    if not msg or not msg.text:
        return

    user_id = msg.from_user.id
    message_text = msg.text.strip().lower()

    if user_id not in USER_ID_TO_MEMBER_MAP:
        return

    worksheet = get_worksheet()
    
    # Logic xử lý /vol và /user tương tự như trước
    if message_text.startswith('/vol '):
        try:
            cumulative_vol_today = float(message_text[5:])
            current_day = datetime.now().day
            target_row = current_day + 2
            member_name = USER_ID_TO_MEMBER_MAP[user_id]
            member_index = TEAM_MEMBERS.index(member_name)
            cumulative_col = 2 + (member_index * 4)

            worksheet.update_cell(target_row, cumulative_col, cumulative_vol_today)
            bot.send_message(chat_id=msg.chat_id, text=f"✅ Đã ghi nhận vol lũy tiến {cumulative_vol_today} cho {member_name}.")
        except Exception as e:
            bot.send_message(chat_id=msg.chat_id, text=f"Lỗi khi xử lý /vol: {e}")

    elif message_text.startswith('/user '):
        # Tương tự cho lệnh /user...
        pass

# Route để kiểm tra xem bot có đang chạy không
@app.route('/')
def index():
    return 'Bot is running!'