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
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        res = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})
        print("[TELEGRAM]", res.status_code, "-", res.text)
    except Exception as e:
        print("[TELEGRAM ERROR]", str(e))

# === TẠO HEADER OKX ===
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
        "x-simulated-trading": "1"
    }

# === ĐẶT LỆNH GIAO DỊCH DEMO ===
def place_order(symbol, side, qty):
    try:
        # 1. Lấy giá thị trường
        r = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}")
        price_data = r.json()
        mark_price = float(price_data['data'][0]['last'])

        # 2. Tính khối lượng base theo đòn bẩy
        leverage = 20
        notional = float(qty)
        base_qty = round(notional / mark_price * leverage, 4)

        # 3. Đặt lệnh thị trường
        path = "/api/v5/trade/order"
        url = OKX_BASE_URL + path
        direction = "buy" if side.lower() == "buy" else "sell"

        order_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": direction,
            "ordType": "market",
            "sz": str(base_qty)
        }

        headers = create_okx_headers("POST", path, body=json.dumps(order_data, separators=(',', ':')))
        order_res = requests.post(url, headers=headers, json=order_data)

        print("[ORDER RAW]", order_res.status_code, order_res.text)

        try:
            order_json = order_res.json()
        except Exception:
            raise Exception("Không phân tích được phản hồi từ OKX")

        if order_json.get("code") != "0":
            raise Exception(order_json.get("msg", "Đặt lệnh thất bại"))

        # 4. Thiết lập TP/SL
        if side.lower() == "buy":
            tp_price = round(mark_price * 1.01, 2)
            sl_price = round(mark_price * 0.985, 2)
            pos_side, opp_side = "long", "sell"
        else:
            tp_price = round(mark_price * 0.99, 2)
            sl_price = round(mark_price * 1.015, 2)
            pos_side, opp_side = "short", "buy"

        # 5. Trailing TP
        tp_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": opp_side,
            "ordType": "move_order_stop",
            "posSide": pos_side,
            "sz": str(base_qty),
            "trailAmt": str(round(mark_price * 0.01, 2))
        }
        headers_tp = create_okx_headers("POST", path, body=json.dumps(tp_data, separators=(',', ':')))
        tp_res = requests.post(url, headers=headers_tp, json=tp_data)
        print("[TP RESPONSE]", tp_res.status_code, tp_res.text)

        # 6. SL cố định
        sl_data = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": opp_side,
            "ordType": "trigger",
            "triggerPx": str(sl_price),
            "posSide": pos_side,
            "sz": str(base_qty)
        }
        headers_sl = create_okx_headers("POST", path, body=json.dumps(sl_data, separators=(',', ':')))
        sl_res = requests.post(url, headers=headers_sl, json=sl_data)
        print("[SL RESPONSE]", sl_res.status_code, sl_res.text)

        return f"✅ Đã vào lệnh {side.upper()} {symbol} {qty} USDT\nGiá: {mark_price}\nTP trailing 1%\nSL: {sl_price}"
    
    except Exception as e:
        return f"❌ Lỗi khi đặt lệnh: {str(e)}"

# === HOME ===
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
