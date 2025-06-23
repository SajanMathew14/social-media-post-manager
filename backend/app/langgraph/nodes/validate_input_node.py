"""
Input validation node for news processing workflow.

This node follows LangGraph best practices:
- Single responsibility: Input validation only
- Comprehensive logging with structured output
- Robust error handling with custom exceptions
- Immutable state updates
- Clear documentation
"""
import time
from datetime import datetime
from typing import Dict, Any

from app.langgraph.state.news_state import NewsState, ProcessingStatus, mark_step_completed, mark_step_error
from app.langgraph.utils.logging_config import StructuredLogger
from app.langgraph.utils.error_handlers import (
    ValidationError, 
    handle_node_error,
    NonRetryableError
)
from app.core.config import settings


class ValidateInputNode:
    """
    Validates input parameters for news processing workflow.
    
    Responsibilities:
    - Validate topic format and content
    - Validate date format and range
    - Validate top_n parameter bounds
    - Validate LLM model selection
    - Validate session_id format
    
    This node implements comprehensive validation to catch
    issues early in the workflow before expensive API calls.
    """
    
    def __init__(self):
        """Initialize validation node with structured logger."""
        self.logger = StructuredLogger("validate_input")
        self.node_name = "validate_input"
    
    async def __call__(self, state: NewsState) -> NewsState:
        """
        Execute input validation.
        
        Args:
            state: Current workflow state containing input parameters
            
        Returns:
            Updated state with validation results
            
        Raises:
            ValidationError: When input validation fails
        """
        start_time = time.time()
        
        # Log node entry
        self.logger.log_node_entry(
            session_id=state["session_id"],
            workflow_id=state["workflow_id"],
            step="input_validation",
            extra_data={
                "topic": state["topic"],
                "date": state["date"],
                "top_n": state["top_n"],
                "llm_model": state["llm_model"]
            }
        )
        
        try:
            # Update state to show current processing step
            new_state = state.copy()
            new_state["current_step"] = "Validating input parameters"
            
            # Perform all validations
            validation_errors = []
            
            # Validate topic
            topic_errors = self._validate_topic(state["topic"])
            validation_errors.extend(topic_errors)
            
            # Validate date
            date_errors = self._validate_date(state["date"])
            validation_errors.extend(date_errors)
            
            # Validate top_n
            top_n_errors = self._validate_top_n(state["top_n"])
            validation_errors.extend(top_n_errors)
            
            # Validate LLM model
            llm_errors = self._validate_llm_model(state["llm_model"])
            validation_errors.extend(llm_errors)
            
            # Validate session ID
            session_errors = self._validate_session_id(state["session_id"])
            validation_errors.extend(session_errors)
            
            # Check if any validation errors occurred
            if validation_errors:
                error_message = f"Input validation failed: {'; '.join(validation_errors)}"
                
                # Log validation errors
                self.logger.log_error(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="input_validation",
                    error=ValidationError("multiple_fields", "various", error_message),
                    extra_data={"validation_errors": validation_errors}
                )
                
                # Update state with errors
                new_state["validation_errors"] = validation_errors
                error_state = mark_step_error(new_state, "input_validation", error_message)
                
                # Log node exit with failure
                duration = time.time() - start_time
                self.logger.log_node_exit(
                    session_id=state["session_id"],
                    workflow_id=state["workflow_id"],
                    step="input_validation",
                    success=False,
                    duration=duration,
                    extra_data={"validation_errors": validation_errors}
                )
                
                raise ValidationError("input_validation", "multiple", error_message)
            
            # All validations passed
            self.logger.log_processing_step(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="input_validation",
                message="All input parameters validated successfully"
            )
            
            # Mark validation as completed
            completed_state = mark_step_completed(
                new_state, 
                "input_validation", 
                "Input parameters validated successfully"
            )
            
            # Log successful completion
            duration = time.time() - start_time
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="input_validation",
                success=True,
                duration=duration,
                extra_data={"validation_passed": True}
            )
            
            return completed_state
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Handle unexpected errors
            duration = time.time() - start_time
            
            # Convert to custom error with context
            custom_error = handle_node_error(
                error=e,
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                node_name=self.node_name,
                step="input_validation"
            )
            
            # Log the error
            self.logger.log_error(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="input_validation",
                error=custom_error
            )
            
            # Log node exit with failure
            self.logger.log_node_exit(
                session_id=state["session_id"],
                workflow_id=state["workflow_id"],
                step="input_validation",
                success=False,
                duration=duration
            )
            
            raise custom_error
    
    def _validate_topic(self, topic: str) -> list[str]:
        """
        Validate topic parameter.
        
        Args:
            topic: Topic string to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not topic:
            errors.append("Topic is required")
            return errors
        
        if not isinstance(topic, str):
            errors.append("Topic must be a string")
            return errors
        
        topic = topic.strip()
        
        if len(topic) < 2:
            errors.append("Topic must be at least 2 characters long")
        
        if len(topic) > 100:
            errors.append("Topic must be less than 100 characters")
        
        # Check for potentially harmful content
        forbidden_chars = ['<', '>', '"', "'", '&', ';']
        if any(char in topic for char in forbidden_chars):
            errors.append("Topic contains forbidden characters")
        
        return errors
    
    def _validate_date(self, date: str) -> list[str]:
        """
        Validate date parameter.
        
        Args:
            date: Date string to validate (YYYY-MM-DD format)
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not date:
            errors.append("Date is required")
            return errors
        
        if not isinstance(date, str):
            errors.append("Date must be a string")
            return errors
        
        # Validate date format
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            errors.append("Date must be in YYYY-MM-DD format")
            return errors
        
        # Check if date is not in the future
        today = datetime.now().date()
        if parsed_date.date() > today:
            errors.append("Date cannot be in the future")
        
        # Check if date is not too old (e.g., more than 1 year ago)
        days_ago = (today - parsed_date.date()).days
        if days_ago > 365:
            errors.append("Date cannot be more than 1 year ago")
        
        return errors
    
    def _validate_top_n(self, top_n: int) -> list[str]:
        """
        Validate top_n parameter.
        
        Args:
            top_n: Number of articles to fetch
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if top_n is None:
            errors.append("Top N is required")
            return errors
        
        if not isinstance(top_n, int):
            errors.append("Top N must be an integer")
            return errors
        
        if top_n < 1:
            errors.append("Top N must be at least 1")
        
        if top_n > settings.MAX_NEWS_ARTICLES:
            errors.append(f"Top N cannot exceed {settings.MAX_NEWS_ARTICLES}")
        
        return errors
    
    def _validate_llm_model(self, llm_model: str) -> list[str]:
        """
        Validate LLM model parameter.
        
        Args:
            llm_model: LLM model identifier
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not llm_model:
            errors.append("LLM model is required")
            return errors
        
        if not isinstance(llm_model, str):
            errors.append("LLM model must be a string")
            return errors
        
        # Valid LLM models
        valid_models = ["claude-3-5-sonnet", "gpt-4-turbo", "gemini-pro"]
        
        if llm_model not in valid_models:
            errors.append(f"LLM model must be one of: {', '.join(valid_models)}")
        
        return errors
    
    def _validate_session_id(self, session_id: str) -> list[str]:
        """
        Validate session ID parameter.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        if not session_id:
            errors.append("Session ID is required")
            return errors
        
        if not isinstance(session_id, str):
            errors.append("Session ID must be a string")
            return errors
        
        # Basic UUID format validation
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        if not uuid_pattern.match(session_id):
            errors.append("Session ID must be a valid UUID")
        
        return errors
