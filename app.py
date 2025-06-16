from flask import Flask, request, jsonify
import requests
import os
import json
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# Thiết lập Flask
app = Flask(__name__)

# Lấy thông tin từ .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY_DEMO")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY_DEMO")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE_DEMO")

# Gửi tin nhắn Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload)
        print("[TELEGRAM]", response.status_code, "-", response.text)
    except Exception as e:
        print("[TELEGRAM ERROR]", str(e))

# Gửi lệnh demo lên OKX
def send_demo_order(symbol, side, qty):
    if not OKX_API_KEY or not OKX_SECRET_KEY or not OKX_PASSPHRASE:
        return {"error": "Missing OKX demo API credentials."}

    url = "https://www.okx.com/api/v5/trade/order"

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": OKX_API_KEY,
        "OK-ACCESS-SIGN": "",  # Nếu cần sign thật phải thêm
        "OK-ACCESS-TIMESTAMP": "",
        "OK-ACCESS-PASSPHRASE": OKX_PASSPHRASE
    }

    payload = {
        "instId": symbol,
        "tdMode": "cash",
        "side": side,
        "ordType": "market",
        "sz": str(qty)
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        try:
            return response.json()
        except json.JSONDecodeError:
            return {
                "error": "Non-JSON response from OKX",
                "status_code": response.status_code,
                "text": response.text[:500]  # chỉ gửi 500 ký tự đầu nếu là HTML
            }
    except Exception as e:
        return {"error": str(e)}

# Webhook nhận tín hiệu từ TradingView
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("[WEBHOOK]", data)

        symbol = data.get("symbol")
        side = data.get("side")
        qty = data.get("qty", 200)

        if not symbol or not side:
            return jsonify({"error": "Thiếu symbol hoặc side"}), 400

        result = send_demo_order(symbol, side, qty)

        if "error" in result:
            msg = f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {qty} USDT\nLý do: {result.get('error', 'Không rõ')}"
            send_telegram_message(msg)
            return jsonify(result), 500

        msg = f"✅ Gửi lệnh DEMO thành công: {symbol} - {side.upper()} {qty} USDT"
        send_telegram_message(msg)
        return jsonify({"status": "ok", "result": result}), 200

    except Exception as e:
        error_msg = f"❌ Lỗi xử lý webhook: {str(e)}"
        send_telegram_message(error_msg)
        return jsonify({"error": str(e)}), 500

# Chạy Flask nếu cần
if __name__ == "__main__":
    app.run(debug=True)
