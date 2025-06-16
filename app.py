from flask import Flask, request, jsonify
import os
import requests
from dotenv import load_dotenv

# Load biến môi trường từ Render hoặc file .env
load_dotenv()

app = Flask(__name__)

# === LẤY BIẾN MÔI TRƯỜNG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")

# === GỬI TIN NHẮN TELEGRAM ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print("[TELEGRAM]", response.status_code, "-", response.text)
    except Exception as e:
        print("[TELEGRAM ERROR]", str(e))

# === TRANG CHỦ KIỂM TRA ===
@app.route("/")
def home():
    return "✅ OK - Webhook bot is running!"

# === ROUTE NHẬN TÍN HIỆU WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("[WEBHOOK]", data)

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        # Gửi thông báo về Telegram
        send_telegram_message(f"📈 Tín hiệu nhận được: {side.upper()} {symbol} - Số lượng: {qty}")

        # Giả lập xử lý lệnh ở đây nếu cần

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        send_telegram_message(f"❌ Lỗi xử lý tín hiệu: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# === CHẠY LOCAL (CHỈ DÙNG KHI TEST MÁY TÍNH) ===
if __name__ == "__main__":
    app.run(debug=True, port=8000)
