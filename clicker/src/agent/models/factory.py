from typing import Dict, Type

from .base import BaseModel
from .qwen3_vl import Qwen3VL
from .tars_v1 import TARS_v1
from .tars_v15 import TARS_v15


class ModelFactory:
    """Factory class for creating model instances."""
    
    _model_classes: Dict[str, Type[BaseModel]] = {
        "tars_v1": TARS_v1,
        "tars_v15": TARS_v15,
        "qwen3_vl": Qwen3VL,
        # Add new model implementations here
    }
    
    @classmethod
    def create_model(
        cls,
        model_type: str,
        inference_ip: str
    ) -> BaseModel:
        """
        Create a model instance of the specified type.
        
        Args:
            model_type: Type of model to create (e.g., "tars")
            inference_ip: full url of the inference server ('http://ip:port' or 'https://ip:port')
            
        Returns:
            Instance of the requested model type
            
        Raises:
            ValueError: If the model type is not supported
        """
        model_class = cls._model_classes.get(model_type.lower())
        if not model_class:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        return model_class(inference_ip)
    
    @classmethod
    def register_model(cls, model_type: str, model_class: Type[BaseModel]) -> None:
        """
        Register a new model type.
        
        Args:
            model_type: Type identifier for the model
            model_class: Class implementing the model
        """
        cls._model_classes[model_type.lower()] = model_class 