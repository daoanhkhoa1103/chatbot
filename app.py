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

WORKSHEET_NAME = "Vol_T8"
TEAM_MEMBERS = ["KhoaDA", "VyDTT", "YenTTH", "PhatLH","QuyenTTS", "HungLD"]
USER_ID_TO_MEMBER_MAP = {
    7626921008: "KhoaDA", 5939326062: "VyDTT", 5050768441: "YenTTH", 5620934782: "PhatLH", 6885129892: "QuyenTTS", 515315411: "HungLD"
}

# ==============================================================================
# KHỞI TẠO ỨNG DỤNG
# ==============================================================================
app = Flask(__name__)
# KHÔNG KHỞI TẠO BOT Ở ĐÂY NỮA, CHÚNG TA SẼ TẠO SAU TRONG TỪNG YÊU CẦU

def get_worksheet():
    """Hàm kết nối và lấy worksheet - Sử dụng Secret File."""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(GOOGLE_SHEET_NAME)
    return spreadsheet.worksheet(WORKSHEET_NAME)

async def process_update_async(update):
    """Hàm bất đồng bộ xử lý toàn bộ logic cho một tin nhắn."""
    # TẠO MỘT ĐỐI TƯỢNG BOT MỚI SẠCH SẼ CHO YÊU CẦU NÀY
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    
    msg = update.message
    if not msg or not msg.text:
        return

    user_id = msg.from_user.id
    message_text = msg.text.strip().lower()

    if user_id not in USER_ID_TO_MEMBER_MAP:
        return

    try:
        worksheet = get_worksheet()
        current_day = datetime.now().day
        target_row = current_day + 2
        member_name = USER_ID_TO_MEMBER_MAP[user_id]
        member_index = TEAM_MEMBERS.index(member_name)

        # Định nghĩa các cột dựa trên cấu trúc mới: Mỗi thành viên chiếm 3 cột (User, Vol tổng, Vol ngày)
        # Base: KhoaDA bắt đầu từ cột 3 (C: User, D: Vol tổng, E: Vol ngày)
        user_col = 3 + (member_index * 3)
        vol_tong_col = 4 + (member_index * 3)
        vol_ngay_col = 5 + (member_index * 3)

        reply_text = ""

        if message_text.startswith('/vol '):
            vol_str = message_text[5:].strip().replace(',', '')  # Loại bỏ dấu phẩy để xử lý số có phân cách nghìn
            try:
                volume_tong = float(vol_str)
            except ValueError as ve:
                print(f"Lỗi giá trị input: {ve}")
                await bot.send_message(chat_id=msg.chat_id, text="❌ Lỗi: Vui lòng nhập số hợp lệ (ví dụ: /vol 100.5 hoặc /vol 1000, không dùng dấu cách trong số).")
                return  # Thoát sớm để tránh xử lý tiếp
            
            # Lấy vol tổng ngày hôm trước
            vol_tong_yesterday_str = worksheet.cell(target_row - 1, vol_tong_col).value or '0'
            vol_tong_yesterday_str = vol_tong_yesterday_str.replace(',', '')  # Đảm bảo loại dấu phẩy nếu có
            vol_tong_yesterday = float(vol_tong_yesterday_str if vol_tong_yesterday_str else 0)
            
            # Tính vol ngày
            vol_ngay = volume_tong - vol_tong_yesterday
            
            # Ghi vol tổng và vol ngày
            worksheet.update_cell(target_row, vol_tong_col, volume_tong)
            worksheet.update_cell(target_row, vol_ngay_col, vol_ngay)
            
            reply_text = f"✅ Đã ghi nhận vol tổng {volume_tong} cho {member_name}. Vol ngày: {vol_ngay}."

        elif message_text.startswith('/user '):
            user_str = message_text[6:].strip().replace(',', '')  # Tương tự, xử lý dấu phẩy cho /user
            try:
                users = int(user_str)
            except ValueError as ve:
                print(f"Lỗi giá trị input: {ve}")
                await bot.send_message(chat_id=msg.chat_id, text="❌ Lỗi: Vui lòng nhập số hợp lệ (ví dụ: /user 10).")
                return
            
            worksheet.update_cell(target_row, user_col, users)
            reply_text = f"✅ Đã ghi nhận {users} user cho {member_name}."
        
        if reply_text:
            await bot.send_message(chat_id=msg.chat_id, text=reply_text)
            
    except Exception as e:
        print(f"Lỗi khi đang xử lý tin nhắn: {e}")
        await bot.send_message(chat_id=msg.chat_id, text=f"Đã có lỗi xảy ra khi xử lý lệnh của bạn.")
    
    # Giải phóng tài nguyên bot sau khi xử lý xong
    await bot.shutdown()

# ==============================================================================
# CÁC ROUTE CỦA WEBHOOK
# ==============================================================================
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Endpoint chính nhận Webhook và gọi hàm xử lý bất đồng bộ."""
    if request.is_json:
        update_data = request.get_json()
        # Tạo một đối tượng bot tạm thời chỉ để phân tích cú pháp update
        temp_bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        update = telegram.Update.de_json(update_data, temp_bot)
        
        if update.message:
            asyncio.run(process_update_async(update))
            
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is running!'