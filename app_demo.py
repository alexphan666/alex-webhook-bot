@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if data is None:
        return 'No data received', 400

    # Lấy thông tin từ TradingView
    signal = data.get("signal")
    coin = data.get("coin")  # BTC, AAVE, BCH

    # Gửi tin nhắn về Telegram
    send_telegram_message(f"[DEMO] Tín hiệu nhận được: {signal.upper()} - {coin.upper()}")

    # Xác định mã giao dịch trên OKX
    symbol_map = {
        "BTC": "BTC-USDT",
        "AAVE": "AAVE-USDT",
        "BCH": "BCH-USDT"
    }

    symbol = symbol_map.get(coin.upper(), None)
    if not symbol:
        return "Symbol not supported", 400

    # Khối lượng mỗi lệnh DEMO
    amount = "10"  # 10 USDT

    if signal.lower() == "buy":
        order_response = place_order(symbol, "buy", amount)
    elif signal.lower() == "sell":
        order_response = place_order(symbol, "sell", amount)
    else:
        return "Unknown signal", 400

    return f"Order placed: {order_response}", 200