import logging
from logging.handlers import RotatingFileHandler
import os


def setup_logger(name=__name__, log_file='trading_bot.log', level=logging.INFO):
    # 로그 디렉토리 생성
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)

    # 로그 파일 경로
    log_file_path = os.path.join(log_directory, log_file)

    # 로거 설정
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 이미 핸들러가 있다면 모두 제거
    if logger.hasHandlers():
        logger.handlers.clear()

    # 파일 핸들러 설정 (RotatingFileHandler 사용)
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setLevel(level)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # 포매터 설정
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 상위 로거로의 전파 방지
    logger.propagate = False

    return logger

# 사용 예:
# logger = setup_logger()
