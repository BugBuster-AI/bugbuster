from abc import ABC, abstractmethod

from agent.schemas import ReflectionResult


class BaseReflection(ABC):
    """Base class for reflection models."""
    
    def __init__(self, **kwargs):
        """Initialize the reflection model with necessary clients/configs."""
        pass
    
    @abstractmethod
    async def verify_screenshot(self, image_path: str, reflection_instruction: str, **kwargs) -> ReflectionResult:
        """
        Verify screenshot against reflection instruction.

        Args:
            image_path: Path to the screenshot image
            reflection_instruction: Instruction for verification
            **kwargs: Additional arguments (like logger, retries)

        Returns:
            ReflectionResult with verification details
        """
        pass

    @abstractmethod
    async def verify_two_screenshots(self, before_image_path: str, after_image_path: str, reflection_instruction: str, use_single_screenshot: bool = False, **kwargs) -> ReflectionResult:
        """
        Verify two screenshots (before and after) against reflection instruction.

        Args:
            before_image_path: Path to the 'before' screenshot image
            after_image_path: Path to the 'after' screenshot image
            reflection_instruction: Instruction for verification
            use_single_screenshot: If True, use only the after screenshot (bypass comparison)
            **kwargs: Additional arguments (like logger, retries)

        Returns:
            ReflectionResult with verification details
        """
        pass 