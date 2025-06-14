from flask import Flask, request
import requests
import os

app = Flask(__name__)

# === Cấu hình từ biến môi trường ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

OKX_BASE_URL = "https://www.okx.com"  # hoặc demo nếu bạn dùng OKX demo

# === Hàm gửi tin nhắn Telegram ===
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Chưa có TELEGRAM_BOT_TOKEN hoặc CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print(f"[TELEGRAM] Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# === Giả lập gửi lệnh (chưa gọi API thật của OKX) ===
def place_order(symbol, side, amount):
    print(f"[DEMO ORDER] Gửi lệnh {side.upper()} {amount} USDT với {symbol}")
    return {"status": "success", "symbol": symbol, "side": side, "amount": amount}

@app.route('/')
def home():
    return "Alex Demo Bot is running!"

# === Webhook nhận tín hiệu từ TradingView ===
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    print("[DEBUG] Payload nhận từ TradingView:", data)

    if data is None:
        send_telegram_message("[ERROR] Không nhận được dữ liệu JSON từ TradingView")
        return 'No data received', 400

    signal = data.get("signal")
    coin = data.get("coin") or data.get("symbol")

    if not signal or not coin:
        send_telegram_message("[ERROR] Thiếu trường 'signal' hoặc 'coin/symbol' trong payload")
        return 'Missing signal or coin', 400

    send_telegram_message(f"[DEMO] Tín hiệu nhận được: {signal.upper()} - {coin.upper()}")

    symbol_map = {
        "BTC": "BTC-USDT",
        "AAVE": "AAVE-USDT",
        "BCH": "BCH-USDT"
    }

    symbol = symbol_map.get(coin.upper())
    if not symbol:
        send_telegram_message(f"[ERROR] Symbol không hỗ trợ: {coin.upper()}")
        return "Symbol not supported", 400

    amount = "10"

    if signal.lower() == "buy":
        order_response = place_order(symbol, "buy", amount)
    elif signal.lower() == "sell":
        order_response = place_order(symbol, "sell", amount)
    else:
        send_telegram_message(f"[ERROR] Tín hiệu không hợp lệ: {signal}")
        return "Unknown signal", 400

    send_telegram_message(f"[DEMO] Đã gửi lệnh: {signal.upper()} - {symbol} - {amount} USDT")
    return f"Order placed: {order_response}", 200

# === Chạy app Flask (local testing) ===
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # dùng port khác nếu 5000 bị trùng