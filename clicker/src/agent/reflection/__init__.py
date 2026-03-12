from typing import Dict, Optional

from .base import BaseReflection
from .claude_35 import Claude35Reflection
from .qwen3_vl import Qwen3VLReflection
from .tars_v15 import TarsV15Reflection


class ReflectionFactory:
    """Factory for creating and managing reflection model instances."""
    
    _instances: Dict[str, BaseReflection] = {}
    
    @classmethod
    def create_reflection_client(cls, model_type: str, inference_ip: Optional[str] = None, **kwargs) -> BaseReflection:
        """
        Create a reflection model instance.
        
        Args:
            model_type: Type of reflection model ("claude_35", "tars_v15")
            inference_ip: full url of the inference server ('http://ip:port' or 'https://ip:port') needed for tars_v15
            **kwargs: Additional arguments
            
        Returns:
            Reflection model instance
        """
        if model_type.lower() == "claude_35":
            instance = Claude35Reflection.create_client(**kwargs)
        elif model_type.lower() == "tars_v15":
            if not inference_ip:
                raise ValueError("inference_ip is required for tars_v15 model")
            instance = TarsV15Reflection.create_client(inference_ip=inference_ip, **kwargs)
        elif model_type.lower() == "qwen3_vl":
            if not inference_ip:
                raise ValueError("inference_ip is required for qwen3_vl model")
            instance = Qwen3VLReflection.create_client(inference_ip=inference_ip, **kwargs)
        else:
            raise ValueError(f"Unsupported reflection model type: {model_type}")
        
        # Store the instance
        cls._instances[model_type.lower()] = instance
        return instance
    
    @classmethod
    def get_reflection_client(cls, model_type: str) -> BaseReflection:
        """Get stored reflection client instance."""
        instance = cls._instances.get(model_type.lower())
        if not instance:
            raise ValueError(f"Reflection client not initialized for model type: {model_type}")
        return instance


async def verify_screenshot(model_type: str, image_path: str, reflection_instruction: str, **kwargs):
    """
    Use specified reflection model to verify screenshot.
    
    Args:
        model_type: Type of reflection model to use (e.g., "claude_35", "tars_v15")
        image_path: Path to the screenshot image
        reflection_instruction: Instruction for verification
        **kwargs: Additional arguments passed to the reflection model
        
    Returns:
        ReflectionResult from the specified model
    """
    try:
        # Try to get existing instance first
        model = ReflectionFactory.get_reflection_client(model_type)
    except ValueError:
        # Fall back to old function-based approach for backward compatibility
        if model_type.lower() == "claude_35":
            from .claude_35 import verify_screenshot as claude_verify
            return claude_verify(image_path, reflection_instruction, **kwargs)
        else:
            raise ValueError(f"Unsupported reflection model type: {model_type}")
    
    return await model.verify_screenshot(image_path, reflection_instruction, **kwargs)


async def verify_two_screenshots(model_type: str, before_image_path: str, after_image_path: str, reflection_instruction: str, use_single_screenshot: bool = False, **kwargs):
    """
    Use specified reflection model to verify two screenshots (before and after).

    Args:
        model_type: Type of reflection model to use (e.g., "claude_35", "tars_v15")
        before_image_path: Path to the 'before' screenshot image
        after_image_path: Path to the 'after' screenshot image
        reflection_instruction: Instruction for verification
        use_single_screenshot: If True, use only the after screenshot (bypass comparison)
        **kwargs: Additional arguments passed to the reflection model

    Returns:
        ReflectionResult from the specified model
    """
    try:
        # Try to get existing instance first
        model = ReflectionFactory.get_reflection_client(model_type)
    except ValueError:
        # For backward compatibility, if model is not available, use single screenshot verification
        if model_type.lower() == "claude_35":
            from .claude_35 import verify_screenshot as claude_verify
            return claude_verify(after_image_path, reflection_instruction, **kwargs)
        else:
            raise ValueError(f"Unsupported reflection model type: {model_type}")

    return await model.verify_two_screenshots(before_image_path, after_image_path, reflection_instruction, use_single_screenshot=use_single_screenshot, **kwargs)


__all__ = ['verify_screenshot', 'verify_two_screenshots', 'ReflectionFactory'] 