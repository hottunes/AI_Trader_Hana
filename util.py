import json

from logger_setup import setup_logger

logger = setup_logger(__name__)


def get_instructions(file_path):
    """Read instructions from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print("File not found.")
    except Exception as e:
        print("An error occurred while reading the file:", e)


def log_messages(messages):
    """Log messages content to a file."""
    with open('messages_log.json', 'w') as f:
        json.dump(messages, f, indent=2)

    logger.info(f"Messages content logged to messages_log.json")
    logger.info(f"Number of messages: {len(messages)}")
