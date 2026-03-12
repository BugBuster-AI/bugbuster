from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from langfuse.langchain import CallbackHandler


class BaseModel(ABC):
    """Abstract base class for all model implementations."""
    
    @abstractmethod
    async def get_coordinates(
        self,
        image_path: str,
        task: str,
        langfuse_handler: CallbackHandler,
        is_base64: bool,
        context_screenshot_image_path: str = None,
        context_screenshot_is_base64: bool = False
    ) -> Tuple[int, int]:
        """
        Get coordinates for an element in an image.
        
        Args:
            image_path: Path to the image file
            task: Instruction for the model
            langfuse_handler: Langfuse callback handler
            
        Returns:
            Tuple of (x, y) coordinates
        """
        pass
    
    @abstractmethod
    async def get_scroll_scores(
        self,
        image_path: str,
        element_description: str,
        langfuse_handler: CallbackHandler,
        crop_len: int = 900,
        crops: Optional[List[str]] = None
    ) -> List[int]:
        """
        Detect elements in a scrollable area.
        
        Args:
            image_path: Path to the image file
            element_description: Description of the element to detect
            langfuse_handler: Langfuse callback handler
            crop_len: Length of each crop
            crops: Optional list of pre-cropped images
            
        Returns:
            List of confidence scores for each crop
        """
        pass 