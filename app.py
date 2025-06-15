import os
import time
import base64
import hmac
import hashlib
import json
import requests
from flask import Flask, request

app = Flask(__name__)

# Token Telegram và chat_id (nên để ở biến môi trường khi chạy thật)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trạng thái từng coin
coin_state = {
    "AAVE-USDT": {"active": False, "level": 1, "entry_price": None},
    "BTC-USDT": {"active": False, "level": 1, "entry_price": None},
    "BCH-USDT": {"active": False, "level": 1, "entry_price": None},
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    print("[TELEGRAM]", response.status_code, "-", response.text)

def generate_signature(timestamp, method, request_path, body, secret_key):
    message = f'{timestamp}{method}{request_path}{body}'
    mac = hmac.new(bytes(secret_key, encoding='utf-8'), bytes(message, encoding='utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

def place_order(symbol, side, amount):
    base_url = "https://www.okx.com"
    endpoint = "/api/v5/trade/order"

    symbol_map = {
        "BTC-USDT": "BTC-USDT-SWAP",
        "BCH-USDT": "BCH-USDT-SWAP",
        "AAVE-USDT": "AAVE-USDT-SWAP"
    }
    instId = symbol_map.get(symbol, symbol)

    timestamp = str(time.time())
    body = {
        "instId": instId,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": str(amount)
    }
    body_json = json.dumps(body)

    signature = generate_signature(
        timestamp,
        "POST",
        endpoint,
        body_json,
        os.getenv("OKX_API_SECRET")
    )

    headers = {
        "OK-ACCESS-KEY": os.getenv("OKX_API_KEY"),
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": os.getenv("OKX_API_PASSPHRASE"),
        "Content-Type": "application/json"
    }

    response = requests.post(base_url + endpoint, headers=headers, data=body_json)
    print("[OKX ORDER]", response.status_code, response.text)
    return response.json()

@app.route('/webhook-demo', methods=['POST'])
def webhook_demo():
    data = request.get_json()
    print("[WEBHOOK] Dữ liệu nhận được:", data)

    if not data:
        send_telegram_message("❌ Không nhận được JSON từ TradingView")
        return "No data", 400

    signal = data.get("signal")
    coin = data.get("coin") or data.get("symbol")

    if not signal or not coin:
        send_telegram_message("❌ Thiếu signal hoặc coin")
        return "Missing fields", 400

    symbol_map = {
        "BTC": "BTC-USDT",
        "AAVE": "AAVE-USDT",
        "BCH": "BCH-USDT"
    }
    symbol = symbol_map.get(coin.upper())
    if not symbol:
        send_telegram_message(f"⚠️ Coin không hỗ trợ: {coin}")
        return "Unsupported coin", 400

    # Tính số tiền theo bậc (level)
    level = coin_state[symbol]["level"]
    if level == 1:
        amount = 200
    elif level == 2:
        amount = 350
    elif level == 3:
        amount = 500
    else:
        amount = 200
    amount = str(amount)

    # Xác định hướng lệnh
    if signal.lower() == "buy":
        side = "buy"
    elif signal.lower() == "sell":
        side = "sell"
    else:
        send_telegram_message(f"❌ Tín hiệu không hợp lệ: {signal}")
        return "Invalid signal", 400

    order_response = place_order(symbol, side, amount)

    # Cập nhật trạng thái
    coin_state[symbol]["active"] = True
    coin_state[symbol]["entry_price"] = 9999  # Placeholder

    # Gửi thông báo rút gọn về Telegram
    send_telegram_message(f"✅ Đã gửi lệnh {side.upper()} {symbol} - {amount} USDT")

    # Ghi log phản hồi ra console để kiểm tra
    print("[ORDER RESPONSE]", order_response)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)