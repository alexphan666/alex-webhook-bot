@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"[DEBUG] Nhận tín hiệu: {data}")  # In toàn bộ dữ liệu gửi đến

        if data is None:
            print("[ERROR] Không nhận được data")
            return 'No data received', 400

        signal = data.get("signal")
        coin = data.get("coin")
        print(f"[DEBUG] Tín hiệu: {signal}, Coin: {coin}")

        if not signal or not coin:
            print("[ERROR] Thiếu tín hiệu hoặc coin")
            return 'Missing signal or coin', 400

        # Map coin với instId trên OKX
        symbol_map = {
            "BTC": "BTC-USDT",
            "AAVE": "AAVE-USDT",
            "BCH": "BCH-USDT"
        }
        symbol = symbol_map.get(coin.upper())
        if not symbol:
            print("[ERROR] Coin không nằm trong danh sách hỗ trợ")
            return "Symbol not supported", 400

        # Gửi tin nhắn Telegram
        send_telegram_message(f"[DEMO] Tín hiệu nhận được: {signal.upper()} - {coin.upper()}")

        # Gửi lệnh vào OKX
        amount = "10"
        if signal.lower() == "buy":
            response = place_order(symbol, "buy", amount)
        elif signal.lower() == "sell":
            response = place_order(symbol, "sell", amount)
        else:
            print("[ERROR] Tín hiệu không hợp lệ")
            return "Unknown signal", 400

        print(f"[OKX RESPONSE] {response}")
        return f"Order placed: {response}", 200

    except Exception as e:
        print(f"[EXCEPTION] Lỗi xảy ra: {str(e)}")
        return "Internal Server Error", 500