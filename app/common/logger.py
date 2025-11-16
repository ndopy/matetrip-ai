import sys
from loguru import logger

logger.remove()  # 기본 stderr 핸들러 제거

# 콘솔 출력 핸들러 추가
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan> - {message}",
    level="INFO",
)

# 파일 출력 핸들러 추가
logger.add(
    "app.log",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan> - {message}",
    level="INFO",
    rotation="10 MB",
    retention="7 days",
)
