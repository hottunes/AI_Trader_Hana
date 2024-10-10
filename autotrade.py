import os
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

import schedule
from dotenv import load_dotenv
from openai import OpenAI
from capture_chart_images import capture_tradingview_charts, get_chart_images
from send_discord import DiscordNotifier
from fetch_bybit_status import fetch_bybit_current_status
from fetch_cyrpto_news import fetch_and_nomalized_crypto_news_data
from fetch_fear_and_greed import fetch_fear_and_greed_index
from send_notifications import send_error_notifications, send_notifications
from fetch_tradingview_ideas import get_normalized_tradingview_ideas
from fetch_tradingview_news import fetch_and_normalized_tradingview_news
from logger_setup import setup_logger

from fetch_database import fetch_recent_decisions, save_decision_to_db, initialize_db
from excute_trading import execute_bybit_trade
from util import get_instructions

logger = setup_logger(__name__)
load_dotenv()

# Access the variables
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
BINANCE_API_KEY = os.getenv('BYBIT_TESTNET_API_KEY')
BINANCE_API_SECRET = os.getenv('BYBIT_TESTNET_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
RAPIDAPI_TRADINGVIEW_KEY = os.getenv('RAPIDAPI_TRADINGVIEW_KEY')
RAPIDAPI_TRADINGVIEW_HOST = os.getenv('RAPIDAPI_TRADINGVIEW_HOST')
RAPIDAPI_NEWS_KEY = os.getenv('RAPIDAPI_NEWS_KEY')
RAPIDAPI_NEWS_HOST = os.getenv('RAPIDAPI_NEWS_HOST')
BYBIT_API_KEY_1 = os.getenv('BYBIT_API_KEY_1')
BYBIT_API_SECRET_1 = os.getenv('BYBIT_API_SECRET_1')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialize clients
discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)
logger.info("Initializing OpenAI client")
client = OpenAI(api_key=OPENAI_API_KEY)
logger.info("Initializing BYBIT client")

api_token_usage = 0


async def make_decision_and_execute() -> None:
    logger.info("Starting decision-making and execution")
    try:
        # Create tasks for all async operations
        crypto_news_task = asyncio.create_task(
            fetch_and_nomalized_crypto_news_data(RAPIDAPI_NEWS_KEY, RAPIDAPI_NEWS_HOST))
        tradingview_ideas_task = asyncio.create_task(
            get_normalized_tradingview_ideas(RAPIDAPI_TRADINGVIEW_KEY, RAPIDAPI_TRADINGVIEW_HOST))
        tradingview_news_task = asyncio.create_task(
            fetch_and_normalized_tradingview_news(RAPIDAPI_TRADINGVIEW_KEY, RAPIDAPI_TRADINGVIEW_HOST))
        last_decisions_task = asyncio.create_task(fetch_recent_decisions())
        fear_and_greed_task = asyncio.create_task(fetch_fear_and_greed_index())

        # Wait for all tasks to complete and log each result
        crypto_news = await crypto_news_task
        logger.info("Crypto news fetched successfully")

        tradingview_ideas = await tradingview_ideas_task
        logger.info("TradingView ideas fetched successfully")

        tradingview_overall_news = await tradingview_news_task
        logger.info("TradingView news fetched successfully")

        last_decisions = await last_decisions_task
        logger.info("Last decisions fetched successfully")

        fear_and_greed = await fear_and_greed_task
        logger.info("Fear and Greed index fetched successfully")

        # Error handling for capture_tradingview_charts
        try:
            tradingview_chart_images = await capture_tradingview_charts(get_chart_images())
        except Exception as e:
            error_message = f"Failed to capture TradingView charts: {str(e)}"
            logger.error(error_message)
            send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
            return
        logger.info("TradingView charts captured successfully")

        # Error handling for get_bybit_current_status
        try:
            current_account_status = fetch_bybit_current_status(BYBIT_API_KEY_1, BYBIT_API_SECRET_1, testnet=False)
            logger.info("Bybit account status fetched successfully")

            # Determine the instructions path based on the current position type
            if current_account_status['position']['type'] == 'Short':
                instructions_path = "instructions_3_Short.md"
            elif current_account_status['position']['type'] == 'Long':
                instructions_path = "instructions_3_Long.md"
            else:  # None or any other type (which means Closed)
                instructions_path = "instructions_3_Closed.md"

            logger.info(f"Selected instructions path: {instructions_path}")
        except Exception as e:
            error_message = f"Failed to fetch Bybit account status: {str(e)}"
            logger.error(error_message)
            send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
            return

    except Exception as e:
        error_message = f"An error occurred while fetching data: {str(e)}. Analysis terminated."
        logger.error(error_message, exc_info=True)
        send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
        return

    try:
        advice = analyze_data_with_gpt4(
            instructions_path,
            tradingview_chart_images,
            crypto_news,
            tradingview_ideas,
            tradingview_overall_news,
            fear_and_greed,
            last_decisions,
            current_account_status
        )
        decision = json.loads(advice)
        decision['timestamp'] = int(datetime.now().timestamp())
        logger.info(f"Decision made: {json.dumps(decision, indent=2)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {e}")
        error_message = f"Failed to parse decision: {str(e)}"
        send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
        return
    except Exception as e:
        logger.error(f"Unexpected error in decision making: {str(e)}")
        error_message = f"Error in decision making: {str(e)}"
        send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
        return

    try:
        order_result = execute_bybit_trade(decision, BYBIT_API_KEY_1, BYBIT_API_SECRET_1, testnet=False)
        if isinstance(order_result, dict) and 'error' in order_result:
            raise Exception(order_result['error'])
        logger.info(f"Order execution result: {order_result}")
    except Exception as e:
        logger.error(f"Error in executing decision: {str(e)}")
        error_message = f"Error in executing decision: {str(e)}\nDecision: {json.dumps(decision, indent=2)}"
        send_error_notifications(error_message, DISCORD_WEBHOOK_URL)
        return

    logger.info("Saving decision to DB")
    await save_decision_to_db(decision)
    logger.info("Decision saved to DB")
    logger.info("Sending notifications about the decision")
    send_notifications(json.dumps(decision), tradingview_chart_images, DISCORD_WEBHOOK_URL)
    logger.info("Finished sending notifications about the decision")
    logger.info("Decision making and execution process completed")


