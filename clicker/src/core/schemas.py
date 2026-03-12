import json
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)
from typing_extensions import Annotated


class MinioObjectPath(BaseModel):
    bucket: str = Field(min_length=1)
    file: str = Field(min_length=1)


class FlexibleStepPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


class CoordinatesRequest(BaseModel):
    image_base64_string: Optional[str] = None
    prompt: str
    minio_path: Optional[MinioObjectPath] = None
    context_screenshot_path: Optional[MinioObjectPath] = None


class ReflectionRequest(BaseModel):
    reflection_instruction: str
    before_image_base64_string: Optional[str] = None
    before_minio_path: Optional[MinioObjectPath] = None
    after_image_base64_string: Optional[str] = None
    after_minio_path: Optional[MinioObjectPath] = None
    use_single_screenshot: Optional[bool] = Field(default=True, description="use_single_screenshot")


class SOPValidationRequest(BaseModel):
    sop: List[str]
    action_plan_id: Optional[str] = None
    user_id: Optional[str] = None
    case_id: Optional[str] = None


class RecordModel(BaseModel):
    record: List[Dict[str, Any]]
    context: Optional[str] = None

class ConvertToSopResponse(BaseModel):
    steps_description: List[str]

class CaseBase(BaseModel):
    name: str
    context: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    before_browser_start: Optional[List[str | FlexibleStepPayload]] = Field(default_factory=list)
    before_steps: Optional[List[str | FlexibleStepPayload]] = Field(default_factory=list)
    steps: List[str | FlexibleStepPayload]
    after_steps: Optional[List[str | FlexibleStepPayload]] = Field(default_factory=list)
    type: Optional[str] = "automated"
    status: Optional[str] = "Draft"
    priority: Optional[str] = "Low"
    url: Optional[HttpUrl] = None
    variables: Optional[str] = "Default"
    is_valid: Optional[bool] = True
    validation_reason: Optional[str | FlexibleStepPayload] = Field(default_factory=dict)
    action_plan: Optional[List[FlexibleStepPayload]] = Field(default_factory=list)
    external_id: Optional[str] = None
    environment_id: Optional[UUID4] = None

class CaseRead(CaseBase):
    case_id: UUID4
    suite_id: UUID4
    project_id: Optional[UUID4] = None
    position: int

    class Config:
        from_attributes = True
        extra = "allow"


class RunSingleCase(BaseModel):
    id: UUID4
    task: str
    args: list
    kwargs: Dict[str, Any]


class CaseStatusEnum(str, Enum):
    UNTESTED = "untested"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INVALID = "invalid"
    RETEST = "retest"
    IN_PROGRESS = "in_progress"
    IN_QUEUE = "in_queue"
    STOPPED = "stopped"
    STOP_IN_PROGRESS = "stop_in_progress"
    PREPARATION = "preparation"
    AFTER_STEP_FAILURE = "after_step_failure"


class Lang(str, Enum):
    RU = "ru"
    EN = "en"


class ColorEnum(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"


class ApiStep(BaseModel):
    type: Literal["api"] = "api"  # всегда "api"
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$", description="метод")
    url: str = Field(..., min_length=1, description="URL")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Заголовки")
    data: Optional[Any] = Field(None, description="Тело запроса (для JSON, form-data)")
    files: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Файлы для загрузки")
    value: str = Field(..., min_length=1, description="CURL для фронта")

    @field_validator('method')
    @classmethod
    def method_upper(cls, v):
        return v.upper()

    @field_validator('headers', mode='before')
    @classmethod
    def set_default_headers(cls, v):
        return v or {}

    @field_validator('data', mode='before')
    @classmethod
    def validate_data(cls, v):
        if isinstance(v, str):
            try:
                # Пробуем распарсить строку как JSON
                return json.loads(v)
            except json.JSONDecodeError:
                # Если не JSON, оставляем как строку
                return v
        return v

    def get_content_type(self) -> Optional[str]:
        """Content-Type из headers"""
        if not self.headers:
            return None

        for header_name, header_value in self.headers.items():
            if header_name.lower() == "content-type":
                return header_value.lower()
        return None


class ElementDescriptionRequest(BaseModel):
    image_base64_string: Optional[str] = None
    minio_path: Optional[MinioObjectPath] = None
    x1: int = Field(..., description="Left X coordinate of element bounding box")
    y1: int = Field(..., description="Top Y coordinate of element bounding box")
    x2: int = Field(..., description="Right X coordinate of element bounding box")
    y2: int = Field(..., description="Bottom Y coordinate of element bounding box")
    thinking_mode: bool = Field(default=True, description="Enable reasoning/thinking before response")
    color: ColorEnum = Field(default=ColorEnum.RED, description="Color for drawing bounding box")


class CoordinatesResponse(BaseModel):
    result_id: str
    generate_time: str
    original_prompt: str
    final_prompt: str
    coords: tuple[int, int]
    original_image_base64: str
    annotated_image_base64: str
    context_screenshot_path: Optional[MinioObjectPath] = None


class ReflectionResponse(BaseModel):
    result_id: str
    reflection_time: str
    reflection_step: str
    reflection_title: str
    reflection_description: str
    reflection_thoughts: str
    reflection_result: Literal["passed", "failed"]


class ElementDescriptionResponse(BaseModel):
    result_id: str
    generate_time: str
    bounding_box: Dict[str, int]
    description: str
    color: ColorEnum
    success: bool
    original_image_base64: str
