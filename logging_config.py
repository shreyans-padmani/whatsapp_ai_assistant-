import logging
from datetime import timezone, timedelta
from typing import Optional

# --- CUSTOM LOGGING HELPER ---
class RequestLogger:
    """Scalable logger that accepts message_id as parameter for multi-worker support"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
        self.ist = timezone(timedelta(hours=5, minutes=30))
    
    def _format_log(self, message: str, message_id: str = "SYSTEM") -> str:
        """Format log with IST timestamp, message_id, and line number"""
        from datetime import datetime
        ist_time = datetime.now(self.ist).strftime("%Y-%m-%d %H:%M:%S")
        return f"{ist_time} - {message_id} - {message}"
    
    def info(self, message_or_id: str, message: Optional[str] = None):
        """Log info level - supports both info(msg_id, msg) and info(msg) formats"""
        if message is None:
            self.logger.info(self._format_log(message_or_id))
        else:
            self.logger.info(self._format_log(message, message_or_id))
    
    def error(self, message_or_id: str, message: Optional[str] = None):
        """Log error level - supports both error(msg_id, msg) and error(msg) formats"""
        if message is None:
            self.logger.error(self._format_log(message_or_id))
        else:
            self.logger.error(self._format_log(message, message_or_id))
    
    def warning(self, message_or_id: str, message: Optional[str] = None):
        """Log warning level - supports both warning(msg_id, msg) and warning(msg) formats"""
        if message is None:
            self.logger.warning(self._format_log(message_or_id))
        else:
            self.logger.warning(self._format_log(message, message_or_id))
    
    def debug(self, message_or_id: str, message: Optional[str] = None):
        """Log debug level - supports both debug(msg_id, msg) and debug(msg) formats"""
        if message is None:
            self.logger.debug(self._format_log(message_or_id))
        else:
            self.logger.debug(self._format_log(message, message_or_id))

def setup_logging():
    """Configure logging with IST timezone support"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    return RequestLogger("API")

# --- GLOBAL LOGGER INSTANCE ---
request_logger = setup_logging()