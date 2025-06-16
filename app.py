import os
import hmac
import json
import time
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment Variables
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_BASE_URL = "https://www.okx.com"

# Gửi tin nhắn Telegram
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        resp = requests.post(url, json=data)
        print("[TELEGRAM]", resp.status_code, "-", resp.text)
    except Exception as e:
        print("Telegram error:", e)

# Ký dữ liệu theo chuẩn OKX
def sign(message, secret_key):
    return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

# Đặt lệnh trên OKX
def place_order(symbol, side, usdt_amount):
    # Lấy giá hiện tại
    resp = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}")
    try:
        data = resp.json()
        last_price = float(data["data"][0]["last"])
    except Exception as e:
        send_telegram_message(f"❌ Lỗi đọc giá ticker: HTTP {resp.status_code}, nội dung: {resp.text[:200]}")
        raise RuntimeError("Không lấy được giá từ OKX.")

    # Tính khối lượng với đòn bẩy 20x
    qty = round(usdt_amount / last_price * 20, 6)
    tp_price = round(last_price * 1.01, 2)   # trailing TP 1%
    sl_price = round(last_price * 0.985, 2)  # SL 1.5%

    side_type = "buy" if side.lower() == "buy" else "sell"
    pos_side = "long" if side_type == "buy" else "short"
    trade_mode = "isolated"
    ord_type = "market"

    # Tạo chữ ký
    timestamp = str(time.time())
    path = "/api/v5/trade/order"
    body_json = {
        "instId": symbol,
        "tdMode": trade_mode,
        "side": side_type,
        "ordType": ord_type,
        "sz": str(qty),
        "posSide": pos_side,
        # "slTriggerPx": str(sl_price),
        # "tpTriggerPx": str(tp_price),
        # trailing TP/SL không được hỗ trợ trực tiếp => xử lý riêng sau nếu muốn nâng cấp
    }
    body = json.dumps(body_json)
    message = timestamp + "POST" + path + body
    signature = sign(message, OKX_API_SECRET)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
        "x-simulated-trading": "1",
    }

    order_resp = requests.post(OKX_BASE_URL + path, headers=headers, data=body)
    try:
        result = order_resp.json()
    except Exception:
        send_telegram_message(f"❌ Lỗi JSON khi đặt lệnh: HTTP {order_resp.status_code}, nội dung: {order_resp.text[:200]}")
        raise RuntimeError("Lệnh market lỗi.")

    return result

# Đầu vào từ webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("[WEBHOOK]", data)
    symbol = data.get("symbol")
    side = data.get("side")
    qty = float(data.get("qty"))

    try:
        result = place_order(symbol, side, qty)
        send_telegram_message(f"📈 Đã gửi lệnh DEMO: {side.upper()} {symbol} - {qty} USDT")
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        send_telegram_message(f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {qty} USDT\nChi tiết: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Trang chủ test
@app.route("/", methods=["GET"])
def home():
    return "✅ Webhook OK!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
