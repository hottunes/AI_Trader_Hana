import re

import aiohttp

from logger_setup import setup_logger

logger = setup_logger(__name__)


async def fetch_tradingview_ideas(rapidapi_key, rapidapi_host):
    logger.info("Fetching TradingView ideas")
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': rapidapi_host
    }

    url = f"https://{rapidapi_host}/ideas/list?page=1&per_page=20&sort=recent&market=bitcoin&stock_country=us&symbol=BTCUSDT&locale=en"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()

        json_data = data
        logger.info(f"Fetched {len(json_data['results'])} TradingView ideas")
        unique_entries = {}
        for result in json_data["results"]:
            title = result["name"].strip()
            cleaned_result = [
                result["date_timestamp"],
                result["likes_count"],
                title,
                result["description"].strip(),
            ]
            if title not in unique_entries or result["date_timestamp"] > unique_entries[title][0]:
                unique_entries[title] = cleaned_result

        processed_ideas = list(unique_entries.values())
        logger.info(f"Processed {len(processed_ideas)} unique TradingView ideas")
        return processed_ideas

    except Exception as e:
        error_message = f"An error occurred: {e}"
        return [[None, None, None, error_message]]


def normalize_text(text, max_length=1500):
    # Remove emojis and special characters
    text = re.sub(r'[^\w\s$.,!?%-]', '', text)

    # Remove excessive whitespace
    text = ' '.join(text.split())

    # Fix common typos and abbreviations, and standardize capitalization
    replacements = {
        'btc': 'Bitcoin',
        'bct': 'Bitcoin',
        'btcusdt': 'Bitcoin',
        'btc/usdt': 'Bitcoin',
        'bitcoin': 'Bitcoin',
        'BITCOIN': 'Bitcoin',
        'hodl': 'hold',
        'bullish': 'bullish',
        'bearish': 'bearish',
        'dump': 'decrease',
        'pump': 'increase',
        'moon': 'significant increase',
        'fud': 'fear uncertainty doubt',
        'ath': 'all-time high',
        'dca': 'dollar cost average',
        'ta': 'technical analysis',
        'fa': 'fundamental analysis',
        'rsi': 'relative strength index',
        'ma': 'moving average',
        'usdt': 'USDT',
        'fed': 'FED',
    }

    for old, new in replacements.items():
        text = re.sub(r'\b' + re.escape(old) + r'\b', new, text, flags=re.IGNORECASE)

    # Standardize price formatting
    text = re.sub(r'\$(\d+)k', r'$\1,000', text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)(?=\s|$)', lambda m: f"${float(m.group(1)):,.2f}", text)

    # Truncate to max_length
    return text[:max_length]


def normalize_data(data):
    normalized_data = []
    for item in data:
        normalized_item = [
            item[0],  # Keep timestamp as is
            item[1],  # Keep likes count as is
            normalize_text(item[2]),  # Normalize title
            normalize_text(item[3])  # Normalize description
        ]
        normalized_data.append(normalized_item)
    return normalized_data


async def get_normalized_tradingview_ideas(rapidapi_key, rapidapi_host):
    # Fetch the data
    data = await fetch_tradingview_ideas(rapidapi_key, rapidapi_host)

    # Normalize the data
    normalized_data = normalize_data(data)

    # Convert to JSON and return
    return normalized_data
