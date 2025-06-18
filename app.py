import os
import json
import hmac
import hashlib
import base64
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Load biến môi trường ---
load_dotenv()

API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") or "https://discord.com/api/webhooks/your_webhook"

app = Flask(__name__)

# --- Hàm ký yêu cầu OKX ---
def sign_request(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

# --- Gửi tin nhắn tới Discord ---
def send_discord_message(text):
    try:
        payload = {"content": text}
        headers = {"Content-Type": "application/json"}
        response = requests.post(DISCORD_WEBHOOK_URL, headers=headers, json=payload, timeout=10)
        print("Discord response:", response.status_code, response.text)
    except Exception as e:
        print(f"Lỗi gửi Discord: {e}")

# --- Lấy giá thị trường ---
def get_market_price(symbol):
    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
    try:
        response = requests.get(url, timeout=10)
        print("DEBUG status:", response.status_code)
        print("DEBUG text:", response.text)
        data = response.json()
        return float(data['data'][0]['last'])
    except Exception as e:
        print(f"Lỗi lấy giá thị trường: {e}")
        return None

# --- Đặt lệnh OKX với 200 USDT ---
def place_order(symbol, side):
    last_price = get_market_price(symbol)
    if not last_price:
        send_discord_message("\u274C Lỗi: Không lấy được giá thị trường!")
        return {"error": "Không lấy được giá thị trường"}

    qty = round(200 / last_price, 4)
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

    try:
        response = requests.post(url, headers=headers, data=body, timeout=10)
        print("=== OKX DEBUG ===")
        print("Status:", response.status_code)
        print("Body:", response.text)
        return response.json()
    except Exception as e:
        print(f"Lỗi gửi lệnh OKX: {e}")
        return {"error": str(e)}

@app.route("/", methods=["GET"])
def home():
    return "Webhook bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received Webhook:", data)

    symbol = data.get("symbol")
    side = data.get("side")

    send_discord_message(f"\u2705 Nhận tín hiệu: {side.upper()} 200 USDT {symbol}")
    result = place_order(symbol, side)
    send_discord_message(f"\U0001F4B3 Kết quả đặt lệnh: {result}")

    return jsonify({"status": "done", "result": result})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
