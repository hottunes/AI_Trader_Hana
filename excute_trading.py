import os

from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from logger_setup import setup_logger

logger = setup_logger(__name__)


def execute_bybit_trade(decision, api_key, api_secret, testnet=True):
    # Initialize the HTTP session
    session = HTTP(
        testnet=testnet,
        api_key=api_key,
        api_secret=api_secret
    )

    # Extract trade details
    action = decision['action']

    # Set desired leverage
    desired_leverage = 3.0

    # Get current position
    position_info = session.get_positions(category="linear", symbol="BTCUSDT")
    if position_info['retCode'] != 0:
        raise Exception(f"Failed to get position info: {position_info['retMsg']}")

    current_position = position_info['result']['list'][0]
    current_leverage = float(current_position['leverage'])
    current_size = float(current_position['size'])
    current_side = current_position['side']

    logger.info(f"Current leverage: {current_leverage}")
    logger.info(f"Current position: {current_size} ({current_side})")

    if action in ["Open Long", "Open Short", "Close Long", "Close Short", "Switch to Long", "Switch to Short"]:
        # Get account balance
        account_info = session.get_wallet_balance(accountType="UNIFIED")
        if account_info['retCode'] != 0:
            raise Exception(f"Failed to get account balance: {account_info['retMsg']}")

        balance = float(account_info['result']['list'][0]['totalEquity'])

        # Get current market price
        ticker = session.get_tickers(category="linear", symbol="BTCUSDT")
        if ticker['retCode'] != 0:
            raise Exception(f"Failed to get ticker: {ticker['retMsg']}")

        current_price = float(ticker['result']['list'][0]['lastPrice'])

        # Check if leverage needs to be changed
        if current_leverage != desired_leverage:
            try:
                leverage_result = session.set_leverage(
                    category="linear",
                    symbol="BTCUSDT",
                    buyLeverage=str(desired_leverage),
                    sellLeverage=str(desired_leverage)
                )
                if leverage_result['retCode'] != 0:
                    logger.warning(f"Failed to set leverage: {leverage_result['retMsg']}. Will use current leverage.")
                else:
                    logger.info(f"Leverage successfully set to {desired_leverage}")
                    current_leverage = desired_leverage
            except Exception as e:
                logger.warning(f"An error occurred while setting leverage: {str(e)}. Will use current leverage.")
        else:
            logger.info(f"Leverage is already set to {current_leverage}. No change needed.")

        # Determine order details based on action
        if action in ["Open Long", "Open Short"]:
            # Calculate quantity in BTC (90% of balance with current leverage)
            qty = (balance * 0.9 * current_leverage) / current_price
            qty = round(qty, 3)  # Round to 3 decimal places
            side = "Buy" if action == "Open Long" else "Sell"
        elif action in ["Close Long", "Close Short"]:
            if current_size == 0:
                logger.info("No position to close.")
                return None
            qty = current_size
            side = "Sell" if current_side == "Buy" else "Buy"
        elif action in ["Switch to Long", "Switch to Short"]:
            # First, close the existing position
            if current_size > 0:
                close_position(session, current_side, current_size)
                logger.info(f"Closed existing {current_side} position of size {current_size}")

            # Then, open a new position in the opposite direction
            qty = (balance * 0.9 * current_leverage) / current_price
            qty = round(qty, 3)  # Round to 3 decimal places
            side = "Buy" if action == "Switch to Long" else "Sell"

            # Place the order
        try:
            order_params = {
                "category": "linear",
                "symbol": "BTCUSDT",
                "side": side,
                "orderType": "Market",
                "qty": str(qty),
                "timeInForce": "GoodTillCancel",
                "positionIdx": 0  # 0 for one-way mode
            }

            # Check if we have enough balance for the order
            required_margin = (qty * current_price) / current_leverage
            if required_margin > balance:
                logger.warning(f"Not enough available balance. Required: {required_margin}, Available: {balance}")
                return None

            order = session.place_order(**order_params)

            if order['retCode'] != 0:
                raise Exception(f"Failed to place order: {order['retMsg']}")

            logger.info(f"Order placed successfully: {order['result']}")
            return order['result']

        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            return None

    elif action in ["Maintain Long", "Maintain Short"]:
        if current_size == 0:
            logger.info("No position to maintain.")
            return None

        if (action == "Maintain Long" and current_side != "Buy") or \
                (action == "Maintain Short" and current_side != "Sell"):
            logger.warning(f"Current position ({current_side}) does not match the action ({action}).")
            return None

        logger.info("Maintaining current position. No changes made.")
        return None

    elif action == "Stay Out of the Market":
        logger.info("Staying out of the market. No action taken.")
        return None

    else:
        raise ValueError(f"Invalid action: {action}")


def close_position(session, current_side, current_size):
    close_side = "Sell" if current_side == "Buy" else "Buy"
    try:
        close_order = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side=close_side,
            orderType="Market",
            qty=str(current_size),
            timeInForce="GoodTillCancel",
            positionIdx=0
        )
        if close_order['retCode'] != 0:
            raise Exception(f"Failed to close position: {close_order['retMsg']}")
        logger.info(f"Existing position closed: {close_order['result']}")
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")


def main():
    load_dotenv()
    api_key = os.getenv('BYBIT_API_KEY_1')
    api_secret = os.getenv('BYBIT_API_SECRET_1')

    decision = {
        "action": "Maintain Long",
        "rationale": {
            "technical_analysis": "On the 1D chart, Bitcoin remains in a descending channel with significant resistance at the upper channel line near $58,000. The RSI(1D) stands at 45.19, indicating neutral to mildly bearish momentum, while the MACD is bearish, with the signal line below the MACD line and the histogram showing negative values. The price is trading below both the 50 EMA ($59,683) and the 200 EMA ($59,302), confirming a broader bearish trend. On the 4H chart, Bitcoin recently bounced off the lower boundary of the descending channel but is now facing resistance after failing to break above $57,000, with RSI(4H) at 60.91, indicating short-term overbought conditions. The MACD(4H) is positive but shows signs of weakening momentum as the histogram decreases. This suggests potential exhaustion at this resistance level. Hence, there is an opportunity for a short position as the price struggles at key resistance.",
            "news_impact": "Bitcoin ETF inflows have resumed with $28.7M, but the broader sentiment remains cautious given record losses from crypto scams, with $5.6 billion lost in 2023. Meanwhile, there are no significant immediate catalysts as stated by NYDIG, and while Bitcoin has retaken $57K, potential positive catalysts are sparse. Additionally, a seasonal slowdown in market action has been noted in recent news.",
            "market_sentiment": "The Crypto Fear and Greed Index is at 'Fear' with a value of 33, reflecting market uncertainty. TradingView user sentiment is mixed, though more cautious with short-term trades and predictions forecasting reluctance to break key resistance levels near $57K to $58K. Multiple traders are considering short positions with target levels at $55,000-$56,000.",
            "conclusion": "Considering the technical setup with failed attempts at breaking resistance, briefly overbought conditions on the 4H chart, and mixed market sentiment, opening a short position at current levels around $57,000-$57,500 appears optimal. The target range for this trade is near support at $55,000. The broader bearish trend remains intact, and caution is warranted, but this setup offers a favorable risk-to-reward ratio."
        },
        "confidence_score": 0.78,
    }
    if not api_key or not api_secret:
        logger.error("Error: API key or secret not found in environment variables.")
        return

    execute_bybit_trade(decision, api_key, api_secret, testnet=False)


if __name__ == '__main__':
    main()