def analyze_data_with_gpt4(
        instructions_path: str,
        tradingview_chart_images: List[Dict[str, Any]],
        crypto_news: Dict[str, Any],
        tradingview_ideas: Dict[str, Any],
        tradingview_overall_news: Dict[str, Any],
        fear_and_greed: Dict[str, Any],
        last_decisions: List[Dict[str, Any]],
        current_account_status: Dict[str, Any]
) -> Optional[str]:
    global api_token_usage

    try:
        instructions = get_instructions(instructions_path)
        if not instructions:
            logger.error("No instructions found.")
            return None

        messages = [
            {"role": "system", "content": instructions},
        ]

        # Adding each trading view image separately
        for chart_info in tradingview_chart_images:
            if chart_info["image_data"]:
                try:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "image_url",
                             "image_url": {"url": f"data:image/png;base64,{chart_info['image_data']}"}}
                        ]
                    })
                    logger.info(f"Added image for {chart_info['file_name']} to messages")
                except Exception as e:
                    logger.error(f"Error adding image for {chart_info['file_name']}: {str(e)}")
            else:
                logger.warning(f"Image data not available for {chart_info['file_name']}")

        # Adding other data
        messages.extend(
            {"role": "user", "content": json.dumps(data, ensure_ascii=False, indent=2)}
            for data in [last_decisions, crypto_news, tradingview_ideas, fear_and_greed, tradingview_overall_news,
                         current_account_status]
        )

        try:
            response = client.chat.completions.create(
                model="chatgpt-4o-latest",
                messages=messages,
                response_format={"type": "json_object"}
            )

            advice = response.choices[0].message.content

            # Increment the token usage counter based on the response
            api_token_usage += response.usage.total_tokens
            logger.info(f"Finished analyze_data_with_gpt4. Updated api_token_usage: {api_token_usage}")

            return advice
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return None

    except Exception as e:
        logger.error(f"Error in analyzing data with GPT-4: {str(e)}")
        return None


def run_make_decision_and_execute() -> None:
    asyncio.run(make_decision_and_execute())


if __name__ == "__main__":
    initialize_db()
    for hour in ["03:58", "07:58", "11:58", "15:58", "19:58", "23:58"]:
        schedule.every().day.at(hour, "UTC").do(run_make_decision_and_execute)

    logger.info("Scheduler initialized. Waiting for scheduled runs.")

    while True:
        schedule.run_pending()
