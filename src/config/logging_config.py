import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from src.config.settings import LOG_DIR


def setup_loggers():
    """Setup application loggers"""

    # Ensure log directory exists
    LOG_DIR.mkdir(exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Error logger
    error_logger = logging.getLogger('error')
    error_logger.setLevel(logging.ERROR)
    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / 'error.log',
        when='W0',  # Weekly on Monday
        backupCount=4
    )
    error_handler.setFormatter(formatter)
    error_logger.addHandler(error_handler)

    # User action logger
    user_logger = logging.getLogger('user')
    user_logger.setLevel(logging.INFO)
    user_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / 'user.log',
        when='W0',
        backupCount=4
    )
    user_handler.setFormatter(formatter)
    user_logger.addHandler(user_handler)

    # Application logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    app_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / 'app.log',
        when='W0',
        backupCount=4
    )
    app_handler.setFormatter(formatter)
    app_logger.addHandler(app_handler)

    return {
        'error': error_logger,
        'user': user_logger,
        'app': app_logger
    }


loggers = setup_loggers()