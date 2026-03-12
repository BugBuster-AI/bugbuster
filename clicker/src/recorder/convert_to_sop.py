import asyncio
import base64
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from core.config import logger
from llm_controller import LLMProvider, create_llm_service
from recorder.prompt import prompt__td_kf_act_intro


class StepReasoningSchema(BaseModel):
    thoughts: str = Field(
        ...,
        description="Elements interacted with",
        max_length=100
    )
    observation: str = Field(
        ...,
        description="Conditions check",
        max_length=50
    )
    instructions: list[str] = Field(
        default=[],
        description=(
            "Describe the actions that need to be repeated to achieve the same result as the user. Answer in the requested language! Return an empty list if the step should be skipped."
        )
    )


class OptimizedStepsSchema(BaseModel):
    optimized_steps: list[str] = Field(
        ...,
        description="List of optimized and consolidated test steps"
    )


llm_client = create_llm_service(
    provider=LLMProvider.OPENAI,
    api_key=os.getenv("OPENROUTER_API_KEY", "CHANGE_ME_OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

def group_actions(steps: List[Dict[str, Any]], step_descriptions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    auxiliary_actions = {'SCROLL'}
    input_actions = {'INPUT'}
    
    grouped_steps = []
    current_group = []
    prev_group_last_step = None
    all_prev_step_descriptions = []
    current_description_index = 0
    
    i = 0
    while i < len(steps):
        step = steps[i]
        action_type = step.get('action', '').upper()

        should_continue = False

        # Filter zero-delta scrolls
        if action_type == 'SCROLL':
            scroll_data = step.get('scrollData', [])
            if all(entry.get('deltaY', 0) == 0 and entry.get('deltaX', 0) == 0 for entry in scroll_data):
                i += 1
                continue

        # Filter accidental clicks on non-interactive P elements with long text
        if action_type == 'CLICK':
            el_details = step.get('elementDetails', {})
            if (el_details.get('elementType', '').upper() == 'P'
                    and len(el_details.get('elementText', '')) > 80):
                i += 1
                continue

        # Merge click-on-INPUT followed by INPUT actions into a single group
        if action_type == 'CLICK':
            el_details = step.get('elementDetails', {})
            if el_details.get('elementType', '').upper() == 'INPUT':
                click_class = el_details.get('elementClass', '')
                click_url = el_details.get('url', '')
                if (i + 1 < len(steps)
                        and steps[i + 1].get('action', '').upper() in input_actions
                        and steps[i + 1].get('elementDetails', {}).get('elementClass', '') == click_class
                        and steps[i + 1].get('elementDetails', {}).get('url', '') == click_url):
                    # Skip the click — the subsequent INPUT group will represent this interaction
                    i += 1
                    continue

        if action_type in input_actions:
            current_element_class = step.get('elementDetails', {}).get('elementClass', '')
            
            consecutive_inputs = [step]
            j = i + 1
            
            while j < len(steps):
                next_step = steps[j]
                next_action_type = next_step.get('action', '').upper()
                
                if next_action_type in input_actions:
                    next_element_class = next_step.get('elementDetails', {}).get('elementClass', '')
                    current_element_url = step.get('elementDetails', {}).get('url', '')
                    next_element_url = next_step.get('elementDetails', {}).get('url', '')
                    
                    if (next_element_class == current_element_class and current_element_class and
                        current_element_url == next_element_url):
                        consecutive_inputs.append(next_step)
                        j += 1
                    else:
                        break
                else:
                    break
            
            if len(consecutive_inputs) > 1:
                current_group.append(consecutive_inputs[-1])
                i = j
            else:
                current_group.append(step)
                i += 1
                
        else:
            current_group.append(step)
            i += 1

        if i < len(steps):
            action_type = current_group[-1].get('action', '').upper()
            if action_type in auxiliary_actions:
                should_continue = True
        
        if not should_continue:
            group_data = {
                'steps': current_group,
                'prevStepScreenshot': prev_group_last_step.get('beforeAnnotatedScreenshot') if prev_group_last_step else None,
                'allPrevStepDescriptions': all_prev_step_descriptions.copy()
            }
            grouped_steps.append(group_data)
            
            if step_descriptions and current_description_index < len(step_descriptions):
                current_step_description = step_descriptions[current_description_index]
                all_prev_step_descriptions.append(current_step_description)
                current_description_index += 1
            
            prev_group_last_step = current_group[-1]
            current_group = []
    
    if current_group:
        group_data = {
            'steps': current_group,
            'prevStepScreenshot': prev_group_last_step.get('beforeAnnotatedScreenshot') if prev_group_last_step else None,
            'allPrevStepDescriptions': all_prev_step_descriptions.copy()
        }
        grouped_steps.append(group_data)
    
    return grouped_steps

def _build_user_prompt(task_descrip: str, ui_name: str, step_group: List[Dict[str, Any]], language) -> str:
    base_prompt = prompt__td_kf_act_intro(task_descrip, ui_name, language)
    
    step_info_parts = ["\n\nUser actions:"]
    
    for j, step in enumerate(step_group):
        action_type = step.get('action', '')
        element_details = step.get('elementDetails', {})
        element_type = element_details.get('elementType', '')
        element_text = element_details.get('elementText', '')
        element_class = element_details.get('elementClass', '')
        element_id = element_details.get('elementId', '')
        element_url = element_details.get('url', '')
        element_outer_html = element_details.get('elementOuterHTML', '')
        parent_type = element_details.get('parentElementType', '')
        parent_class = element_details.get('parentElementClass', '')
        parent_outer_html = element_details.get('parentElementOuterHTML', '')
        coords = step.get('coords', {})
        input_text = step.get('inputText')

        step_info_parts.append(f"\nAction {j + 1}: {action_type}")

        if element_type:
            step_info_parts.append(f"  Element type: {element_type}")
        if element_text:
            step_info_parts.append(f"  Element text: '{element_text}'")
        if element_id:
            step_info_parts.append(f"  Element ID: {element_id}")
        if element_class:
            step_info_parts.append(f"  Element class: {element_class}")
        if element_outer_html:
            step_info_parts.append(f"  Element HTML: {element_outer_html[:200]}")
        if parent_type:
            parent_desc = f"  Parent element: {parent_type}"
            if parent_class:
                parent_desc += f" (class: {parent_class})"
            step_info_parts.append(parent_desc)
        if parent_outer_html:
            step_info_parts.append(f"  Parent HTML: {parent_outer_html[:200]}")
        if coords:
            step_info_parts.append(f"  Coordinates: x={coords.get('x')}, y={coords.get('y')}")
        if input_text:
            step_info_parts.append(f"  Typed text: '{input_text}'")
        if element_url and j == 0:
            step_info_parts.append(f"  Page URL: {element_url}")
    
    return base_prompt + "\n".join(step_info_parts)

async def _process_step_group(i: int, step_group_data: Dict[str, Any], task_descrip: str, ui_name: str, language: str, semaphore: asyncio.Semaphore) -> tuple[int, List[str]]:
    async with semaphore:
        step_group = step_group_data['steps']
        prev_screenshot = step_group_data['prevStepScreenshot']
        prev_step_description = step_group_data.get('prevStepDescription')
        
        user_prompt = _build_user_prompt(task_descrip, ui_name, step_group, language)
        
        if prev_step_description:
            user_prompt += f"\n\nPrevious step description: {prev_step_description}"
        
        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text":f"""You are a web application tester. Your task is to analyze screenshots and DSL logs, then create an unambiguous test step description in natural language. The instructions should be written in the following language: {language}.

CRITICAL: The screenshot is your PRIMARY source of truth. The DSL log is only a hint about what happened. Always look at the screenshot first to understand:
- What page/screen the user is on
- What UI elements are visible
- Where exactly the red cross marker points to
- What text, labels, and context surround the interacted element

Each instruction MUST be specific enough that it cannot be interpreted in more than one way. Include the element's visible label, its location on the page, and the surrounding context (form name, section, panel, etc.).

Describe only the necessary actions, using neutral wording (for example, "click," "scroll to the element"), without addressing anyone directly."""
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ]

        if prev_screenshot:
            prev_url = prev_screenshot.get('url')
            if prev_url:
                response = httpx.get(prev_url)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if content_type in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                        encoded_image = base64.b64encode(response.content).decode("utf-8")
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Previous step screenshot:"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{content_type};base64,{encoded_image}"
                                    }
                                }
                            ]
                        })

        for step in step_group:
            annotated_url = step.get('beforeAnnotatedScreenshot', {}).get('url')
            if annotated_url:
                response = httpx.get(annotated_url)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if content_type in ["image/png", "image/jpeg", "image/gif", "image/webp"]:
                        encoded_image = base64.b64encode(response.content).decode("utf-8")
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{content_type};base64,{encoded_image}"
                                    }
                                }
                            ]
                        })

        logger.info(f"Sending prompt to model to generate description for step {i + 1}.")
        
        try:
            response = await llm_client.fetch_completion(
                model='anthropic/claude-haiku-4.5',
                messages=messages,
                response_clazz=StepReasoningSchema,
                args={
                    "temperature": 0
                },
                component="recorder"
            )
            response_data = json.loads(response)
            results = response_data['instructions']
            logger.info(f"Generated description for step {i + 1}: {results}")
            return (i, [str(result) for result in results])
            
        except Exception as e:
            logger.error(f"Error generating description for step group {i + 1}: {e}")
            last_action = step_group[-1].get('action', 'unknown')
            return (i, [f"Step group {i + 1}: {last_action} action"])


async def generate_sop_from_demo(full_response: List[Dict[str, Any]], task_descrip: Optional[str] = None, language: str = 'english') -> List[str]:
    full_data = full_response[0]

    ui_name = full_data.get('metadata', {}).get('ui_name', 'web application')
    steps = full_data['full_data']['steps']

    if task_descrip is None:
        task_descrip = full_data.get('task', {}).get('description', "Generate SOP for provided website")

    grouped_steps = group_actions(steps)
    
    semaphore = asyncio.Semaphore(20)
    
    tasks = []
    for i, step_group_data in enumerate(grouped_steps):
        task = _process_step_group(i, step_group_data, task_descrip, ui_name, language, semaphore)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    step_descriptions = []
    sorted_results = sorted(results, key=lambda x: x[0] if not isinstance(x, Exception) else 999999)
    
    for result in sorted_results:
        if isinstance(result, Exception):
            logger.error(f"Error in parallel processing: {result}")
            step_descriptions.append("Error processing step group")
        else:
            _, descriptions = result
            if descriptions:
                step_descriptions.extend(descriptions)
    
    # optimized_steps = await _optimize_steps(step_descriptions, language)
    
    return step_descriptions
