import os
import json
import hmac
import hashlib
import base64
import time
import requests
import telegram
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Load các biến môi trường
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")

print("DEBUG TELEGRAM_TOKEN:", TELEGRAM_TOKEN)
print("DEBUG TELEGRAM_CHAT_ID:", CHAT_ID)

app = Flask(__name__)
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Lỗi khi gửi Telegram:", e)

def sign_request(timestamp, method, request_path, body, secret_key):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()

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
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, data=body)
    print("DEBUG response:", response.text)
    return response.json()

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

    send_telegram_message(f"Nhận tín hiệu: {side.upper()} {qty} {symbol}")
    response = place_order(symbol, side, qty)
    send_telegram_message(f"Kết quả đặt lệnh: {response}")

    return jsonify({"status": "success", "response": response})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
