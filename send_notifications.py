import json
import base64
import io
from datetime import datetime
from logger_setup import setup_logger

from send_discord import DiscordNotifier

logger = setup_logger(__name__)


def send_error_notifications(error_message, discord_webhook_url):
    timestamp = int(datetime.now().timestamp())
    error_data = {
        "action": "ERROR",
        "error_details": error_message,
        "timestamp": timestamp
    }
    error_json = json.dumps(error_data)

    # Send Discord notification
    try:
        discord_notifier = DiscordNotifier(discord_webhook_url)
        discord_notifier.send_decision(error_json, [])
        logger.info("Discord error notification sent successfully")
    except Exception as e:
        logger.error(f"Error sending Discord error notification: {e}")


def send_notifications(decision, chart_images, discord_webhook_url):
    logger.info("Sending notifications about the decision")

    # Prepare chart images for both Discord and Telegram
    discord_image_files = []
    telegram_image_files = []
    for image in chart_images:
        if image['image_data']:
            # For Discord
            discord_image_files.append(
                (f"{image['file_name']}.png", base64.b64decode(image['image_data']), 'image/png'))
            # For Telegram
            telegram_image_files.append(
                (f"{image['file_name']}.png", io.BytesIO(base64.b64decode(image['image_data'])), 'image/png'))
        else:
            logger.warning(f"No image data for {image['file_name']}. Skipping this image.")

    # Send Discord notification
    try:
        discord_notifier = DiscordNotifier(discord_webhook_url)
        discord_notifier.send_decision(decision, discord_image_files)
        logger.info("Discord notification sent successfully")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
