import os
import json
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()  # Load biến môi trường từ .env

app = Flask(__name__)

# Biến môi trường
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
OKX_BASE_URL = "https://www.okx.com"

HEADERS = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-SIGN": "",
    "OK-ACCESS-TIMESTAMP": "",
    "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE,
    "x-simulated-trading": "1"  # Giao dịch demo
}


def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, json=payload)


def sign_request(timestamp, method, request_path, body=""):
    message = f"{timestamp}{method}{request_path}{body}"
    mac = hmac.new(bytes(OKX_API_SECRET, encoding='utf8'), bytes(message, encoding='utf8'), digestmod=hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode("utf-8")


def place_order(symbol, side, usdt_amount):
    # Lấy giá hiện tại
    ticker = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}").json()
    price = float(ticker["data"][0]["last"])

    # Tính số lượng coin và lấy giá TP, SL
    qty = round(usdt_amount / price, 6)
    tp_price = round(price * 1.01, 2)  # Trailing TP 1%
    sl_price = round(price * 0.985, 2)  # SL 1.5%

    timestamp = str(time.time())
    method = "POST"
    path = "/api/v5/trade/order"

    body = {
        "instId": symbol,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": str(qty),
        "lever": "20"
    }

    body_str = json.dumps(body)
    sign = sign_request(timestamp, method, path, body_str)

    HEADERS["OK-ACCESS-SIGN"] = sign
    HEADERS["OK-ACCESS-TIMESTAMP"] = timestamp

    response = requests.post(OKX_BASE_URL + path, headers=HEADERS, data=body_str)
    if response.status_code == 200:
        send_telegram_message(f"✅ Đã gửi lệnh DEMO: {side.upper()} {symbol} - Số lượng: {qty}\nTP: {tp_price} | SL: {sl_price}")
        return response.json()
    else:
        send_telegram_message(f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {usdt_amount} USDT\nChi tiết: {response.text}")
        return {"error": response.text}


@app.route("/")
def index():
    return "✅ Webhook bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("[WEBHOOK]", data)

    symbol = data.get("symbol")
    side = data.get("side")
    qty = data.get("qty")

    if not symbol or not side or not qty:
        return jsonify({"error": "Missing required fields"}), 400

    # Gửi thông báo Telegram
    send_telegram_message(f"📈 Tín hiệu nhận được: {side.upper()} {symbol} - Số lượng: {qty}")

    # Gửi lệnh đến OKX
    result = place_order(symbol, side, qty)

    if "error" in result:
        return jsonify(result), 500

    return jsonify({"message": "Order placed successfully"})


if __name__ == "__main__":
    app.run(debug=True)
