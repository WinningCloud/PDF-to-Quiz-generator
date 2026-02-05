import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os
import json
from typing import Dict, Any

from config.settings import settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.thread,
            "thread_name": record.threadName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)

class CustomLogger:
    """Custom logger with structured logging"""
    
    @staticmethod
    def setup_logger(
        name: str = "pdf_quiz_platform",
        level: str = None,
        log_to_file: bool = True,
        log_to_console: bool = True
    ) -> logging.Logger:
        """
        Setup and configure logger
        
        Args:
            name: Logger name
            level: Logging level
            log_to_file: Whether to log to file
            log_to_console: Whether to log to console
            
        Returns:
            Configured logger
        """
        # Get log level from settings or default
        if level is None:
            level = settings.LOG_LEVEL
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatters
        json_formatter = JSONFormatter()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # File handler
        if log_to_file:
            # Create logs directory if it doesn't exist
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            # Application log file
            app_log_file = os.path.join(log_dir, "application.log")
            file_handler = RotatingFileHandler(
                app_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(json_formatter)
            logger.addHandler(file_handler)
            
            # Error log file (only errors)
            error_log_file = os.path.join(log_dir, "error.log")
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(json_formatter)
            logger.addHandler(error_handler)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
    
    @staticmethod
    def get_logger(name: str = None) -> logging.Logger:
        """
        Get logger instance
        
        Args:
            name: Logger name (defaults to root)
            
        Returns:
            Logger instance
        """
        if name is None:
            name = "pdf_quiz_platform"
        
        return logging.getLogger(name)
    
    @staticmethod
    def log_with_context(
        logger: logging.Logger,
        level: str,
        message: str,
        context: Dict[str, Any] = None,
        **kwargs
    ):
        """
        Log message with context
        
        Args:
            logger: Logger instance
            level: Log level
            message: Log message
            context: Additional context data
            **kwargs: Additional fields
        """
        log_method = getattr(logger, level.lower(), logger.info)
        
        # Create extra data
        extra = {}
        if context:
            extra.update(context)
        extra.update(kwargs)
        
        # Add extra data to log record
        if extra:
            log_record = logger.makeRecord(
                logger.name,
                getattr(logging, level.upper()),
                "",
                0,
                message,
                (),
                None,
                extra=extra
            )
            logger.handle(log_record)
        else:
            log_method(message)

# Global logger instance
logger = CustomLogger.setup_logger()

# Convenience functions
def get_logger(name: str = None) -> logging.Logger:
    """Get logger instance"""
    return CustomLogger.get_logger(name)

def log_info(message: str, context: Dict[str, Any] = None, **kwargs):
    """Log info message with context"""
    logger = get_logger()
    CustomLogger.log_with_context(logger, "INFO", message, context, **kwargs)

def log_warning(message: str, context: Dict[str, Any] = None, **kwargs):
    """Log warning message with context"""
    logger = get_logger()
    CustomLogger.log_with_context(logger, "WARNING", message, context, **kwargs)

def log_error(message: str, context: Dict[str, Any] = None, **kwargs):
    """Log error message with context"""
    logger = get_logger()
    CustomLogger.log_with_context(logger, "ERROR", message, context, **kwargs)

def log_debug(message: str, context: Dict[str, Any] = None, **kwargs):
    """Log debug message with context"""
    logger = get_logger()
    CustomLogger.log_with_context(logger, "DEBUG", message, context, **kwargs)

def log_exception(message: str, exception: Exception, context: Dict[str, Any] = None, **kwargs):
    """Log exception with context"""
    logger = get_logger()
    
    # Add exception info to context
    if context is None:
        context = {}
    
    context.update({
        "exception_type": type(exception).__name__,
        "exception_message": str(exception)
    })
    
    CustomLogger.log_with_context(logger, "ERROR", message, context, **kwargs)
    logger.exception(message)

# Database logging
def log_db_operation(
    operation: str,
    model: str,
    record_id: int = None,
    user_id: int = None,
    details: Dict[str, Any] = None
):
    """Log database operation"""
    context = {
        "operation": operation,
        "model": model,
        "record_id": record_id,
        "user_id": user_id
    }
    
    if details:
        context["details"] = details
    
    log_info(f"Database {operation} on {model}", context)

# API logging
def log_api_request(
    method: str,
    path: str,
    status_code: int,
    user_id: int = None,
    duration_ms: float = None,
    **kwargs
):
    """Log API request"""
    context = {
        "api_method": method,
        "api_path": path,
        "status_code": status_code,
        "user_id": user_id,
        "duration_ms": duration_ms
    }
    context.update(kwargs)
    
    level = "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR"
    
    logger = get_logger()
    CustomLogger.log_with_context(
        logger,
        level,
        f"API {method} {path} - {status_code}",
        context
    )

# PDF processing logging
def log_pdf_processing(
    pdf_id: int,
    stage: str,
    status: str,
    details: Dict[str, Any] = None,
    **kwargs
):
    """Log PDF processing event"""
    context = {
        "pdf_id": pdf_id,
        "processing_stage": stage,
        "processing_status": status
    }
    
    if details:
        context.update(details)
    context.update(kwargs)
    
    log_info(f"PDF processing {stage} - {status}", context)

# Quiz generation logging
def log_quiz_generation(
    quiz_id: int,
    stage: str,
    status: str,
    details: Dict[str, Any] = None,
    **kwargs
):
    """Log quiz generation event"""
    context = {
        "quiz_id": quiz_id,
        "generation_stage": stage,
        "generation_status": status
    }
    
    if details:
        context.update(details)
    context.update(kwargs)
    
    log_info(f"Quiz generation {stage} - {status}", context)