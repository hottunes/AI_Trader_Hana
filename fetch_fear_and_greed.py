import aiohttp
from collections import OrderedDict

from logger_setup import setup_logger

logger = setup_logger(__name__)


async def fetch_fear_and_greed_index(limit=1, date_format=''):
    logger.info("Fetching Fear and Greed Index data...")
    base_url = "https://api.alternative.me/fng/"
    params = {
        'limit': limit,
        'format': 'json',
        'date_format': date_format
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            data = await response.json()

    data = data['data'][0]

    ordered_data = OrderedDict([
        ('timestamp', data['timestamp']),
        ('value', data['value']),
        ('value_classification', data['value_classification']),
        ('time_until_update', data['time_until_update'])
    ])
    logger.info("Fear and Greed Index data fetched successfully")
    return ordered_data

if __name__ == "__main__":
    print(fetch_fear_and_greed_index())
