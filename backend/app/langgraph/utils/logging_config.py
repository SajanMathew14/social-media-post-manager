"""
Structured logging configuration for LangGraph nodes
"""
import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'session_id'):
            log_data["session_id"] = record.session_id
        if hasattr(record, 'workflow_id'):
            log_data["workflow_id"] = record.workflow_id
        if hasattr(record, 'node_name'):
            log_data["node_name"] = record.node_name
        if hasattr(record, 'step'):
            log_data["step"] = record.step
        if hasattr(record, 'duration'):
            log_data["duration"] = record.duration
        if hasattr(record, 'error_type'):
            log_data["error_type"] = record.error_type
            
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logger for LangGraph nodes following best practices.
    
    Provides consistent logging interface with structured output
    for easy parsing and analysis.
    """
    
    def __init__(self, node_name: str):
        """
        Initialize structured logger for a specific node.
        
        Args:
            node_name: Name of the LangGraph node
        """
        self.node_name = node_name
        self.logger = logging.getLogger(f"langgraph.{node_name}")
        
    def log_node_entry(
        self, 
        session_id: str, 
        workflow_id: str, 
        step: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log node entry with context.
        
        Args:
            session_id: User session identifier
            workflow_id: Workflow execution identifier
            step: Current processing step
            extra_data: Additional data to log
        """
        self.logger.info(
            f"Entering node: {self.node_name}",
            extra={
                "session_id": session_id,
                "workflow_id": workflow_id,
                "node_name": self.node_name,
                "step": step,
                "event": "node_entry",
                **(extra_data or {})
            }
        )
    
    def log_node_exit(
        self, 
        session_id: str, 
        workflow_id: str, 
        step: str,
        success: bool,
        duration: Optional[float] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log node exit with results.
        
        Args:
            session_id: User session identifier
            workflow_id: Workflow execution identifier
            step: Processing step that completed
            success: Whether the node completed successfully
            duration: Processing duration in seconds
            extra_data: Additional data to log
        """
        level = logging.INFO if success else logging.ERROR
        message = f"Exiting node: {self.node_name} - {'SUCCESS' if success else 'FAILURE'}"
        
        extra = {
            "session_id": session_id,
            "workflow_id": workflow_id,
            "node_name": self.node_name,
            "step": step,
            "event": "node_exit",
            "success": success,
            **(extra_data or {})
        }
        
        if duration is not None:
            extra["duration"] = duration
            
        self.logger.log(level, message, extra=extra)
    
    def log_processing_step(
        self,
        session_id: str,
        workflow_id: str,
        step: str,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a processing step within the node.
        
        Args:
            session_id: User session identifier
            workflow_id: Workflow execution identifier
            step: Current processing step
            message: Step description
            extra_data: Additional data to log
        """
        self.logger.info(
            message,
            extra={
                "session_id": session_id,
                "workflow_id": workflow_id,
                "node_name": self.node_name,
                "step": step,
                "event": "processing_step",
                **(extra_data or {})
            }
        )
    
    def log_error(
        self,
        session_id: str,
        workflow_id: str,
        step: str,
        error: Exception,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with full context.
        
        Args:
            session_id: User session identifier
            workflow_id: Workflow execution identifier
            step: Step where error occurred
            error: Exception that occurred
            extra_data: Additional data to log
        """
        self.logger.error(
            f"Error in {self.node_name}: {str(error)}",
            extra={
                "session_id": session_id,
                "workflow_id": workflow_id,
                "node_name": self.node_name,
                "step": step,
                "event": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                **(extra_data or {})
            },
            exc_info=True
        )
    
    def log_api_call(
        self,
        session_id: str,
        workflow_id: str,
        api_name: str,
        method: str,
        url: str,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log external API calls.
        
        Args:
            session_id: User session identifier
            workflow_id: Workflow execution identifier
            api_name: Name of the API being called
            method: HTTP method
            url: API endpoint URL
            status_code: HTTP response status code
            duration: Request duration in seconds
            extra_data: Additional data to log
        """
        message = f"API call to {api_name}: {method} {url}"
        if status_code:
            message += f" -> {status_code}"
            
        extra = {
            "session_id": session_id,
            "workflow_id": workflow_id,
            "node_name": self.node_name,
            "event": "api_call",
            "api_name": api_name,
            "method": method,
            "url": url,
            **(extra_data or {})
        }
        
        if status_code is not None:
            extra["status_code"] = status_code
        if duration is not None:
            extra["duration"] = duration
            
        level = logging.INFO if not status_code or status_code < 400 else logging.WARNING
        self.logger.log(level, message, extra=extra)


def setup_logging() -> None:
    """
    Setup structured logging configuration for the application.
    
    Configures root logger with structured JSON formatter and
    appropriate log levels based on settings.
    """
    # Get log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    if settings.LOG_FORMAT.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    logging.getLogger("langgraph").setLevel(log_level)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info("Structured logging configured successfully", extra={
        "log_level": settings.LOG_LEVEL,
        "log_format": settings.LOG_FORMAT
    })
