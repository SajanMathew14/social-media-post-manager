"""
Langfuse client for LLM observability
"""
from typing import Optional, Dict, Any
from langfuse import Langfuse
from langfuse.callback import CallbackHandler
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LangfuseClient:
    """Langfuse client for LLM observability"""
    
    def __init__(self):
        self._client: Optional[Langfuse] = None
        self._callback_handler: Optional[CallbackHandler] = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Langfuse client if credentials are provided"""
        try:
            if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
                self._client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                
                self._callback_handler = CallbackHandler(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST
                )
                
                logger.info("Langfuse client initialized successfully")
            else:
                logger.info("Langfuse credentials not provided, observability disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse client: {e}")
            self._client = None
            self._callback_handler = None
    
    @property
    def is_enabled(self) -> bool:
        """Check if Langfuse is enabled and properly configured"""
        return self._client is not None
    
    @property
    def callback_handler(self) -> Optional[CallbackHandler]:
        """Get the callback handler for LangChain integration"""
        return self._callback_handler
    
    def create_trace(self, name: str, user_id: Optional[str] = None, 
                    session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Create a new trace for tracking LLM operations"""
        if not self.is_enabled:
            return None
        
        try:
            return self._client.trace(
                name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to create Langfuse trace: {e}")
            return None
    
    def create_generation(self, trace_id: str, name: str, model: str, 
                         input_data: Any, output_data: Any, metadata: Optional[Dict[str, Any]] = None):
        """Create a generation event for LLM calls"""
        if not self.is_enabled:
            return None
        
        try:
            return self._client.generation(
                trace_id=trace_id,
                name=name,
                model=model,
                input=input_data,
                output=output_data,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Failed to create Langfuse generation: {e}")
            return None
    
    def flush(self):
        """Flush pending events to Langfuse"""
        if self.is_enabled:
            try:
                self._client.flush()
            except Exception as e:
                logger.error(f"Failed to flush Langfuse events: {e}")


# Global Langfuse client instance
langfuse_client = LangfuseClient()
