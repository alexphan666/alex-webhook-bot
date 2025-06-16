import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()  # Tải các biến môi trường từ .env (nếu dùng local)

app = Flask(__name__)

# Lấy biến môi trường DEMO từ Render
OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    print("[TELEGRAM]", response.status_code, "-", response.text)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("[WEBHOOK]", data)

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        if not all([symbol, side, qty]):
            raise ValueError("Thiếu thông tin trong payload.")

        if not OKX_API_KEY or not OKX_API_SECRET or not OKX_API_PASSPHRASE:
            raise ValueError("Missing OKX demo API credentials.")

        # Giả lập gửi lệnh (thay phần này bằng gọi API OKX thật nếu cần)
        print(f"Gửi lệnh DEMO: {symbol} - {side.upper()} {qty} USDT")

        # Gửi thông báo Telegram
        send_telegram_message(f"✅ Gửi lệnh DEMO thành công: {symbol} - {side.upper()} {qty} USDT")

        return {"status": "ok"}, 200

    except Exception as e:
        error_msg = f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {qty} USDT\nChi tiết: {str(e)}"
        send_telegram_message(error_msg)
        return {"error": str(e)}, 500

@app.route("/", methods=["GET"])
def index():
    return "✅ Webhook Bot đang chạy!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
