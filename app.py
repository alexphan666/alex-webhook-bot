import os
import json
from flask import Flask, request
from okx.v5.trade import TradeAPI

app = Flask(__name__)

# Lấy biến môi trường OKX
api_key = os.getenv("OKX_API_KEY")
api_secret = os.getenv("OKX_API_SECRET")
api_passphrase = os.getenv("OKX_API_PASSPHRASE")

# Khởi tạo đối tượng giao dịch OKX
tradeAPI = TradeAPI(api_key, api_secret, api_passphrase, "https://www.okx.com")

@app.route('/')
def home():
    return 'AlexWebhookBot is running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("📩 Nhận tín hiệu:", data)

    symbol = data.get("coin")
    signal = data.get("signal")

    # Chỉ xử lý AAVEUSDT
    if symbol != "AAVEUSDT":
        print(f"⚠️ Bỏ qua {symbol}, chỉ giao dịch AAVEUSDT")
        return {"status": "ignored"}, 200

    side = "buy" if signal == "buy" else "sell"

    try:
        order = tradeAPI.place_order(
            instId="AAVE-USDT-SWAP",
            tdMode="isolated",
            side=side,
            ordType="market",
            sz="1"
        )
        print("✅ Đã gửi lệnh:", order)
        return {"status": "order_sent"}, 200
    except Exception as e:
        print("❌ Lỗi khi gửi lệnh:", e)
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

