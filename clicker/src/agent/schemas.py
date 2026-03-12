import logging
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from playwright.async_api import Page
from pydantic import BaseModel, ConfigDict, Field, model_validator

from browser_actions.tab_manager import TabManager
from browser_actions.user_storage import UserStorage
from core.schemas import CaseStatusEnum

ActionType = Literal["CLICK", "HOVER", "TYPE", "CLEAR", "SCROLL", "INNER_SCROLL", "PRESS", "NEW_TAB", "SWITCH_TAB", "WAIT", "READ", "PASTE", "SELECT", "API", "expected_result"]


class DictLikeModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if self.model_extra:
            return self.model_extra.get(key, default)
        return default

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if self.model_extra and key in self.model_extra:
            return self.model_extra[key]
        raise KeyError(key)


class CasePayload(DictLikeModel):
    case_id: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    user_storage: Optional[Dict[str, Any]] = None
    action_plan: List[Dict[str, Any]] = Field(default_factory=list)
    before_browser_start: List[str | Dict[str, Any]] = Field(default_factory=list)
    before_steps: List[str | Dict[str, Any]] = Field(default_factory=list)
    steps: List[str | Dict[str, Any]] = Field(default_factory=list)
    after_steps: List[str | Dict[str, Any]] = Field(default_factory=list)


class ResolutionPayload(BaseModel):
    width: int = 1920
    height: int = 1080


class EnvironmentPayload(DictLikeModel):
    retry_enabled: bool = False
    retry_timeout: Optional[int] = 30
    browser: str = "firefox"
    resolution: ResolutionPayload = Field(default_factory=ResolutionPayload)

    @model_validator(mode='after')
    def validate_retry_timeout(self):
        if self.retry_timeout is None:
            self.retry_timeout = 30
        return self


class StepPayload(DictLikeModel):
    action_type: ActionType = "CLICK"
    element_description: Optional[str] = None
    container_description: Optional[str] = None
    text_to_type: Optional[str] = None
    key_to_press: Optional[str] = None
    scroll_target: Optional[str] = None
    wait_time: Optional[str | int] = None
    tab_name: Optional[str] = None
    value: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class ReflectionStepConfig(BaseModel):
    instruction: str = Field(description="Reflection instruction text")
    use_single_screenshot: bool = Field(default=True, description="Use single screenshot verification instead of two-screenshot comparison")


class Action(BaseModel):
    action_type: ActionType = Field(
        "CLICK",
        description="Action type to take when `is_completed=False`.",
    )
    element_description: Optional[str] = Field(
        None,
        description="Comprehensive description of the element to interact with including name, type, position, and other attributes.",
    )
    container_description: Optional[str] = Field(
        None,
        description="Comprehensive description of the scrollable container including name, type, position, and other distinguishing attributes.",
    )
    text_to_type: Optional[str] = Field(
        None,
        description="Text to type if action_type is TYPE.",
    )
    key_to_press: Optional[str] = Field(
        None,
        description="Key to press if action_type is PRESS.",
    )
    scroll_target: Optional[str] = Field(
        None,
        description="Name/text of the target element to scroll into view if action_type is INNER_SCROLL or SCROLL.",
    )
    wait_time: Optional[str | int] = Field(
        None,
        description="Time to wait in seconds if action_type is WAIT.",
    )
    tab_name: Optional[str] = Field(
        None,
        description="Title or address of the tab to navigate to if action_type is NEW_TAB or SWITCH_TAB.",
    )
    storage_key: Optional[str] = Field(
        None,
        description="Key to store/retrieve text for READ/PASTE actions. For READ with {{var_name}}, use var_name without braces.",
    )
    instruction: Optional[str] = Field(
        None,
        description="Instruction for what text to read for READ action.",
    )
    option_value: Optional[str] = Field(
        None,
        description="Option value to select if action_type is SELECT.",
    )


