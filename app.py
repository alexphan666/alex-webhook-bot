from flask import Flask, request, jsonify
import os
import requests
import time
import base64
import hmac
import hashlib
import json
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

app = Flask(__name__)

# === BIẾN MÔI TRƯỜNG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")
OKX_BASE_URL = "https://www.okx.com"

# === GỬI TIN NHẮN TELEGRAM ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print("[TELEGRAM]", response.status_code, "-", response.text)
    except Exception as e:
        print("[TELEGRAM ERROR]", str(e))

# === HÀM TẠO CHỮ KÝ OKX ===
def create_okx_headers(method, path, body=""):
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
    prehash = f"{timestamp}{method}{path}{body}"
    signature = base64.b64encode(
        hmac.new(OKX_API_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()
    return {
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
        "Content-Type": "application/json",
        "x-simulated-trading": "1"  # ⚠️ Bắt buộc với tài khoản demo
    }

# === CHUYỂN JSON SANG CHUỖI ===
def json_string(data):
    return json.dumps(data, separators=(',', ':'))

# === HÀM ĐẶT LỆNH GIAO DỊCH ===
def place_order(symbol, side, qty):
    try:
        # 1. Lấy giá thị trường
        res = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}")
        data = res.json()
        mark_price = float(data['data'][0]['last'])

        # 2. Tính số lượng coin
        notional = float(qty)
        leverage = 20
        base_qty = round(notional / mark_price * leverage, 4)

        # 3. Gửi lệnh thị trường
        path = "/api/v5/trade/order"
        url = f"{OKX_BASE_URL}{path}"
        direction = "buy" if side.lower() == "buy" else "sell"

        order_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": direction,
            "ordType": "market",
            "sz": str(base_qty)
        }
        order_body = json_string(order_data)
        headers = create_okx_headers("POST", path, body=order_body)
        order_res = requests.post(url, headers=headers, data=order_body).json()
        print("[ORDER RESULT]", order_res)

        if order_res.get("code") != "0":
            raise Exception(order_res.get("msg", "Đặt lệnh thất bại"))

        # 4. Tính TP & SL
        if side.lower() == "buy":
            tp_price = round(mark_price * 1.01, 2)
            sl_price = round(mark_price * 0.985, 2)
            pos_side = "long"
            opp_side = "sell"
        else:
            tp_price = round(mark_price * 0.99, 2)
            sl_price = round(mark_price * 1.015, 2)
            pos_side = "short"
            opp_side = "buy"

        # 5. Đặt TP trailing stop
        tp_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": opp_side,
            "ordType": "move_order_stop",
            "posSide": pos_side,
            "sz": str(base_qty),
            "trailAmt": str(round(mark_price * 0.01, 2))
        }
        tp_body = json_string(tp_data)
        headers_tp = create_okx_headers("POST", path, body=tp_body)
        requests.post(url, headers=headers_tp, data=tp_body)

        # 6. Đặt SL cố định
        sl_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": opp_side,
            "ordType": "trigger",
            "triggerPx": str(sl_price),
            "posSide": pos_side,
            "sz": str(base_qty)
        }
        sl_body = json_string(sl_data)
        headers_sl = create_okx_headers("POST", path, body=sl_body)
        requests.post(url, headers=headers_sl, data=sl_body)

        return f"✅ Đã vào lệnh {side.upper()} {symbol} {qty} USDT\nGiá: {mark_price}\nTP trailing 1%\nSL cố định: {sl_price}"

    except Exception as e:
        return f"❌ Lỗi khi đặt lệnh: {str(e)}"

# === TRANG CHỦ ===
@app.route("/")
def home():
    return "✅ OK - Webhook bot is running!"

# === WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("[WEBHOOK]", data)

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        send_telegram_message(f"📈 Đã nhận tín hiệu: {side.upper()} {symbol} - {qty} USDT")

        result = place_order(symbol, side, qty)

        send_telegram_message(result)

        return jsonify({"status": "ok", "message": result}), 200
    except Exception as e:
        send_telegram_message(f"❌ Lỗi webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# === CHẠY LOCAL ===
if __name__ == "__main__":
    app.run(debug=True, port=8000)
