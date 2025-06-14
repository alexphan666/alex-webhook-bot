import os
from flask import Flask, request
import hmac
import hashlib
import json
import requests
import time

# ---------------------------
# 1. Load biến môi trường DEMO
# ---------------------------
OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

app = Flask(__name__)

# ---------------------------
# 2. Gửi tin nhắn về Telegram
# ---------------------------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# ---------------------------
# 3. Gửi lệnh thị trường vào OKX DEMO
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
# 4. Tạo chữ ký OKX
# ---------------------------
def generate_signature(timestamp, method, request_path, body):
    message = timestamp + method + request_path + body
    return hmac.new(
        bytes(OKX_API_SECRET, 'utf-8'),
        bytes(message, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

# ---------------------------
# 5. Nhận tín hiệu từ TradingView
# ---------------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    
    if data is None:
        return 'No data received', 400

    # Lấy thông tin từ TradingView
    signal = data.get("signal")
    coin = data.get("coin")  # BTC, AAVE, BCH

    # Gửi tin nhắn về Telegram
    send_telegram_message(f"[DEMO] Tín hiệu nhận được: {signal.upper()} - {coin.upper()}")

    # Xác định mã giao dịch trên OKX
    symbol_map = {
        "BTC": "BTC-USDT",
        "AAVE": "AAVE-USDT",
        "BCH": "BCH-USDT"
    }

    symbol = symbol_map.get(coin.upper(), None)
    if not symbol:
        return "Symbol not supported", 400

    # Khối lượng mỗi lệnh DEMO (có thể chỉnh sửa tuỳ ý)
    amount = "10"  # 10 USDT

    if signal.lower() == "buy":
        order_response = place_order(symbol, "buy", amount)
    elif signal.lower() == "sell":
        order_response = place_order(symbol, "sell", amount)
    else:
	return "Unknown signal", 400

    return f"Order placed: {order_response}", 200

# ---------------------------
# 6. Run local (chỉ khi test)
# ---------------------------
if __name__ == '__main__':
    app.run(debug=True)