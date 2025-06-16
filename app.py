from flask import Flask, request, jsonify
import os
import requests
import hmac
import hashlib
import base64
import json
import time

app = Flask(__name__)

# Hàm tạo chữ ký OKX
def generate_okx_signature(timestamp, method, request_path, body, secret_key):
    message = f'{timestamp}{method}{request_path}{body}'
    mac = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# Hàm gửi lệnh demo lên OKX
def send_demo_order(symbol, side, usdt_amount):
    api_key = os.getenv("OKX_API_KEY_DEMO")
    api_secret = os.getenv("OKX_API_SECRET_DEMO")
    passphrase = os.getenv("OKX_API_PASSPHRASE_DEMO")

    if not all([api_key, api_secret, passphrase]):
        return {"error": "Missing OKX demo API credentials."}

    url = "https://www.okx.com/api/v5/trade/order"
    method = "POST"
    request_path = "/api/v5/trade/order"

    payload = {
        "instId": symbol,
        "tdMode": "cash",
        "side": side,
        "ordType": "market",
        "ccy": "USDT",
        "sz": str(usdt_amount)
    }
    body = json.dumps(payload)

    timestamp = str(time.time())
    signature = generate_okx_signature(timestamp, method, request_path, body, api_secret)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "x-simulated-trading": "1"
    }

    try:
        response = requests.post(url, headers=headers, data=body)
        print("🔁 OKX Status:", response.status_code)
        print("🔁 OKX Response:", response.text)

        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": "Response is not JSON", "detail": response.text}
    except Exception as e:
        return {"error": "Request exception", "detail": str(e)}

# Hàm gửi Telegram
def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=data)
        print("📬 TELEGRAM", response.status_code, "-", response.text)
    except Exception as e:
        print("Telegram error:", e)

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("📥 Webhook nhận:", data)

        # Giả sử TradingView gửi theo dạng:
        # {
        #   "symbol": "BTC-USDT",
        #   "side": "buy",
        #   "qty": 200
        # }

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty")

        if not symbol or not side or not qty:
            return jsonify({"error": "Thiếu thông tin"}), 400

        result = send_demo_order(symbol, side, qty)

        if "error" in result:
            msg = f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {qty} USDT\nChi tiết: {result}"
            send_telegram_message(msg)
            return jsonify(result), 500

        msg = f"✅ Gửi lệnh DEMO thành công: {symbol} - {side.upper()} {qty} USDT\nChi tiết: {result}"
        send_telegram_message(msg)
        return jsonify({"status": "ok", "result": result}), 200

    except Exception as e:
        error_msg = f"❌ Lỗi xử lý webhook: {str(e)}"
        send_telegram_message(error_msg)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
