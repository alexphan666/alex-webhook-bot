from flask import Flask, request
import os
import time
import hmac
import hashlib
import base64
import requests
import json

app = Flask(__name__)

@app.route('/')
def index():
    return '🚀 Alex Webhook Bot is running'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("📩 Nhận tín hiệu:", data)

    coin = data.get('coin')         # Ví dụ: AAVE-USDT
    side = data.get('signal')       # 'buy' hoặc 'sell'

    if not coin or not side:
        return {'error': 'Thiếu coin hoặc signal'}, 400

    try:
        response = send_order_to_okx(coin, side)
        print("✅ OKX Response:", response)
        return {'status': 'Đã gửi lệnh thành công', 'response': response}
    except Exception as e:
        print("❌ Lỗi khi gửi lệnh:", str(e))
        return {'error': str(e)}, 500

def send_order_to_okx(coin, side):
    api_key = os.getenv("OKX_API_KEY")
    secret_key = os.getenv("OKX_API_SECRET")
    passphrase = os.getenv("OKX_API_PASSPHRASE")

    url = "https://www.okx.com/api/v5/trade/order"
    method = "POST"

    body = {
        "instId": coin,                # Ví dụ: "AAVE-USDT"
        "tdMode": "isolated",
        "side": side,                  # "buy" hoặc "sell"
        "ordType": "market",
        "sz": "1"                      # Khối lượng (test là 1)
    }

    timestamp = str(time.time())
    prehash = f"{timestamp}{method}/api/v5/trade/order{json.dumps(body)}"
    sign = base64.b64encode(
        hmac.new(secret_key.encode(), prehash.encode(), hashlib.sha256).digest()
    ).decode()

    headers = {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": sign,
        "OK-ACCESS-TIMESTAMP": timestamp,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    print("🔐 Headers:", headers)
    print("📦 Body gửi đi:", body)

    response = requests.post(url, headers=headers, json=body)

    print("💬 OKX Status Code:", response.status_code)
    print("💬 OKX Raw Response:", response.text)

    try:
        return response.json()
    except json.JSONDecodeError:
        raise Exception("Lỗi phản hồi từ OKX: Không phải định dạng JSON")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)