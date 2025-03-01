"""
Model switching mechanism for Home Assistant Agent.
Handles dynamic selection between local Ollama models and cloud Anthropic models.
"""
from typing import Literal, Optional, Union, Any
from crewai import LLM
from loguru import logger


class ModelSwitcher:
    """
    Class for dynamically switching between local and cloud-based AI models
    based on task complexity, latency requirements, and other factors.
    """
    
    def __init__(
        self, 
        local_model: LLM, 
        cloud_model: LLM,
        default_to_local: bool = True
    ):
        """
        Initialize the ModelSwitcher.
        
        Args:
            local_model: An initialized LLM instance for local model (e.g., Ollama)
            cloud_model: An initialized LLM instance for cloud model (e.g., Anthropic)
            default_to_local: Whether to default to local model when requirements are ambiguous
        """
        self.local_model = local_model
        self.cloud_model = cloud_model
        self.current_model = local_model if default_to_local else cloud_model
        self.default_to_local = default_to_local
        
        # Log initial setup
        logger.info(
            f"ModelSwitcher initialized with default model: "
            f"{'local' if default_to_local else 'cloud'}"
        )
    
    def select_model(
        self, 
        task_complexity: int = 5, 
        latency_sensitive: bool = False, 
        force_model: Optional[Literal["local", "cloud"]] = None
    ) -> LLM:
        """
        Select appropriate model based on task requirements.
        
        Args:
            task_complexity: Int from 1-10 indicating complexity (1=simplest, 10=most complex)
            latency_sensitive: Bool indicating if task needs fast response
            force_model: "local" or "cloud" to override automatic selection
            
        Returns:
            Selected model instance (either local_model or cloud_model)
        """
        # Force specific model if requested
        if force_model == "local":
            logger.debug("Forcing selection of local model")
            self.current_model = self.local_model
            return self.local_model
        
        if force_model == "cloud":
            logger.debug("Forcing selection of cloud model")
            self.current_model = self.cloud_model
            return self.cloud_model
        
        # Validate task_complexity
        if not 1 <= task_complexity <= 10:
            logger.warning(f"Invalid task complexity: {task_complexity}. Using default value of 5.")
            task_complexity = 5
        
        # Automatic selection based on task requirements
        if task_complexity > 7 and not latency_sensitive:
            # Complex tasks use cloud model for better quality
            logger.debug(
                f"Selected cloud model based on high complexity ({task_complexity}) "
                f"and no latency sensitivity"
            )
            self.current_model = self.cloud_model
        elif latency_sensitive or task_complexity < 5:
            # Time-sensitive or simple tasks use local model
            logger.debug(
                f"Selected local model based on {'latency sensitivity' if latency_sensitive else 'low complexity'}"
            )
            self.current_model = self.local_model
        else:
            # Medium complexity, non-latency-sensitive tasks
            # Default to configured preference
            default_model = self.local_model if self.default_to_local else self.cloud_model
            model_type = "local" if self.default_to_local else "cloud"
            logger.debug(f"Selected {model_type} model based on default preference")
            self.current_model = default_model
            
        return self.current_model
    
    def get_current_model(self) -> LLM:
        """Get the currently selected model"""
        return self.current_model
    
    def get_model_type(self) -> str:
        """Get the type of currently selected model (local or cloud)"""
        return "local" if self.current_model == self.local_model else "cloud"
    
    def force_local(self) -> LLM:
        """Force selection of local model"""
        return self.select_model(force_model="local")
    
    def force_cloud(self) -> LLM:
        """Force selection of cloud model"""
        return self.select_model(force_model="cloud") 