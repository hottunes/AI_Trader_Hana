
import os
from datetime import datetime
import re

import aiohttp
from dotenv import load_dotenv

from logger_setup import setup_logger

logger = setup_logger(__name__)


def clean_text(text):
    # Replace Unicode characters with ASCII equivalents
    text = text.replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2013', '-').replace('\u2014', '--')

    # Remove placeholder content
    text = text.replace('TKTK', '')

    # Standardize whitespace
    text = ' '.join(text.split())

    # Standardize ellipsis
    text = text.replace('...', '…').replace('. . .', '…')

    # Remove extra spaces before punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)

    # Ensure single space after punctuation
    text = re.sub(r'([.,!?;:])(?=[^\s])', r'\1 ', text)

    # Standardize quotation marks
    text = re.sub(r'(?<=\s)"(?=\S)', '"', text)
    text = re.sub(r'(?<=\S)"(?=[\s.,!?;:]|$)', '"', text)

    return text.strip()


async def fetch_and_nomalized_crypto_news_data(rapidapi_key, rapidapi_host):
    logger.info("Fetching crypto news data")

    async with aiohttp.ClientSession() as session:
        headers = {
            'x-rapidapi-key': rapidapi_key,
            'x-rapidapi-host': rapidapi_host
        }
        url = f"https://{rapidapi_host}/api/v1/crypto/articles?page=1&limit=50&time_frame=24h&format=json&source=coindesk"

        async with session.get(url, headers=headers) as response:
            parsed_data = await response.json()

    result = []
    for article in parsed_data:
        title = clean_text(article.get('title', '')) if article.get('title') else ''
        summary = clean_text(article.get('summary', '')) if article.get('summary') else ''
        published = article.get('published', '')
        try:
            timestamp = int(datetime.fromisoformat(published.replace('Z', '+00:00')).timestamp())
        except (ValueError, AttributeError):
            continue  # Skip articles with invalid timestamps

        if title and timestamp:
            result.append([timestamp, title, summary])

    logger.info(f"Processed {len(result)} valid crypto news articles")

    return result if result else "No coindesk newspaper articles in the last 24 hours."

if __name__ == "__main__":
    load_dotenv()
    rapidapi_news_key = os.getenv('RAPIDAPI_NEWS_KEY')
    rapidapi_news_host = os.getenv('RAPIDAPI_NEWS_HOST')
    print(fetch_and_nomalized_crypto_news_data(rapidapi_news_key, rapidapi_news_host))
