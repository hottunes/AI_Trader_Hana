import os

import requests
import logging
import json
from datetime import datetime, timezone
import pytz
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.MAX_MESSAGE_LENGTH = 2000

    def send_message(self, message, image_files=None):
        if len(message) > self.MAX_MESSAGE_LENGTH:
            chunks = self.split_message(message)
            for chunk in chunks:
                self._send_single_message(chunk)
            if image_files:
                self._send_single_message("", image_files)
        else:
            self._send_single_message(message, image_files)

    def _send_single_message(self, message, image_files=None):
        payload = {"content": message}
        files = {}
        try:
            if image_files:
                for i, image_file in enumerate(image_files):
                    file_name, file_data, content_type = image_file
                    files[f'file{i}'] = (file_name, file_data, content_type)
                response = requests.post(self.webhook_url, data=payload, files=files)
            else:
                response = requests.post(self.webhook_url, json=payload)

            if response.status_code in [200, 204]:
                logger.info("Message sent to Discord successfully")
            else:
                logger.error(f"Failed to send message to Discord. Status code: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending message to Discord: {str(e)}")

    def split_message(self, message):
        chunks = []
        while len(message) > self.MAX_MESSAGE_LENGTH:
            split_index = message.rfind('\n', 0, self.MAX_MESSAGE_LENGTH)
            if split_index == -1:
                split_index = self.MAX_MESSAGE_LENGTH
            chunks.append(message[:split_index])
            message = message[split_index:].lstrip()
        chunks.append(message)
        return chunks

    def send_decision(self, decision, image_files):
        try:
            decision_data = json.loads(decision) if isinstance(decision, str) else decision

            utc_time = datetime.fromtimestamp(decision_data['timestamp'], tz=timezone.utc)
            seoul_tz = pytz.timezone('Asia/Seoul')
            seoul_time = utc_time.astimezone(seoul_tz)
            formatted_seoul_time = seoul_time.strftime('%Y-%m-%d %H:%M')

            message = (
                f"**결정:** {decision_data['action'].upper()}\n"
                f"**시간:** {formatted_seoul_time}\n\n"
            )

            trade_details = decision_data.get('trade_details', {})
            if trade_details:
                message += (
                    f"SL: ${trade_details.get('stop_loss', 'N/A')}\n"
                    f"TP: ${trade_details.get('take_profit', 'N/A')}\n\n"
                )

            rationale = decision_data.get('rationale', {})
            if rationale:
                message += (
                    f"차트:\n{rationale.get('technical_analysis', 'N/A')}\n\n"
                    f"뉴스:\n{rationale.get('news_impact', 'N/A')}\n\n"
                    f"감정:\n{rationale.get('market_sentiment', 'N/A')}\n\n"
                    f"결론:\n{rationale.get('conclusion', 'N/A')}\n\n"
                )

            message += f"**신뢰도:** {decision_data.get('confidence_score', 'N/A')}\n\n"

            self.send_message(message, image_files)

        except json.JSONDecodeError:
            logger.error("Failed to parse decision JSON")
            self.send_message("Error: Failed to parse decision data")
        except KeyError as e:
            logger.error(f"Missing key in decision data: {str(e)}")
            self.send_message(f"Error: Missing key in decision data - {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in send_decision: {str(e)}")
            self.send_message(f"Error: Unexpected error occurred - {str(e)}")


def main():
    load_dotenv()
    DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
    discord_notifier = DiscordNotifier(DISCORD_WEBHOOK_URL)

    message = {
        "action": "Maintain Short Position",
        "trade_details": {
            "stop_loss": 55500.0,
            "take_profit": 50200.0
        },
        "rationale": {
            "technical_analysis": "Bitcoin is still trading within a downward trend both on the daily and 4-hour charts. The price remains below the 50-day and 200-day EMAs on the 1D chart, reinforcing the bearish bias. The RSI on both the 1D (35.40) and 4H chart (36.89) is nearing oversold territory, but no clear signs of reversal or bullish divergences have appeared yet. The MACD on both timeframes remains bearish. The 4H chart shows a falling wedge pattern, a typically bullish reversal sign, but a confirmed breakout has yet to occur, and the momentum is still weak.",
            "news_impact": "Recent economic data, including weaker U.S. jobs reports, are contributing to overall cautious market sentiment, keeping pressure on Bitcoin and other risk assets. Tether's investment in agriculture has made headlines but did not generate any immediate effects on Bitcoin's price. Broader macroeconomic uncertainty continues to weigh on sentiment, with no major bullish news currently present.",
            "market_sentiment": "The Crypto Fear and Greed Index remains in 'Fear' territory at 29, indicating a pessimistic market mood. TradingView community ideas remain mixed, but the most popular ones continue to emphasize the potential for further downside, with some targeting as low as $50K. Growing concerns about economic conditions and Bitcoin's prolonged downtrend are reflected in both news and trader sentiment.",
            "conclusion": "Due to the sustained bearish momentum, the lack of a breakout in the falling wedge pattern, and ongoing negative market sentiment, it is prudent to maintain the current short position. The stop-loss is appropriately set at $55,500 above resistance levels, and the take-profit target remains at $50,200, aligning well with short-term support levels."
        },
        "confidence_score": 0.78,
        "timestamp": 1725807732
    }
    # For testing purposes, we'll use None for image_files
    # In a real scenario, you would provide actual image files
    image_files = None

    discord_notifier.send_decision(message, image_files)
    print("Message sent to Discord")


if __name__ == "__main__":
    main()