class ActionList(BaseModel):
    actions: List[Action] = Field(
        ...,
        description="List of actions to take."
    )


# Graph states
class InputState(BaseModel):
    run_id: str
    case: CasePayload
    environment: EnvironmentPayload
    user_id: str
    background_video_generate: bool


class StepState(BaseModel):
    step_id: str = Field(description="Step identifier")
    current_step: StepPayload = Field(description="Class with step data")
    action: ActionType = Field(description="Step action")
    element_description: Optional[str] = Field(description="Comprehensive description of the element")
    before_screenshot_path: Path = Field(description="Path to the before screenshot")
    annotated_screenshot_path: Path = Field(description="Path to the annotated screenshot")
    after_screenshot_path: Path = Field(description="Path to the after screenshot")
    full_screenshot_path: Path = Field(description="Path to the screenshot of the whole page")
    context_screenshot_path: Optional[Path] = Field(default=None, description="Path to the context screenshot")
    use_single_screenshot: bool = Field(default=True, description="Use single screenshot verification instead of two-screenshot comparison")
    validation_result: Dict[str, Any] = Field(default_factory=dict, description="reflection results")
    model_time: float = Field(default=0, description="Inference time")
    start_time: float = Field(description="Timestamp of the start of current attempt to execute the step")
    reflection_time: float = Field(default=0, description="Time taken to perform reflection steps")

    detection_confidence: list[int] = Field(default_factory=lambda: [0], description="Detection confidence, for scrolling actions it's list of confidences for each screenshot crop")
    coordinates: tuple[int, int] = Field(default=(0, 0), description="Step coordinates for actions: click, hover, type")
    text_to_type: Optional[str] = Field(default=None, description="Text to type")
    wait_time: int = Field(default=30, description="Maximum waiting time for the WAIT action")
    scroll_y: int = Field(default=0, description="Scroll y coordinate")
    scroll_element: str = Field(default="body", description="Scrollable element (or 'body' if scrolling the whole page)")
    key_to_press: Optional[str] = Field(default=None, description="Key to press")
    tab_name: Optional[str] = Field(default=None, description="Tab name")
    extra: Optional[Dict[str, Any]] = Field(default=None, description="extra")


def merge_step_states(step_state1: Optional[Union[StepState, dict]], step_state2: Optional[Union[StepState, dict]]) -> Optional[Union[StepState, dict]]:
    if step_state1 is None:
        return step_state2
    if step_state2 is None:
        return step_state1

    # If both are dictionaries, simply merge them
    if isinstance(step_state1, dict) and isinstance(step_state2, dict):
        merged_dict = step_state1.copy()
        merged_dict.update(step_state2)
        return merged_dict

    # Convert to dictionaries if needed
    step_state1_dict = step_state1 if isinstance(step_state1, dict) else step_state1.model_dump()
    step_state2_dict = step_state2 if isinstance(step_state2, dict) else step_state2.model_dump()

    # Merge the dictionaries
    merged_dict = step_state1_dict.copy()
    merged_dict.update(step_state2_dict)

    # If one of the inputs was a StepState, convert back to StepState
    if isinstance(step_state1, StepState) or isinstance(step_state2, StepState):
        return StepState(**merged_dict)

    return merged_dict


class RetrySettings(BaseModel):
    enabled: bool = False
    timeout: Optional[int] = Field(30, ge=1, le=60)
    interval: int = 2

    @model_validator(mode='after')
    def validate_retries(self):
        if self.timeout is None:
            # 30 по дефолту
            self.timeout = 30


