import requests
import time
import hmac
import hashlib
import json

class TradeAPI:
    def __init__(self, api_key, secret_key, passphrase, base_url="https://www.okx.com"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.base_url = base_url

    def _get_timestamp(self):
        return str(int(time.time()))

    def _sign(self, timestamp, method, request_path, body=''):
        message = f"{timestamp}{method}{request_path}{body}"
        mac = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256)
        return mac.hexdigest()

    def _headers(self, method, path, body=''):
        timestamp = self._get_timestamp()
        signature = self._sign(timestamp, method, path, body)
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

    def place_order(self, instId, side, ordType, sz):
        path = '/api/v5/trade/order'
        url = self.base_url + path
        body_dict = {
            "instId": instId,
            "tdMode": "isolated",
            "side": side,
            "ordType": ordType,
            "sz": sz
        }
        body = json.dumps(body_dict)
        headers = self._headers('POST', path, body)
        response = requests.post(url, headers=headers, data=body)
        return response.json()