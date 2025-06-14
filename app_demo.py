import os
import hmac
import hashlib
import json
import time
import requests
from flask import Flask, request

# Khởi tạo Flask app
app = Flask(__name__)

# ---------------------------
# 1. Load biến môi trường DEMO
# ---------------------------
OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ---------------------------
# 2. Gửi tin nhắn về Telegram
# ---------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# ---------------------------
# 3. Tạo chữ ký OKX
# ---------------------------
def generate_signature(timestamp, method, request_path, body):
    message = timestamp + method + request_path + body
    return hmac.new(
        bytes(OKX_API_SECRET, 'utf-8'),
        bytes(message, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

# ---------------------------
# 4. Gửi lệnh thị trường vào OKX DEMO
# ---------------------------
def place_order(symbol, side, amount):
    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = str(time.time())

    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": generate_signature(timestamp, 'POST', '/api/v5/trade/order', ''),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    data = {
        "instId": symbol,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": amount
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

# ---------------------------
# 5. Nhận tín hiệu từ TradingView
# ---------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("Received payload:", data)  # debug

    if data is None:
        return 'No data received', 400

    signal = data.get("signal")
    coin = data.get("symbol")  # <== sửa từ "coin" sang "symbol"

    if not signal or not coin:
        return 'Missing signal or coin', 400

    # Gửi tin nhắn về Telegram
    send_telegram_message(f"[DEMO] Tín hiệu nhận được: {signal.upper()} - {coin.upper()}")

    # Map coin với instId trên OKX
    symbol_map = {
        "BTC": "BTC-USDT",
        "AAVE": "AAVE-USDT",
        "BCH": "BCH-USDT"
    }

    inst_id = symbol_map.get(coin.upper())
    if not inst_id:
        return "Symbol not supported", 400

    amount = "10"  # Khối lượng demo cố định

    if signal.lower() == "buy":
        order_response = place_order(inst_id, "buy", amount)
    elif signal.lower() == "sell":
        order_response = place_order(inst_id, "sell", amount)
    else:
        return "Unknown signal", 400

    return f"Order placed: {order_response}", 200

# ---------------------------
# 6. Chạy local khi test
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)