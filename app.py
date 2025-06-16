import os
import time
import hmac
import hashlib
import base64
import json
import requests
from flask import Flask, request, jsonify
import telegram
from telegram.request import HTTPXRequest  # DÙNG CHO BẢN ĐỒNG BỘ

# Load biến môi trường
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
PASSPHRASE = os.getenv("OKX_PASSPHRASE")

# In ra để debug trên Render logs
print("DEBUG TELEGRAM_TOKEN:", TELEGRAM_TOKEN)
print("DEBUG TELEGRAM_CHAT_ID:", CHAT_ID)

# Khởi tạo Telegram bot (sync)
bot = telegram.Bot(token=TELEGRAM_TOKEN, request=HTTPXRequest())

app = Flask(__name__)

# OKX base URL demo
BASE_URL = "https://www.okx.com"

# Ký request
def sign_request(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# Gửi tin nhắn Telegram
def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Lỗi khi gửi Telegram:", e)

# Đặt lệnh OKX demo
def place_order(symbol, side, usdt_amount):
    try:
        timestamp = str(int(time.time() * 1000))
        leverage = 20

        # Lấy giá thị trường hiện tại
        ticker = requests.get(f"{BASE_URL}/api/v5/market/ticker?instId={symbol}").json()
        price = float(ticker["data"][0]["last"])

        # Tính số lượng coin
        coin_qty = round(usdt_amount / price, 4)

        body_dict = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": side,
            "ordType": "market",
            "sz": str(coin_qty),
            "posSide": "long" if side == "buy" else "short",
            "clOrdId": f"alex_{int(time.time())}"
        }

        body = json.dumps(body_dict)

        signature = sign_request(timestamp, "POST", "/api/v5/trade/order", body, API_SECRET)
        headers = {
            "OK-ACCESS-KEY": API_KEY,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": PASSPHRASE,
            "Content-Type": "application/json"
        }

        # Đặt lệnh thị trường
        response = requests.post(f"{BASE_URL}/api/v5/trade/order", headers=headers, data=body)
        res_json = response.json()
        print("OKX response:", res_json)

        if res_json.get("code") == "0":
            send_telegram_message(f"✅ Đã đặt lệnh demo {side.upper()} {symbol} với {usdt_amount} USDT")
        else:
            send_telegram_message(f"❌ Lỗi đặt lệnh: {res_json.get('msg', 'Không rõ lỗi')}")
    except Exception as e:
        send_telegram_message(f"❌ Lỗi khi đặt lệnh: {str(e)}")

# Route webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received Webhook:", data)

    symbol = data.get("symbol")
    side = data.get("side")
    qty = float(data.get("qty", 0))

    if not all([symbol, side, qty]):
        return jsonify({"error": "Thiếu thông tin"}), 400

    send_telegram_message(f"📈 Đã nhận tín hiệu: {side.upper()} {symbol} - {qty} USDT")
    place_order(symbol, side, qty)

    return jsonify({"message": "Đã nhận tín hiệu"}), 200

# Home route test
@app.route("/")
def home():
    return "Alex Webhook Bot is running!"
