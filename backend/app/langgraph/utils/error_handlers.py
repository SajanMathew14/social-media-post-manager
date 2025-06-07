"""
Custom exception classes and error handling utilities for LangGraph nodes
"""
from typing import Optional, Dict, Any
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NewsProcessingError(Exception):
    """
    Base exception for news processing errors.
    
    All custom exceptions in the news processing workflow
    should inherit from this base class.
    """
    
    def __init__(
        self, 
        message: str, 
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize news processing error.
        
        Args:
            message: Human-readable error message
            severity: Error severity level
            error_code: Machine-readable error code
            context: Additional context about the error
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "context": self.context
        }


class ValidationError(NewsProcessingError):
    """Raised when input validation fails"""
    
    def __init__(self, field: str, value: Any, reason: str):
        message = f"Validation failed for field '{field}' with value '{value}': {reason}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            error_code="VALIDATION_ERROR",
            context={"field": field, "value": str(value), "reason": reason}
        )


class QuotaExceededError(NewsProcessingError):
    """Raised when user quota is exceeded"""
    
    def __init__(self, quota_type: str, used: int, limit: int):
        message = f"{quota_type} quota exceeded: {used}/{limit}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            error_code="QUOTA_EXCEEDED",
            context={
                "quota_type": quota_type,
                "used": used,
                "limit": limit
            }
        )


class DuplicateRequestError(NewsProcessingError):
    """Raised when a duplicate request is detected"""
    
    def __init__(self, request_hash: str, original_timestamp: str):
        message = f"Duplicate request detected (hash: {request_hash})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            error_code="DUPLICATE_REQUEST",
            context={
                "request_hash": request_hash,
                "original_timestamp": original_timestamp
            }
        )


class SerperAPIError(NewsProcessingError):
    """Raised when Serper API calls fail"""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        super().__init__(
            message=f"Serper API error: {message}",
            severity=ErrorSeverity.HIGH,
            error_code="SERPER_API_ERROR",
            context={
                "status_code": status_code,
                "response_body": response_body
            }
        )


class LLMProviderError(NewsProcessingError):
    """Raised when LLM provider calls fail"""
    
    def __init__(
        self, 
        provider: str, 
        original_error: str,
        error_type: Optional[str] = None
    ):
        message = f"LLM Provider {provider} failed: {original_error}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.HIGH,
            error_code="LLM_PROVIDER_ERROR",
            context={
                "provider": provider,
                "original_error": original_error,
                "error_type": error_type
            }
        )


class DatabaseError(NewsProcessingError):
    """Raised when database operations fail"""
    
    def __init__(self, operation: str, original_error: str):
        message = f"Database {operation} failed: {original_error}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,
            error_code="DATABASE_ERROR",
            context={
                "operation": operation,
                "original_error": original_error
            }
        )


class TopicConfigError(NewsProcessingError):
    """Raised when topic configuration is invalid or missing"""
    
    def __init__(self, topic: str, reason: str):
        message = f"Topic configuration error for '{topic}': {reason}"
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            error_code="TOPIC_CONFIG_ERROR",
            context={
                "topic": topic,
                "reason": reason
            }
        )


class ContentFilteringError(NewsProcessingError):
    """Raised when content filtering fails"""
    
    def __init__(self, reason: str, articles_count: int):
        message = f"Content filtering failed: {reason} (articles: {articles_count})"
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            error_code="CONTENT_FILTERING_ERROR",
            context={
                "reason": reason,
                "articles_count": articles_count
            }
        )


class RetryableError(NewsProcessingError):
    """
    Base class for errors that can be retried.
    
    Nodes can catch this exception type and implement
    retry logic with exponential backoff.
    """
    
    def __init__(
        self, 
        message: str, 
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay


class NonRetryableError(NewsProcessingError):
    """
    Base class for errors that should not be retried.
    
    These are typically validation errors or quota
    exceeded errors that won't resolve with retries.
    """
    pass


# Utility functions for error handling

def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error can be retried, False otherwise
    """
    if isinstance(error, RetryableError):
        return True
    if isinstance(error, NonRetryableError):
        return False
    if isinstance(error, (ValidationError, QuotaExceededError, DuplicateRequestError)):
        return False
    if isinstance(error, (SerperAPIError, LLMProviderError)):
        return True
    
    # Default to non-retryable for unknown errors
    return False


def get_error_severity(error: Exception) -> ErrorSeverity:
    """
    Get error severity level.
    
    Args:
        error: Exception to analyze
        
    Returns:
        Error severity level
    """
    if isinstance(error, NewsProcessingError):
        return error.severity
    
    # Default severity for unknown errors
    return ErrorSeverity.MEDIUM


def create_error_context(
    session_id: str,
    workflow_id: str,
    node_name: str,
    step: str,
    error: Exception
) -> Dict[str, Any]:
    """
    Create comprehensive error context for logging.
    
    Args:
        session_id: User session identifier
        workflow_id: Workflow execution identifier
        node_name: Name of the node where error occurred
        step: Processing step where error occurred
        error: Exception that occurred
        
    Returns:
        Error context dictionary
    """
    context = {
        "session_id": session_id,
        "workflow_id": workflow_id,
        "node_name": node_name,
        "step": step,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "severity": get_error_severity(error).value,
        "retryable": is_retryable_error(error)
    }
    
    # Add custom error context if available
    if isinstance(error, NewsProcessingError):
        context.update(error.context)
        context["error_code"] = error.error_code
    
    return context


def handle_node_error(
    error: Exception,
    session_id: str,
    workflow_id: str,
    node_name: str,
    step: str
) -> NewsProcessingError:
    """
    Convert any exception to a NewsProcessingError with context.
    
    Args:
        error: Original exception
        session_id: User session identifier
        workflow_id: Workflow execution identifier
        node_name: Name of the node where error occurred
        step: Processing step where error occurred
        
    Returns:
        NewsProcessingError with full context
    """
    if isinstance(error, NewsProcessingError):
        # Already a custom error, just add context
        error.context.update({
            "session_id": session_id,
            "workflow_id": workflow_id,
            "node_name": node_name,
            "step": step
        })
        return error
    
    # Convert generic exception to custom error
    return NewsProcessingError(
        message=f"Unexpected error in {node_name}: {str(error)}",
        severity=ErrorSeverity.HIGH,
        error_code="UNEXPECTED_ERROR",
        context=create_error_context(session_id, workflow_id, node_name, step, error)
    )
