from loguru import logger


logger = logger
# Configure logging
logger.add(
    "app.log",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan> - {message}",
    level="INFO",
    rotation="10 MB",
    retention="7 days",
)
