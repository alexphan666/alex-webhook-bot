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
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1376064332852629514/5m43o513-HVIhtNlT2Q3BlAeW5GvE0a6GM8xtUTDOeUosjhgkmtJ5rzZoU4MyGJ0L9Ff"

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
        response = requests.post(DISCORD_WEBHOOK_URL, headers=headers, json=payload)
        print("Discord response:", response.text)
    except Exception as e:
        print(f"Lỗi gửi Discord: {e}")

# --- Đặt lệnh OKX với 200 USDT ---
def place_order(symbol, side):
    ticker_url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        res = requests.get(ticker_url, headers=headers)
        print("DEBUG ticker:", res.status_code, res.text)

        if res.status_code != 200:
            raise Exception("Không kết nối được API giá")

        ticker_res = res.json()
        last_price = float(ticker_res['data'][0]['last'])
        qty = round(200 / last_price, 4)  # Mua 200 USDT
    except Exception as e:
        send_discord_message(f"Lỗi lấy giá thị trường: {e}")
        return {"error": "Không lấy được giá thị trường"}

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
    print("=== OKX DEBUG ===")
    print("Status:", response.status_code)
    print("Body:", response.text)

    try:
        return response.json()
    except Exception as e:
        return {"error": f"Không parse được JSON: {e}"}

# --- Flask routes ---
@app.route("/", methods=["GET"])
def home():
    return "Webhook bot is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Received Webhook:", data)

    symbol = data.get("symbol")
    side = data.get("side")

    send_discord_message(f"✅ Nhận tín hiệu: {side.upper()} 200 USDT {symbol}")
    result = place_o_
