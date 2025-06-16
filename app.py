
import os
import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify
import telegram
from telegram.request import HTTPXRequest

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")

# Debug để kiểm tra biến môi trường
print("DEBUG TELEGRAM_TOKEN:", TELEGRAM_TOKEN)
print("DEBUG TELEGRAM_CHAT_ID:", CHAT_ID)

# Khởi tạo bot Telegram
bot = telegram.Bot(token=TELEGRAM_TOKEN, request=HTTPXRequest())

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Lỗi khi gửi Telegram:", e)

# Flask app
app = Flask(__name__)

# Hàm ký OKX request
def sign_request(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# Hàm đặt lệnh demo OKX
def place_order(symbol, side, usdt_amount):
    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = str(int(time.time() * 1000))

    order_data = {
        "instId": symbol,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": "",  # sẽ tính sau
        "posSide": "long" if side == "buy" else "short",
        "clOrdId": f"webhook-{timestamp}"
    }

    # Gọi API để lấy giá hiện tại
    ticker_resp = requests.get(f"https://www.okx.com/api/v5/market/ticker?instId={symbol}")
    price = float(ticker_resp.json()["data"][0]["last"])
    qty = round(usdt_amount / price, 4)
    order_data["sz"] = str(qty)

    body = json.dumps(order_data)
    signature = sign_request(timestamp, "POST", "/api/v5/trade/order", body, OKX_API_SECRET)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE,
        "x-simulated-trading": "1"
    }

    try:
        response = requests.post(url, headers=headers, json=order_data)
        resp_json = response.json()
        send_telegram_message(f"✅ Đặt lệnh {side.upper()} {symbol} thành công: {resp_json}")
    except Exception as e:
        send_telegram_message(f"❌ Lỗi khi đặt lệnh: {e}")

@app.route("/")
def index():
    return "Webhook OKX Bot"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("Received Webhook:", data)

        symbol = data["symbol"]
        side = data["side"]
        qty = float(data["qty"])

        send_telegram_message(f"📈 Đã nhận tín hiệu: {side.upper()} {symbol} - {qty} USDT")
        place_order(symbol, side, qty)

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        send_telegram_message(f"❌ Lỗi xử lý webhook: {e}")
        return jsonify({"error": str(e)}), 500