class AgentState(BaseModel):
    playwright: Optional[Any] = Field(default=None, description="Playwright instance")
    browser: Optional[Any] = Field(default=None, description="Playwright browser instance")
    context: Optional[Any] = Field(default=None, description="Playwright context")
    session: Optional[Any] = Field(default=None, description="Database session")
    tab_manager: Optional[TabManager] = Field(default=None, description="Tab manager instance")
    user_storage: Optional[UserStorage] = Field(default=None, description="User storage instance")
    page: Optional[Page] = Field(default=None, description="Current page instance")
    logger: Optional[logging.Logger] = Field(default=None, description="Logger instance")
    log_buffer: Optional[StringIO] = Field(default=None, description="Log buffer instance")
    log_handler: Optional[logging.Handler] = Field(default=None, description="Log handler instance")
    inference_client: Optional[Any] = Field(default=None, description="Model inference client instance")
    reflection_client: Optional[Any] = Field(default=None, description="Reflection model client instance")
    screenshot_base_path: Path = Field(description="Base path for screenshots")
    trace_file_path: str = Field(description="Path to trace file")
    run_id: str = Field(description="Unique task identifier")  # can later move those fields to config https://langchain-ai.github.io/langgraph/how-tos/configuration/
    case_id: str = Field(description="Case identifier")
    case_name: str = Field(description="Name of the test case")
    width: int = Field(default=1920, description="Width of the browser viewport")
    height: int = Field(default=1080, description="Height of the browser viewport")
    start_dt: datetime = Field(description="Start timestamp")
    action_plan: List[Dict[str, Any]] = Field(description="List of actions to execute")
    case_steps: List[str | Dict[str, Any]] = Field(description="List of steps")
    steps_descriptions: List[str] = Field(description="List of steps descriptions")
    current_step_index: int = Field(default=0, description="Current step index")
    current_attempt: int = Field(default=0, description="Current attempt number")
    status: CaseStatusEnum = Field(default=CaseStatusEnum.PASSED, description="Current status of the task execution")
    run_summary: str = Field(default="", description="Summary of the run")
    retry_messages_buffer: str = Field(default="", description="Buffer log messages for retries")
    retry_temp_result_reflection: Optional[Any] = Field(default=None, description="Temp reflection result for retries")
    local_async_engine: Optional[Any] = Field(default=None, description="Local async engine instance")
    background_video_generate: bool
    main_steps_failed: bool = Field(default=False, description="Simple step failed")
    after_step_failed: bool = Field(default=False, description="After step failed")
    retry_settings: Optional[Any] = Field(default=RetrySettings, description="retry_settings")

    step_state: Annotated[Optional[StepState], merge_step_states] = Field(
        default=None,
        description="The state of the current step"
    )
    completed_steps: List[StepState] = Field(
        default_factory=list,
        description="History of successfully executed steps"
    )

    class Config:
        arbitrary_types_allowed = True


class ReflectionResult(BaseModel):
    instruction_language: str = Field(description="Verification Instruction Language")
    thought_process: str = Field(description="Thought Process")
    details: str
    verification_passed: bool

    @classmethod
    def from_tars_v15(cls, tars_result):
        """Convert TarsV15ReflectionResult to ReflectionResult"""

        return cls(
            instruction_language=tars_result.instruction_language,
            thought_process=tars_result.chain_of_thoughts,
            details=tars_result.details,
            verification_passed=tars_result.verification_passed
        )

    @classmethod
    def from_claude(cls, claude_result):
        """Convert ClaudeReflectionResult to ReflectionResult"""

        # Convert List[ThoughtProcess] to string
        thought_process_str = "\n".join([
            f"Step {tp.step}: {tp.description}"
            for tp in claude_result.thought_process
        ])

        return cls(
            instruction_language=claude_result.instruction_language,
            thought_process=thought_process_str,
            details=claude_result.details,
            verification_passed=claude_result.verification_passed
        )

    @classmethod
    def from_qwen3_vl(cls, qwen3_vl_result):

        return cls(
            instruction_language=qwen3_vl_result.instruction_language,
            thought_process=qwen3_vl_result.thought_process,
            details=qwen3_vl_result.details,
            verification_passed=qwen3_vl_result.verification_passed
        )
