"""
Base Stub Class

Abstract base class for all API stubs.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class StubResponse:
    """Standard response from stub methods."""
    success: bool
    data: Any
    message: str = ""
    error: Optional[str] = None


class BaseStub(ABC):
    """
    Abstract base class for API stubs.
    
    All stub implementations should inherit from this class
    and implement the required abstract methods.
    """
    
    name: str = "base_stub"
    description: str = "Base stub class"
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self._setup_seed()
    
    def _setup_seed(self):
        import random
        import numpy as np
        random.seed(self.seed)
        np.random.seed(self.seed)
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if stub is available (always True for stubs)."""
        pass
    
    @abstractmethod
    def get_mock_data(self, *args, **kwargs) -> Any:
        """Generate mock data for the stub."""
        pass
    
    def log_stub_call(self, method: str, params: Dict[str, Any] = None):
        """Log stub method call for debugging."""
        logger.info(f"[STUB] {self.name}.{method} called with params: {params}")
    
    def to_dict(self) -> Dict[str, str]:
        """Return stub metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "type": "stub",
        }
