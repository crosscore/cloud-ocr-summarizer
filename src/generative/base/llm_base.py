from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMBase(ABC):
    """Base class for LLM processors"""

    @abstractmethod
    def get_summary(self, ocr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate summary from OCR data

        Args:
            ocr_data: Dictionary containing OCR results

        Returns:
            Dictionary containing summaries and metadata
        """
        pass
