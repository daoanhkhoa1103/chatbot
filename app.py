import os
import json
import telegram
import asyncio
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==============================================================================
# PHẦN THIẾT LẬP (Giữ nguyên)
# ==============================================================================
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GOOGLE_SHEET_NAME = os.environ.get('GOOGLE_SHEET_NAME')

WORKSHEET_NAME = "vol_t7"
TEAM_MEMBERS = ["Khoa Dao", "Hung Luu", "Thao Vy"]
USER_ID_TO_MEMBER_MAP = {
    7626921008: "Khoa Dao", 515315411: "Hung Luu", 5939326062: "Thao Vy",
}

# ==============================================================================
# KHỞI TẠO ỨNG DỤNG
# ==============================================================================
app = Flask(__name__)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def get_worksheet():
    """Hàm kết nối và lấy worksheet - Sử dụng Secret File."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(GOOGLE_SHEET_NAME)
    return spreadsheet.worksheet(WORKSHEET_NAME)

# --- TÁI CẤU TRÚC LOGIC VÀO MỘT HÀM ASYNC DUY NHẤT ---
async def process_update_async(update):
    """Hàm bất đồng bộ xử lý toàn bộ logic cho một tin nhắn."""
    msg = update.message
    if not msg or not msg.text:
        return

    user_id = msg.from_user.id
    message_text = msg.text.strip().lower()

    if user_id not in USER_ID_TO_MEMBER_MAP:
        return

    try:
        # Tương tác với Google Sheet (hành động đồng bộ)
        worksheet = get_worksheet()
        current_day = datetime.now().day
        target_row = current_day + 2
        member_name = USER_ID_TO_MEMBER_MAP[user_id]
        member_index = TEAM_MEMBERS.index(member_name)

        reply_text = ""

        if message_text.startswith('/vol '):
            volume_today = float(message_text[5:])
            cumulative_col = 2 + (member_index * 4)
            worksheet.update_cell(target_row, cumulative_col, volume_today)
            reply_text = f"✅ Đã ghi nhận vol lũy tiến {volume_today} cho {member_name}."

        elif message_text.startswith('/user '):
            new_users = int(message_text[6:])
            user_col = 4 + (member_index * 4)
            worksheet.update_cell(target_row, user_col, new_users)
            reply_text = f"✅ Đã ghi nhận {new_users} user mới cho {member_name}."
        
        # Gửi tin nhắn trả lời (hành động bất đồng bộ)
        if reply_text:
            await bot.send_message(chat_id=msg.chat_id, text=reply_text)
            
    except Exception as e:
        print(f"Lỗi khi đang xử lý tin nhắn: {e}")
        # Gửi tin nhắn lỗi (hành động bất đồng bộ)
        await bot.send_message(chat_id=msg.chat_id, text=f"Đã có lỗi xảy ra khi xử lý lệnh của bạn.")

# ==============================================================================
# CÁC ROUTE CỦA WEBHOOK
# ==============================================================================
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Endpoint chính nhận Webhook và gọi hàm xử lý bất đồng bộ."""
    if request.is_json:
        update_data = request.get_json()
        update = telegram.Update.de_json(update_data, bot)
        # Chạy hàm async từ context đồng bộ của Flask
        asyncio.run(process_update_async(update))
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is running!'