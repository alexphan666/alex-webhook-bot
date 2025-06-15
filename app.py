from flask import Flask, request
import requests
import os
import json
import time
import hmac
import base64

app = Flask(__name__)

# === Cấu hình từ biến môi trường ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

OKX_BASE_URL = "https://www.okx.com"

# === Trạng thái từng coin ===
coin_state = {
    "BTC-USDT": {"level": 1, "entry_price": None, "active": False},
    "AAVE-USDT": {"level": 1, "entry_price": None, "active": False},
    "BCH-USDT": {"level": 1, "entry_price": None, "active": False},
}

# === Gửi tin nhắn Telegram ===
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Thiếu cấu hình token/chat_id")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        r = requests.post(url, json=payload)
        print(f"[TELEGRAM] Status: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# === Tạo chữ ký OKX ===
def generate_signature(timestamp, method, request_path, body, secret_key):
    message = f'{timestamp}{method}{request_path}{body}'
    mac = hmac.new(bytes(secret_key, encoding='utf-8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d).decode('utf-8')

# === Gửi lệnh demo lên OKX ===
def place_order(symbol, side, amount):
    print(f"[DEMO] Gửi lệnh {side.upper()} {amount} USDT với {symbol}")

    url = "/api/v5/trade/order"
    full_url = OKX_BASE_URL + url

    timestamp = str(time.time())
    method = "POST"
    body = {
        "instId": symbol,
        "tdMode": "cross",
        "side": side,
        "ordType": "market",
        "sz": amount,
        "posSide": "long" if side == "buy" else "short"
    }

    body_str = json.dumps(body)
    sign = generate_signature(timestamp, method, url, body_str, OKX_API_SECRET)

    headers = {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
        "Content-Type": "application/json",
        "x-simulated-trading": "1"  # Bật chế độ demo
    }

    try:
        response = requests.post(full_url, headers=headers, data=body_str)
        print("[OKX DEMO] Response:", response.text)
        return response.json()
    except Exception as e:
        print(f"[ERROR] Gửi lệnh thất bại: {e}")
        return {"error": str(e)}

@app.route('/')
def home():
    return "✅ Alex Demo Bot is running!"

@app.route('/ping')
def ping():
    return "xong", 200

@app.route("/test-telegram")
def test_telegram():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return "❌ Thiếu cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID", 400
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "✅ Bot Telegram hoạt động bình thường!"}
    try:
        r = requests.post(url, json=payload)
        return f"Status: {r.status_code} - {r.text}", 200
    except Exception as e:
        return f"Lỗi gửi Telegram: {str(e)}", 500

# === Webhook chính từ TradingView ===
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

    # Tính số tiền theo từng bậc
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

    # Xử lý lệnh mua/bán
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

    send_telegram_message(f"✅ Đã gửi lệnh {side.upper()} {symbol} - {amount} USDT\n\n📥 Phản hồi: {order_response}")
    return "OK", 200

# === Khởi chạy trên Render ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(debug=True, host='0.0.0.0', port=port)