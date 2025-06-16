from flask import Flask, request, jsonify
import os
import requests
import time
import hmac
import hashlib
from dotenv import load_dotenv

# Load biến môi trường từ Render hoặc file .env
load_dotenv()

app = Flask(__name__)

# === LẤY BIẾN MÔI TRƯỜNG ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_API_SECRET = os.getenv("OKX_API_SECRET_DEMO")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE_DEMO")

OKX_BASE_URL = "https://www.okx.com"
LEVERAGE = 20

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
def sign(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    return hmac.new(
        OKX_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# === HÀM ĐẶT LỆNH TRÊN OKX DEMO ===
def place_order(symbol, side, qty):
    try:
        # Lấy giá hiện tại
        ticker_resp = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}")
        price_data = ticker_resp.json()
        mark_price = float(price_data['data'][0]['last'])

        # Tính TP và SL
        if side.lower() == "buy":
            tp_price = round(mark_price * 1.01, 2)
            sl_price = round(mark_price * 0.985, 2)
            pos_side = "long"
        else:
            tp_price = round(mark_price * 0.99, 2)
            sl_price = round(mark_price * 1.015, 2)
            pos_side = "short"

        # Đặt lệnh thị trường
        order_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": side,
            "ordType": "market",
            "posSide": pos_side,
            "sz": str(qty),
            "lever": str(LEVERAGE)
        }

        # Ký & gửi lệnh
        timestamp = str(time.time())
        headers = {
            "OK-ACCESS-KEY": OKX_API_KEY,
            "OK-ACCESS-SIGN": sign(timestamp, "POST", "/api/v5/trade/order", json.dumps(order_data)),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
            "Content-Type": "application/json"
        }

        order_resp = requests.post(
            f"{OKX_BASE_URL}/api/v5/trade/order",
            headers=headers,
            json=order_data
        )

        print("[OKX ORDER]", order_resp.status_code, order_resp.text)

        # Gửi TP/SL
        if order_resp.status_code == 200:
            time.sleep(1)  # delay để đợi lệnh khớp

            tp_sl_data = {
                "instId": symbol,
                "tdMode": "isolated",
                "posSide": pos_side,
                "ordType": "trigger",
                "side": "sell" if side == "buy" else "buy",
                "triggerPx": str(tp_price),
                "sz": str(qty),
                "orderPx": "-1"  # market order
            }
            # TP trailing order
            trailing_data = {
                "instId": symbol,
                "tdMode": "isolated",
                "side": "sell" if side == "buy" else "buy",
                "ordType": "move_order_stop",
                "posSide": pos_side,
                "sz": str(qty),
                "moveTriggerPx": str(tp_price),
                "orderPx": "-1"
            }

            sl_data = {
                "instId": symbol,
                "tdMode": "isolated",
                "side": "sell" if side == "buy" else "buy",
                "posSide": pos_side,
                "ordType": "trigger",
                "triggerPx": str(sl_price),
                "orderPx": "-1",
                "sz": str(qty)
            }

            for o in [trailing_data, sl_data]:
                r = requests.post(
                    f"{OKX_BASE_URL}/api/v5/trade/order",
                    headers=headers,
                    json=o
                )
                print("[OKX TP/SL]", r.status_code, r.text)

        return order_resp.json()
    except Exception as e:
        send_telegram_message(f"❌ Lỗi đặt lệnh: {str(e)}")
        return None

# === TRANG CHỦ KIỂM TRA ===
@app.route("/")
def home():
    return "✅ OK - Webhook bot is running!"

# === ROUTE NHẬN TÍN HIỆU WEBHOOK ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print("[WEBHOOK]", data)

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        send_telegram_message(f"📈 Tín hiệu nhận được: {side.upper()} {symbol} - Số lượng: {qty}")

        # Đặt lệnh OKX DEMO
        result = place_order(symbol, side, qty)
        send_telegram_message(f"✅ Lệnh đã gửi: {result}")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        send_telegram_message(f"❌ Lỗi xử lý tín hiệu: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# === CHẠY LOCAL (CHỈ DÙNG KHI TEST MÁY TÍNH) ===
if __name__ == "__main__":
    app.run(debug=True, port=8000)
