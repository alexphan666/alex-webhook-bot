import os
import time
import base64
import hmac
import hashlib
import json
import requests
from flask import Flask, request

app = Flask(__name__)

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trạng thái mỗi coin
coin_state = {
    "AAVE-USDT": {"active": False, "level": 1, "entry_price": None},
    "BTC-USDT": {"active": False, "level": 1, "entry_price": None},
    "BCH-USDT": {"active": False, "level": 1, "entry_price": None},
}

# Gửi thông báo Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("[TELEGRAM ERROR]", e)

# Ký signature cho OKX
def generate_signature(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# Gửi lệnh lên OKX DEMO
def place_order(symbol, side, amount):
    try:
        base_url = "https://www.okx.com"  # OKX Demo cũng dùng URL này
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
            os.getenv("OKX_DEMO_API_SECRET")
        )

        headers = {
            "OK-ACCESS-KEY": os.getenv("OKX_DEMO_API_KEY"),
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": os.getenv("OKX_DEMO_API_PASSPHRASE"),
            "Content-Type": "application/json"
        }

        response = requests.post(base_url + endpoint, headers=headers, data=body_json)
        print("[OKX DEMO ORDER]", response.status_code, response.text)

        return response.json()
    except Exception as e:
        send_telegram_message(f"❌ Lỗi gửi lệnh OKX DEMO: {str(e)}")
        return {"error": str(e)}

# Route webhook từ TradingView
@app.route('/webhook-demo', methods=['POST'])
def webhook_demo():
    data = request.get_json()
    print("[WEBHOOK DEMO]", data)

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

    # Xác định số tiền theo bậc
    level = coin_state[symbol]["level"]
    amount = {
        1: 200,
        2: 350,
        3: 500
    }.get(level, 200)

    # Buy / Sell
    side = signal.lower()
    if side not in ["buy", "sell"]:
        send_telegram_message(f"❌ Tín hiệu không hợp lệ: {signal}")
        return "Invalid signal", 400

    # Gửi lệnh demo
    order_response = place_order(symbol, side, amount)

    # Kiểm tra phản hồi
    if "error" in order_response or order_response.get("code") != "0":
        send_telegram_message(f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {amount} USDT\nChi tiết: {order_response}")
        return "Order failed", 500

    # Cập nhật trạng thái
    coin_state[symbol]["active"] = True

    coin_state[symbol]["entry_price"] = 9999  # placeholder

    send_telegram_message(f"✅ ĐÃ GỬI LỆNH DEMO: <b>{side.upper()}</b> {symbol} - {amount} USDT")
    print("[DEMO ORDER SUCCESS]", order_response)
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)