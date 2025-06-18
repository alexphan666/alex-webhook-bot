import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Cấu hình ứng dụng và biến môi trường ---
load_dotenv()

# Biến môi trường cho OKX
API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

# Webhook Discord URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1376064332852629514/5m43o513-HVIhtNlT2Q3BlAeW5GvE0a6GM8xtUTDOeUosjhgkmtJ5rzZoU4MyGJ0L9Ff"

# Khởi tạo ứng dụng Flask
app = Flask(__name__)

# --- Hàm ký (sign) yêu cầu API OKX ---
def sign_request(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# --- Hàm gửi tin nhắn Discord ---
def send_discord_message(text):
    try:
        payload = {"content": text}
        headers = {"Content-Type": "application/json"}
        response = requests.post(DISCORD_WEBHOOK_URL, headers=headers, json=payload)
        print("Discord response:", response.text)
    except Exception as e:
        print(f"Lỗi khi gửi Discord: {e}")

# --- Hàm đặt lệnh trên OKX ---
def place_order(symbol, side, qty):
    url = "https://www.okx.com/api/v5/trade/order"
    timestamp = str(time.time())
    body = json.dumps({
        "instId": symbol,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": str(qty),
        "posSide": "long" if side == "buy" else "short",
        "lever": "20"
    })
    headers = {
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": sign_request(timestamp, "POST", "/api/v5/trade/order", body, API_SECRET),
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json",
        "x-simulated-trading": "1"
    }
    response = requests.post(url, headers=headers, data=body)
    print("DEBUG response:", response.text)
    return response.json()

# --- Định nghĩa các route cho Flask app ---
@app.route("/", methods=["GET"])
def home():
    return "Webhook bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received Webhook:", data)

    symbol = data.get("symbol")
    side = data.get("side")
    qty = data.get("qty")

    send_discord_message(f"Nhận tín t\xedn hiệu: {side.upper()} {qty} {symbol}")
    response = {"note": "Đã nhận tín hiệu nhưng KHÔNG gửi lệnh OKX vì bị Cloudflare block."}
    send_discord_message(f"Kết quả đặt lệnh: {response}")

    return jsonify({"status": "success", "response": response})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
