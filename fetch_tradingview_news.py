import re

import aiohttp
import unicodedata

from logger_setup import setup_logger

logger = setup_logger(__name__)


def clean_text(text):
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', '', text)
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return ' '.join(text.split())


async def fetch_and_normalized_tradingview_news(rapidapi_key, rapidapi_host):
    logger.info("Fetching TradingView news")
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': rapidapi_host
    }

    url = f"https://{rapidapi_host}/news/list?page=1&per_page=20&category=base&country=us&locale=en"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()

        logger.info(f"Fetched {len(data)} news items")
        normalized_data = [
            [
                item['published'],
                clean_text(item.get('source', '')),
                clean_text(item.get('title', ''))
            ]
            for item in data
        ]
        logger.info("TradingView news data is sent successfully")
        return normalized_data
    except Exception as e:
        logger.error(f"Error fetching TradingView news: {e}")
        return []

if __name__ == "__main__":
    news = fetch_and_normalized_tradingview_news()
    print(news)
