import requests
import json
import hmac
import base64
import time
import hashlib
from flask import Flask, request
import os
import telegram

app = Flask(__name__)

# Biến môi trường
API_KEY = os.getenv("OKX_API_KEY")
API_SECRET = os.getenv("OKX_API_SECRET")
API_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BASE_URL = "https://www.okx.com"  # Hoặc URL testnet nếu dùng demo

# Telegram bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
print(f"DEBUG TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
print(f"DEBUG TELEGRAM_CHAT_ID: {CHAT_ID}")
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Lỗi khi gửi Telegram:", e)

def get_iso_timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())

def sign_request(timestamp, method, request_path, body, secret_key):
    message = f'{timestamp}{method}{request_path}{body}'
    mac = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256)
    d = mac.digest()
    return base64.b64encode(d).decode()

def place_order(symbol, side, usdt_amount):
    url = f"{BASE_URL}/api/v5/trade/order"
    
    # Tính giá trị số lượng (ví dụ giả định giá BTC khoảng 65,000 để chia USDT lấy số lượng)
    # Ở bản đầy đủ nên dùng API get giá market real-time
    notional = usdt_amount

    order = {
        "instId": symbol,
        "tdMode": "isolated",
        "side": side,
        "ordType": "market",
        "sz": "",  # nếu spot thì cần số lượng coin, futures thì dùng leverage + margin
        "ccy": "USDT",  # bắt buộc cho demo trading futures
        "posSide": "net",  # net hoặc long/short nếu dual
        "notional": str(notional),
        "lever": "20"
    }

    timestamp = get_iso_timestamp()
    body = json.dumps(order)
    signature = sign_request(timestamp, "POST", "/api/v5/trade/order", body, API_SECRET)

    headers = {
        "Content-Type": "application/json",
        "OK-ACCESS-KEY": API_KEY,
        "OK-ACCESS-SIGN": signature,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": API_PASSPHRASE,
        "x-simulated-trading": "1",  # chỉ bật nếu là demo
    }

    try:
        response = requests.post(url, headers=headers, json=order)
        try:
            res_json = response.json()
        except Exception as e:
            send_telegram_message(f"❌ Không đọc được JSON từ OKX:\n{response.text}")
            return

        if res_json.get("code") == "0":
            send_telegram_message(f"✅ Đã đặt lệnh {side.upper()} {symbol} - {usdt_amount} USDT")
        else:
            send_telegram_message(f"❌ Lỗi từ OKX: {res_json}")
    except Exception as e:
        send_telegram_message(f"❌ Lỗi khi đặt lệnh: {str(e)}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    symbol = data.get("symbol")
    side = data.get("side")
    qty = data.get("qty")

    send_telegram_message(f"📈 Đã nhận tín hiệu: {side.upper()} {symbol} - {qty} USDT")

    if symbol and side and qty:
        place_order(symbol, side, qty)
    else:
        send_telegram_message("⚠️ Tín hiệu không hợp lệ.")

    return {"status": "ok"}
