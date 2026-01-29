import logging
from datetime import datetime
from pathlib import Path
from src.config.settings import LOG_DIR

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)


class RotatingFileHandler(logging.Handler):
    """Custom handler for weekly log rotation"""

    def __init__(self, filename, when='W0'):
        super().__init__()
        self.filename = filename
        self.when = when

    def emit(self, record):
        # Check if we need to rotate (simplified version)
        log_file = Path(self.filename)
        if log_file.exists():
            # Check if it's Monday (start of week)
            if datetime.now().weekday() == 0:
                # Archive old log
                timestamp = datetime.now().strftime('%Y%m%d')
                archive_file = log_file.parent / f"{log_file.stem}_{timestamp}{log_file.suffix}"
                if archive_file.exists():
                    archive_file.unlink()
                log_file.rename(archive_file)

        # Write to log file
        with open(self.filename, 'a') as f:
            f.write(self.format(record) + '\n')


def setup_logger(name: str, log_file: str, level=logging.INFO):
    """Setup a logger with file and console handlers"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with weekly rotation
    file_handler = RotatingFileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Initialize loggers
error_logger = setup_logger('error', LOG_DIR / 'error.log', logging.ERROR)
user_logger = setup_logger('user', LOG_DIR / 'user.log', logging.INFO)
app_logger = setup_logger('app', LOG_DIR / 'app.log', logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger by name"""
    return logging.getLogger(name)


def log_user_action(action: str, details: dict = None):
    """Log user actions"""
    message = f"USER ACTION: {action}"
    if details:
        message += f" - Details: {details}"
    user_logger.info(message)


def log_error(error: Exception, context: str = ""):
    """Log errors with context"""
    error_msg = f"ERROR{': ' + context if context else ''}: {str(error)}"
    error_logger.error(error_msg, exc_info=True)


def log_app_info(message: str):
    """Log application info"""
    app_logger.info(message)