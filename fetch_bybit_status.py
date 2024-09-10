import hmac
import hashlib
import time
import requests
from dotenv import load_dotenv
import os

from logger_setup import setup_logger

logger = setup_logger(__name__)


def get_server_time(testnet=False):
    url = 'https://api-testnet.bybit.com/v5/market/time' if testnet else 'https://api.bybit.com/v5/market/time'
    response = requests.get(url)
    if response.status_code == 200:
        return int(response.json()['result']['timeSecond'])
    else:
        logger.error(f"Failed to get server time: {response.text}")
        return int(time.time())


def get_signature(params, api_secret):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()


def make_request(url, params, api_key, api_secret):
    params['api_key'] = api_key
    params['timestamp'] = get_server_time(testnet=url.startswith('https://api-testnet')) * 1000
    params['recv_window'] = 10000
    params['sign'] = get_signature(params, api_secret)

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None


def get_btcusdt_ticker(api_key, api_secret, testnet=False):
    url = 'https://api-testnet.bybit.com/v5/market/tickers' if testnet else 'https://api.bybit.com/v5/market/tickers'
    params = {
        'category': 'linear',
        'symbol': 'BTCUSDT'
    }
    return make_request(url, params, api_key, api_secret)


def get_btcusdt_position(api_key, api_secret, testnet=False):
    url = 'https://api-testnet.bybit.com/v5/position/list' if testnet else 'https://api.bybit.com/v5/position/list'
    params = {
        'category': 'linear',
        'symbol': 'BTCUSDT'
    }
    return make_request(url, params, api_key, api_secret)


def fetch_bybit_current_status(api_key, api_secret, testnet=False):
    logger.info(f"Fetching Bybit current status ({'testnet' if testnet else 'mainnet'})")

    current_timestamp = get_server_time(testnet)
    ticker_data = get_btcusdt_ticker(api_key, api_secret, testnet)
    current_price = float(ticker_data['result']['list'][0]['lastPrice']) if ticker_data and ticker_data['retCode'] == 0 else None

    position_data = get_btcusdt_position(api_key, api_secret, testnet)
    position = position_data['result']['list'][0] if position_data and position_data['retCode'] == 0 and position_data['result']['list'] else None

    output = {
        "timestamp": current_timestamp,
        "current_market_price": round(current_price, 2) if current_price else None,
        "position": {
            "status": "Open" if position and float(position.get('size', '0')) != 0 else "Closed",
            "type": "Long" if position and position.get('side', '').lower() == 'buy' else "Short" if position and position.get('side', '').lower() == 'sell' else None,
        }
    }
    logger.info(f"Successfully fetched Bybit current status ({'testnet' if testnet else 'mainnet'})")
    return output


def main():
    load_dotenv()
    api_key = os.getenv('BYBIT_TESTNET_API_KEY')
    api_secret = os.getenv('BYBIT_TESTNET_SECRET')

    if not api_key or not api_secret:
        logger.error("Error: API key or secret not found in environment variables.")
        return

    status_testnet = fetch_bybit_current_status(api_key, api_secret, testnet=True)
    print("Testnet status:", status_testnet)


if __name__ == '__main__':
    main()
