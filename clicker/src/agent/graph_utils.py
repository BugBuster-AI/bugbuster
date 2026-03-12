import asyncio
import re
import shutil
from pathlib import Path

from core.celeryconfig import logger


async def clean_up_directories(screenshot_base_path, trace_file_path):
    """
    Clean up temporary files and directories created during the agent's execution.
    
    Args:
        screenshot_base_path (Path): Path to the directory containing screenshots
        trace_file_path (str): Path to the trace file
        
    Returns:
        None
    """
    # Remove screenshots
    if screenshot_base_path.exists() and screenshot_base_path.is_dir():
        try:
            await asyncio.to_thread(shutil.rmtree, screenshot_base_path)
            logger.info("Screenshot directory cleaned up")
        except Exception as e:
            logger.error(f"Error removing screenshot directory {screenshot_base_path}: {e}")
    # Remove trace file
    trace_path = Path(trace_file_path)
    if trace_path.exists():
        try:
            await asyncio.to_thread(trace_path.unlink)
            logger.info("Trace file cleaned up")
        except Exception as e:
            logger.error(f"Error deleting trace file {trace_file_path}: {e}")

    # Remove extracted trace file for video
    zip_extract_file = Path(trace_file_path.replace('.zip', ''))
    if zip_extract_file.exists() and zip_extract_file.is_dir():
        try:
            await asyncio.to_thread(shutil.rmtree, zip_extract_file)
            logger.info("Video directory cleaned up")
        except Exception as e:
            logger.error(f"Error removing video directory {zip_extract_file}: {e}")


def extract_number_from_response(response):
    """
    Extract the first numeric value from a string response.
    Used for post-processing of the response of detection inference.
    
    Args:
        response (str): The string response to extract a number from
        
    Returns:
        str: The first numeric value found in the response, or '0' if no numbers are found
    """
    if response:
        digits = re.findall(r'\d+', response)
        if digits:
            response = digits[0]
        else:
            response = '0'
    else:
        response = '0'
    return response


def check_annotated_screenshot_exists(image_path, before_screenshot_path, logger):
    """
    Check if an image file exists at the given path. If not, replace it with the before screenshot path
    
    Args:
        image_path (str or Path): Path to the image file to check
        before_screenshot_path (str or Path): Path to the before screenshot to use as fallback
        logger: Logger instance for logging messages
        
    Returns:
        Path: Path to the image file that exists (either the original or the fallback)
    """
    if image_path is None:
        return False
    
    # Convert to Path object if it's a string
    if isinstance(image_path, str):
        image_path = Path(image_path)
    
    if image_path.exists() and image_path.is_file():
        return image_path
    else:
        logger.info(f"Annotated screenshot {image_path} does not exist, replacing with before screenshot {before_screenshot_path}")
        return before_screenshot_path


def check_screenshot_exists(image_path) -> bool:
    if image_path is None:
        return False
    if isinstance(image_path, str):
        image_path = Path(image_path)
    if image_path.exists() and image_path.is_file():
        return True
    return False
