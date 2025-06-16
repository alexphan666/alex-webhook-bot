import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_API_PASSPHRASE = os.getenv("OKX_API_PASSPHRASE")
OKX_BASE_URL = "https://www.okx.com"
LEVERAGE = 20

headers = {
    "Content-Type": "application/json",
    "OK-ACCESS-KEY": OKX_API_KEY,
    "OK-ACCESS-SIGN": "",
    "OK-ACCESS-TIMESTAMP": "",
    "OK-ACCESS-PASSPHRASE": OKX_API_PASSPHRASE
}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    print("[TELEGRAM]", response.status_code, "-", response.text)

def place_order(symbol, side, qty):
    try:
        # Get last price to calculate SL and TP
        ticker = requests.get(f"{OKX_BASE_URL}/api/v5/market/ticker?instId={symbol}").json()
        last_price = float(ticker["data"][0]["last"])
        
        # Convert to base size
        base_qty = qty / last_price

        # Determine order direction
        if side.lower() == "buy":
            sl_price = last_price * (1 - 0.015)
            tp_price = last_price * (1 + 0.01)
        else:
            sl_price = last_price * (1 + 0.015)
            tp_price = last_price * (1 - 0.01)

        # Round to 4 decimals
        sl_price = round(sl_price, 4)
        tp_price = round(tp_price, 4)
        base_qty = round(base_qty, 4)

        # Place market order
        order_payload = {
            "instId": symbol,
            "tdMode": "isolated",
            "side": side,
            "ordType": "market",
            "sz": str(base_qty),
            "lever": str(LEVERAGE)
        }
        order_response = requests.post(
            f"{OKX_BASE_URL}/api/v5/trade/order",
            headers=headers,
            json=order_payload
        ).json()
        print("[ORDER]", order_response)

        # Simulate SL & TP by sending to Telegram
        return {
            "status": "success",
            "tp_price": tp_price,
            "sl_price": sl_price,
            "entry_price": last_price
        }

    except Exception as e:
        return {"error": str(e)}

@app.route("/")
def index():
    return "OKX Webhook Bot Running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("[WEBHOOK]", data)

    symbol = data.get("symbol")
    side = data.get("side")
    qty = data.get("qty")

    if not all([symbol, side, qty]):
        return jsonify({"error": "Missing fields"}), 400

    result = place_order(symbol, side, qty)

    if "error" in result:
        send_telegram_message(f"❌ Gửi lệnh DEMO thất bại: {symbol} - {side.upper()} {qty} USDT\nChi tiết: {result}")
        return jsonify(result), 500

    msg = (
        f"📈 Tín hiệu nhận được: {side.upper()} {symbol} - Số lượng: {qty}\n"
        f"🎯 Entry: {result['entry_price']}\n"
        f"🛑 SL: {result['sl_price']}\n"
        f"📈 TP (trailing): {result['tp_price']}"
    )
    send_telegram_message(msg)

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(debug=True)
