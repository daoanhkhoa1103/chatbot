import os
import json
import telegram
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==============================================================================
# PHẦN THIẾT LẬP - SẼ ĐỌC TỪ BIẾN MÔI TRƯỜNG TRÊN RENDER
# ==============================================================================
# Lấy thông tin nhạy cảm từ Biến Môi Trường (Environment Variables)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME')
CHAT_ID = os.environ.get('CHAT_ID') # CHAT_ID hiện tại chưa dùng trong webhook, nhưng có thể cần sau này

# Các thông tin cấu hình khác có thể đặt cố định hoặc đọc từ biến môi trường
WORKSHEET_NAME = "vol_t7" 
TEAM_MEMBERS = ["Khoa Dao", "Hung Luu", "Thao Vy", "Thành Viên 4", "Thành Viên 5"]

# Ánh xạ User ID của thành viên với tên
USER_ID_TO_MEMBER_MAP = {
    # Thay thế bằng User ID và tên thật của team bạn
    7626921008: "Khoa Dao",
    515315411: "Hung Luu",
    5939326062: "Thao Vy",
    444555666: "Thành Viên 4",
    777888999: "Thành Viên 5",
}

# ==============================================================================
# KHỞI TẠO ỨNG DỤNG
# ==============================================================================
app = Flask(__name__)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def get_worksheet():
    """Hàm kết nối và lấy worksheet - Sử dụng Secret File."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Render sẽ đặt Secret File tại đường dẫn '/etc/secrets/credentials.json'
    # nhưng gspread có thể tìm được nó chỉ bằng tên file.
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(GOOGLE_SHEET_NAME)
    return spreadsheet.worksheet(WORKSHEET_NAME)

def process_message(msg):
    """Hàm xử lý logic chính của bot."""
    if not msg or not msg.text:
        return

    user_id = msg.from_user.id
    message_text = msg.text.strip().lower()

    # Bỏ qua tin nhắn từ người không có trong danh sách
    if user_id not in USER_ID_TO_MEMBER_MAP:
        return

    try:
        worksheet = get_worksheet()
        current_day = datetime.now().day
        target_row = current_day + 2
        member_name = USER_ID_TO_MEMBER_MAP[user_id]
        member_index = TEAM_MEMBERS.index(member_name)

        # Xử lý lệnh báo cáo Volume
        if message_text.startswith('/vol '):
            volume_today = float(message_text[5:])
            cumulative_col = 2 + (member_index * 4) # Cột "Volume Lũy Tiến"
            worksheet.update_cell(target_row, cumulative_col, volume_today)
            bot.send_message(chat_id=msg.chat_id, text=f"✅ Đã ghi nhận vol lũy tiến {volume_today} cho {member_name}.")

        # Xử lý lệnh báo cáo User mới
        elif message_text.startswith('/user '):
            new_users = int(message_text[6:])
            user_col = 4 + (member_index * 4) # Cột "User Mới"
            worksheet.update_cell(target_row, user_col, new_users)
            bot.send_message(chat_id=msg.chat_id, text=f"✅ Đã ghi nhận {new_users} user mới cho {member_name}.")
            
    except Exception as e:
        print(f"Lỗi khi đang xử lý tin nhắn: {e}")
        bot.send_message(chat_id=msg.chat_id, text=f"Đã có lỗi xảy ra: {e}")

# ==============================================================================
# CÁC ROUTE CỦA WEBHOOK
# ==============================================================================
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Endpoint chính để nhận Webhook từ Telegram."""
    if request.is_json:
        update_data = request.get_json()
        update = telegram.Update.de_json(update_data, bot)
        process_message(update.message)
    return 'OK', 200

@app.route('/')
def index():
    """Route để kiểm tra sức khỏe của dịch vụ."""
    return 'Bot is running!'

# Dòng này không cần thiết cho Gunicorn trên Render nhưng hữu ích khi chạy cục bộ
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))