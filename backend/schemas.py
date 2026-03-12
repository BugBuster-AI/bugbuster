import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (UUID4, BaseModel, ConfigDict, EmailStr, Field, HttpUrl,
                      StringConstraints, computed_field, field_validator,
                      model_validator)
from typing_extensions import Annotated


class CoordinatesRequest(BaseModel):
    image_base64_string: Optional[str] = None
    prompt: str
    minio_path: Optional[Dict[str, str]] = None
    context_screenshot_path: Optional[Dict[str, str]] = None
    use_rewriter: Optional[bool] = Field(default=True, description="use_rewriter for prompt")


class ReflectionRequest(BaseModel):
    reflection_instruction: str
    before_image_base64_string: Optional[str] = None
    before_minio_path: Optional[Dict[str, str]] = None
    after_image_base64_string: Optional[str] = None
    after_minio_path: Optional[Dict[str, str]] = None
    use_single_screenshot: Optional[bool] = Field(default=True, description="use_single_screenshot")


class ColorEnum(str, Enum):
    RED = "red"
    BLUE = "blue"
    GREEN = "green"


class ElementDescriptionRequest(BaseModel):
    image_base64_string: Optional[str] = None
    minio_path: Optional[Dict[str, str]] = None
    x1: int = Field(..., description="Left X coordinate of element bounding box")
    y1: int = Field(..., description="Top Y coordinate of element bounding box")
    x2: int = Field(..., description="Right X coordinate of element bounding box")
    y2: int = Field(..., description="Bottom Y coordinate of element bounding box")
    thinking_mode: bool = Field(default=True, description="Enable reasoning/thinking before response")
    color: ColorEnum = Field(default=ColorEnum.RED, description="Color for drawing bounding box")


class ContextScreenshotRequestCreate(BaseModel):
    image_base64_string: Optional[str] = None
    minio_path: Optional[Dict[str, str]] = None
    x1: int = Field(..., description="Left X coordinate of element bounding box")
    y1: int = Field(..., description="Top Y coordinate of element bounding box")
    x2: int = Field(..., description="Right X coordinate of element bounding box")
    y2: int = Field(..., description="Bottom Y coordinate of element bounding box")
    color: ColorEnum = Field(default=ColorEnum.RED, description="Color for drawing bounding box")


class ContextScreenshotRequestDelete(BaseModel):
    minio_path: Dict[str, str]


class FlagCatalogBase(BaseModel):
    flag_name: str
    description: str
    default_shown: bool
    default_view_count: int
    is_active: bool


class FlagCatalogCreate(FlagCatalogBase):
    pass


class FlagCatalogRead(FlagCatalogBase):
    created_at: datetime

    class Config:
        from_attributes = True


class UserFlagsBase(BaseModel):
    flags: Dict[str, Dict[str, Any]]


class UserFlagsRead(UserFlagsBase):
    user_id: UUID4
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserFlagsUpdate(BaseModel):
    shown: Optional[Annotated[bool, Field(None, description="Установить состояние показа (True/False). Если None - не изменяется")]] = None
    view_count: Optional[Annotated[int, Field(None, ge=0, description="Установить конкретное значение счетчика. Если None - не изменяется")]] = None
    increment_view: Optional[Annotated[bool, Field(None, description="Увеличить счетчик просмотров на 1. Игнорируется, если указан view_count")]] = None


class GroupRunCaseOrderBy(str, Enum):
    created_at = "created_at"
    deadline = "deadline"
    status = "status"
    user_id = "author"
    name = "name"


class TariffPeriod(str, Enum):
    MONTH = "month"


class WorkspaceMembershipStatusEnum(str, Enum):
    INVITED = "Invited"
    ACTIVE = "Active"


class WorkspaceStatusEnum(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"


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


class CaseFinalStatusEnum(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    AFTER_STEP_FAILURE = "after_step_failure"
    BLOCKED = "blocked"
    INVALID = "invalid"
    STOPPED = "stopped"


class CaseTypeEnum(str, Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"


class BrowserEnum(str, Enum):
    chrome = "chrome"
    firefox = "firefox"
    # safari = "safari"
    # edge = "edge"


class OSEnum(str, Enum):
    windows = "windows"
    macos = "macos"
    linux = "linux"


class Roles(str, Enum):
    ROLE_ADMIN = "admin"
    ROLE_MEMBER = "member"
    ROLE_READ_ONLY = "read-only"
    #  ROLE_SYSTEM = "system"


class Lang(str, Enum):
    RU = "ru"
    EN = "en"


class Resolution(BaseModel):
    width: Annotated[int, Field(default=1920, strict=True, ge=240, le=1920)]
    height: Annotated[int, Field(default=1080, strict=True, ge=240, le=1080)]

    class Config:
        from_attributes = True


class EnvironmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    browser: BrowserEnum
    operation_system: OSEnum
    resolution: Resolution
    retry_enabled: Optional[bool] = False
    retry_timeout: Optional[int] = Field(None, ge=1, le=60)

    @model_validator(mode='after')
    def validate_retries(self):
        if self.retry_enabled is True and self.retry_timeout is None:
            # 30 по дефолту
            self.retry_timeout = 30

        if self.retry_enabled is False and self.retry_timeout is not None:
            # Игнорируем timeout, если retry отключён
            self.retry_timeout = None
        return self

    class Config:
        from_attributes = True


class EnvironmentCreate(EnvironmentBase):
    project_id: UUID4


class EnvironmentRead(EnvironmentBase):
    environment_id: UUID4
    project_id: UUID4

    class Config:
        from_attributes = True


class EnvironmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    browser: Optional[BrowserEnum] = None
    operation_system: Optional[OSEnum] = None
    resolution: Optional[Resolution] = None
    retry_enabled: Optional[bool] = False
    retry_timeout: Optional[int] = Field(None, ge=1, le=60)


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: UUID4
    picture: Optional[str] = None


class TokenData(BaseModel):
    user_id: Optional[UUID4] = None


# пользовательские токены

TokenStatus = Literal["active", "expired", "inactive"]


class UserTokenCreate(BaseModel):
    name: Optional[str] = None
    expires_at: Optional[date] = None  # None — токен вечный

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class UserTokenUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    expires_at: Optional[date] = None   # None — токен вечный

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class UserTokenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token_id: UUID4
    name: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    @computed_field
    @property
    def status(self) -> TokenStatus:
        if not self.is_active:
            return "inactive"
        if self.expires_at is None:
            return "active"
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return "active" if exp > datetime.now(timezone.utc) else "expired"


class UserTokenCreated(UserTokenRead):
    model_config = ConfigDict(extra="forbid")
    # токен показываем один раз при создании
    token: str


class UserIn(BaseModel):
    username: str
    email: EmailStr
    password: str


class Role(BaseModel):
    role: str

    class Config:
        from_attributes = True


class RoleIn(BaseModel):
    role: str


class UserRead(BaseModel):
    user_id: Optional[UUID4] = None
    username: str
    email: str
    is_active: Optional[bool] = None
    registered_at: Optional[datetime] = None
    active_workspace_id: UUID4
    role: Optional[str] = None
    avatar: Optional[str] = None
    host: Optional[str] = None
    workspace_status: Optional[WorkspaceStatusEnum] = None
    max_concurrent_tasks: Optional[int] = None
    tariff_expiration: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserId(BaseModel):
    user_id: UUID4


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr
    language: Optional[Lang] = Lang.RU.value


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class InviteUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    role_title: str
    role: Roles
    project_ids: Optional[List[UUID4]] = None
    language: Optional[Lang] = Lang.RU.value


class EditUserWorkspace(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    role_title: Optional[str] = None
    role: Optional[Roles] = Roles.ROLE_READ_ONLY.value
    project_ids: Optional[List[UUID4]] = None


class HappyPassBase(BaseModel):
    name: str
    context: Optional[str] = None
    images: List
    full_data: Dict
    created_at: datetime
    steps: Optional[List] = None
    action_plan: Optional[List] = None


class HappyPassCreate(HappyPassBase):
    pass


class HappyPassRead(HappyPassBase):
    happy_pass_id: UUID4

    class Config:
        from_attributes = True


# Projects
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = 0


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    project_id: UUID4

    class Config:
        from_attributes = True


class ProjectReadFull(ProjectBase):
    project_id: UUID4
    suites: List['SuiteReadFull'] = []

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    project_id: UUID4
    name: Optional[str] = None
    description: Optional[str] = None
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = 0


class ProjectSummary(BaseModel):
    project_id: UUID4
    name: str
    description: Optional[str] = None
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = 0
    suite_count: int
    case_count: int
    run_count: Optional[int] = 0

    class Config:
        from_attributes = True


# Suites
class SuiteBase(BaseModel):
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SuiteCreate(SuiteBase):
    project_id: UUID4
    parent_id: Optional[UUID4] = None


class SuiteRead(SuiteBase):
    suite_id: UUID4
    parent_id: Optional[UUID4] = None
    position: int

    class Config:
        from_attributes = True


class SuiteReadFull(SuiteBase):
    suite_id: UUID4
    parent_id: Optional[UUID4] = None
    position: int
    cases: List['CaseRead'] = []
    children: List['SuiteReadFull'] = []

    class Config:
        from_attributes = True


class SuiteUpdate(BaseModel):
    suite_id: UUID4
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID4] = None
    new_position: Optional[Annotated[int, Field(ge=0, le=1000)]] = None


class SuiteSummary(BaseModel):
    suite_id: UUID4
    project_id: UUID4
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID4] = None
    case_count: int

    class Config:
        from_attributes = True


# Cases
class CaseBase(BaseModel):
    name: str
    context: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    before_browser_start: Optional[List[str | Dict]] = []
    before_steps: Optional[List[str | Dict]] = []
    steps: List[str | Dict]
    after_steps: Optional[List[str | Dict]] = []
    type: Optional[str] = "automated"
    status: Optional[str] = "Draft"
    priority: Optional[str] = "Low"
    url: Optional[HttpUrl] = None
    variables: Optional[str] = "Default"
    is_valid: Optional[bool] = True
    validation_reason: Optional[str | Dict] = {}
    action_plan: Optional[List[dict]] = []
    external_id: Optional[str] = None
    environment_id: Optional[UUID4] = None


class CaseCreate(BaseModel):
    name: str
    context: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    before_browser_start: Optional[List[Dict]] = []
    before_steps: Optional[List[Dict]] = []
    steps: List[Dict]
    after_steps: Optional[List[Dict]] = []
    type: Optional[CaseTypeEnum] = CaseTypeEnum.AUTOMATED
    status: Optional[str] = "Draft"
    priority: Optional[str] = "Low"
    url: Optional[HttpUrl] = None
    variables: Optional[str] = "Default"
    external_id: Optional[str] = None
    environment_id: Optional[UUID4] = None

    suite_id: UUID4

    @field_validator('before_browser_start', 'before_steps', 'steps', 'after_steps')
    @classmethod
    def validate_step_structure(cls, v, info):
        field_name = info.field_name
        valid_types = {'api', 'action', 'shared_step', 'expected_result'}

        for i, step in enumerate(v):
            if not isinstance(step, dict):
                raise ValueError(f'Item {i} in {field_name} must be a dictionary')

            # Проверяем обязательное поле 'type'
            if 'type' not in step:
                raise ValueError(f'Item {i} in {field_name} must have a "type" field')

            step_type = step['type']
            if step_type not in valid_types:
                raise ValueError(f'Item {i} in {field_name}: type must be one of {valid_types}, got "{step_type}"')

            # Проверяем обязательное поле 'value'
            if 'value' not in step:
                raise ValueError(f'Item {i} in {field_name} must have a "value" field')

        return v


class CaseCreateFromRecord(BaseModel):
    suite_id: UUID4
    happy_pass_id: UUID4
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    before_browser_start: Optional[List[str | Dict]] = []
    before_steps: Optional[List[str | Dict]] = []
    after_steps: Optional[List[str | Dict]] = []
    type: Optional[CaseTypeEnum] = CaseTypeEnum.AUTOMATED
    status: Optional[str] = "Draft"
    priority: Optional[str] = "Low"
    url: Optional[HttpUrl] = None
    variables: Optional[str] = "Default"
    external_id: Optional[str] = None


class CaseRead(CaseBase):
    case_id: UUID4
    suite_id: UUID4
    project_id: Optional[UUID4] = None
    position: int

    class Config:
        from_attributes = True
        extra = "allow"


class CaseUpdate(BaseModel):
    case_id: UUID4
    name: Optional[str] = None
    context: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    before_browser_start: Optional[List[Dict]] = None
    before_steps: Optional[List[str | Dict]] = None
    steps: Optional[List[str | Dict]] = None
    after_steps: Optional[List[str | Dict]] = None
    type: Optional[CaseTypeEnum] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    url: Optional[HttpUrl] = None
    variables: Optional[str] = None
    external_id: Optional[str] = None
    suite_id: Optional[UUID4] = None
    new_position: Optional[int] = None
    environment_id: Optional[UUID4] = None

    # @field_validator('before_browser_start', 'before_steps', 'steps', 'after_steps')
    # @classmethod
    # def validate_step_structure(cls, v, info):
    #     field_name = info.field_name
    #     valid_types = {'api', 'action', 'shared_step', 'expected_result'}

    #     for i, step in enumerate(v):
    #         if not isinstance(step, dict):
    #             raise ValueError(f'Item {i} in {field_name} must be a dictionary')

    #         # Проверяем обязательное поле 'type'
    #         if 'type' not in step:
    #             raise ValueError(f'Item {i} in {field_name} must have a "type" field')

    #         step_type = step['type']
    #         if step_type not in valid_types:
    #             raise ValueError(f'Item {i} in {field_name}: type must be one of {valid_types}, got "{step_type}"')

    #         # Проверяем обязательное поле 'value'
    #         if 'value' not in step:
    #             raise ValueError(f'Item {i} in {field_name} must have a "value" field')

    #     return v


# Shared steps
class SharedStepsBase(BaseModel):
    name: str
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    steps: List[Dict]
    is_valid: Optional[bool] = True
    validation_reason: Optional[str | Dict] = {}
    action_plan: Optional[List[dict]] = []


class SharedStepsCreate(BaseModel):
    name: str
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    steps: List[Dict]
    project_id: UUID4


class SharedStepsRead(SharedStepsBase):
    shared_steps_id: UUID4
    project_id: UUID4

    class Config:
        from_attributes = True


class SharedStepsUpdate(BaseModel):
    shared_steps_id: UUID4
    name: Optional[str] = None
    description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None
    steps: Optional[List[Dict]] = None


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


# Runs

class ExecutionModeEnum(str, Enum):
    sequential = "sequential"
    parallel = "parallel"


class GroupRunCaseCaseInput(BaseModel):
    case_id: UUID4
    execution_mode: ExecutionModeEnum
    execution_order: Optional[int] = Field(default=None, ge=1)


class RunSingleCase(BaseModel):
    id: UUID4
    task: str
    args: list
    kwargs: Dict


class GroupRunCaseCreate(BaseModel):
    project_id: UUID4
    name: str
    description: Optional[str] = None
    environment_id: UUID4
    deadline: Optional[datetime] = None
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = 0
    host: Optional[str] = None
    variables: Optional[str] = None
    cases: List[GroupRunCaseCaseInput]
    extra: Optional[str] = None
    background_video_generate: Optional[bool] = True


class GroupRunCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    environment_id: Optional[UUID4] = None
    deadline: Optional[datetime] = None
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = None
    host: Optional[str] = None
    variables: Optional[str] = None
    cases: Optional[List[GroupRunCaseCaseInput]] = None
    extra: Optional[str] = None
    background_video_generate: Optional[bool] = None


class GroupRunCaseRead(BaseModel):
    project_id: UUID4
    group_run_id: UUID4
    parallel_exec: Optional[Annotated[int, Field(ge=0, le=1000)]] = 0
    user_id: UUID4
    created_at: datetime
    name: str
    description: Optional[str]
    status: str
    extra: Optional[str] = None
    variables: Optional[str] = None
    background_video_generate: Optional[bool] = True

    class Config:
        from_attributes = True


class Task(BaseModel):
    task_id: UUID4
    type: str
    chunk: str | None = None
    end: bool = False
    extra: Optional[Dict[str, str]] = None
    command: str | None = None
    subsuite_id: UUID4 | None = None
    context: str | None = None
    variants: int | None = None
    case_id: UUID4 | None = None
    mode: str | None = None


# Tariffs
class TariffBase(BaseModel):
    tariff_name: str
    tariff_full_name: str
    description: Optional[str] = None
    cnt_months: Annotated[int, Field(default=1, ge=1, le=1000)]
    price: Annotated[float, Field(default=10000, ge=0)]
    cur: str
    discount: Annotated[int, Field(default=0, ge=0, le=100)]
    period: TariffPeriod = TariffPeriod.MONTH
    buy_tariff_manual_only: bool = False
    best_value: bool = False
    can_buy_streams: bool = True
    visible: bool = True


class TariffCreate(TariffBase):
    pass


class TariffRead(TariffBase):
    tariff_id: UUID4

    class Config:
        from_attributes = True


class TariffUpdate(BaseModel):
    tariff_id: UUID4
    tariff_name: Optional[str] = None
    tariff_full_name: Optional[str] = None
    description: Optional[str] = None
    cnt_months: Optional[Annotated[int, Field(ge=1, le=1000)]] = None
    price: Optional[Annotated[float, Field(ge=0)]] = None
    cur: Optional[str] = None
    discount: Optional[Annotated[int, Field(default=0, ge=0, le=100)]] = None
    period: Optional[TariffPeriod] = None
    buy_tariff_manual_only: Optional[bool] = None
    best_value: Optional[bool] = None
    can_buy_streams: Optional[bool] = None
    visible: Optional[bool] = None


class TariffLimitBase(BaseModel):
    feature_name: str
    feature_full_name: str
    feature_full_simple: str
    limit_value: int


class TariffLimitCreate(TariffLimitBase):
    tariff_id: UUID4


class TariffLimitRead(TariffLimitBase):
    limit_id: UUID4
    tariff_id: UUID4

    class Config:
        from_attributes = True


class TariffLimitUpdate(BaseModel):
    limit_id: UUID4
    feature_full_name: Optional[str] = None
    feature_full_simple: Optional[str] = None
    limit_value: Optional[int] = None


# Variables
class VariablesBase(BaseModel):
    variables_kit_name: str
    variables_kit_description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None


class VariablesCreate(VariablesBase):
    project_id: UUID4


class VariablesRead(VariablesBase):
    variables_kit_id: UUID4
    project_id: UUID4

    @computed_field
    @property
    def editable(self) -> bool:
        """Возвращает False если это Default набор, иначе True"""
        return self.variables_kit_name != "Default"

    class Config:
        from_attributes = True


class VariablesUpdate(BaseModel):
    variables_kit_name: Optional[str] = None
    variables_kit_description: Optional[Annotated[str, StringConstraints(max_length=1000)]] = None


# ######################################################## VariablesDetails #########################################################

TimeBaseType = Literal["currentDate",
                       "currentTime",
                       "dateTime",
                       "timestamp",
                       "today",
                       "yesterday",
                       "tomorrow",
                       "startOfDay",
                       "endOfDay"]

TimeUnit = Literal["y", "M", "d", "h", "m", "s"]

# ###### format

# мэппинг формата
TOKEN_TO_STRFTIME = {
    "YYYY": "%Y",
    "YY": "%y",
    "MM": "%m",
    "DD": "%d",
    "HH": "%H",
    "mm": "%M",
    "ss": "%S",
}

# без лидирующего нуля зависит от ОС
if os.name == "nt":
    TOKEN_TO_STRFTIME.update({
        "M": "%#m",
        "D": "%#d",
        "H": "%#H",
        "m": "%#M",
        "s": "%#S",
    })
else:
    TOKEN_TO_STRFTIME.update({
        "M": "%-m",
        "D": "%-d",
        "H": "%-H",
        "m": "%-M",
        "s": "%-S",
    })

UNIX_TOKENS = {"X", "x"}  # это не strftime, обрабатываем отдельно (сек, миллисек)

FORMAT_TOKENS = list(TOKEN_TO_STRFTIME.keys()) + list(UNIX_TOKENS)

ALLOWED_SEPARATORS = set("-.:_/ ")

BASE_DEFAULT_FORMAT: dict[TimeBaseType, str] = {
    "currentDate": "YYYY-MM-DD",
    "today": "YYYY-MM-DD",
    "yesterday": "YYYY-MM-DD",
    "tomorrow": "YYYY-MM-DD",
    "currentTime": "HH:mm:ss",
    "dateTime": "YYYY-MM-DD HH:mm:ss",
    "startOfDay": "YYYY-MM-DD HH:mm:ss",
    "endOfDay": "YYYY-MM-DD HH:mm:ss",
    "timestamp": "X",
}


def parse_format_pattern(pattern: str) -> Tuple[Optional[str], bool, bool]:
    """мэппим на python format
    возвращаем либо флаг unix timestamp, либо format для strftime
    unix нельзя сочетать с strftime
    """
    i = 0
    n = len(pattern)

    is_unix_seconds = False
    is_unix_millis = False
    strftime_parts: list[str] = []

    sorted_tokens = sorted(FORMAT_TOKENS, key=len, reverse=True)

    while i < n:
        matched_token = None

        for token in sorted_tokens:
            if pattern.startswith(token, i):
                matched_token = token
                break

        if matched_token is not None:
            if matched_token in UNIX_TOKENS:
                if strftime_parts:
                    raise ValueError(
                        "Unix tokens 'X' or 'x' cannot be combined with other tokens"
                    )
                if matched_token == "X":
                    is_unix_seconds = True
                else:
                    is_unix_millis = True
                i += len(matched_token)
                continue

            strftime_parts.append(TOKEN_TO_STRFTIME[matched_token])
            i += len(matched_token)
            continue

        ch = pattern[i]

        if ch in ALLOWED_SEPARATORS:
            strftime_parts.append(ch)
            i += 1
            continue

        raise ValueError(
            f"Invalid format pattern: unexpected character '{ch}' at position {i} in '{pattern}'"
        )

    if is_unix_seconds or is_unix_millis:
        return None, is_unix_seconds, is_unix_millis

    if not strftime_parts:
        raise ValueError("Format pattern must contain at least one token")

    return "".join(strftime_parts), False, False
#######################


# ### Подмодели для variable_config ###
class SimpleVariableConfig(BaseModel):
    type: Literal["simple"] = "simple"
    value: Optional[str] = None


# поле "shifts"
class TimeShift(BaseModel):
    value: int
    unit: TimeUnit


class TimeVariableConfig(BaseModel):
    type: Literal["time"] = "time"
    base: TimeBaseType
    utc_offset: Optional[str] = None
    shifts: Optional[list[TimeShift]] = None
    format: Optional[str] = None
    is_const: Optional[bool] = False

    @field_validator('utc_offset')
    @classmethod
    def validate_utc_offset(cls, v: Optional[str]) -> Optional[str]:
        # 3:00 +3:00 03:00 +03:00 -03:00 -3:00
        if v is None:
            return v

        # +-, 1-2 цифры часа, двоеточие, 2 цифры минут
        m = re.fullmatch(r'^\s*([+-])?(\d{1,2}):(\d{2})\s*$', v)
        if not m:
            raise ValueError(
                'utc_offset must be like "+HH:MM", "-HH:MM" or "H:MM" (optional sign).'
            )

        sign = m.group(1) or '+'   # если нет знака — считаем как +
        hours = int(m.group(2))
        minutes = m.group(3)

        if minutes not in {'00', '15', '30', '45'}:
            raise ValueError('utc_offset minutes must be: 00, 15, 30, 45')

        if sign == '-':
            if not (0 <= hours <= 12):
                raise ValueError('utc_offset for negative offsets must be between -12:00 and -00:00')
        else:
            if not (0 <= hours <= 14):
                raise ValueError('utc_offset for positive offsets must be between +00:00 and +14:00')

        # вернём в формате "+HH:MM" или "-HH:MM"
        return f"{sign}{hours:02d}:{minutes}"

    @field_validator('format')
    @classmethod
    def validate_and_fill_format(cls, v: Optional[str], info) -> Optional[str]:
        """
        Если format не задан подставляем дефолт на основе base.
        Валидируем формат через parse_format_pattern
        Если это не Unix сек/миллисек, проверяем, что datetime.strftime(user_format) не падает.
        """
        # достаём base
        base_value: TimeBaseType = info.data.get("base")

        if v is None:
            # дефолтный формат
            try:
                pattern = BASE_DEFAULT_FORMAT[base_value]
            except KeyError:
                raise ValueError(f"No default format for base={base_value!r}")
        else:
            pattern = v.strip()
            if not pattern:
                raise ValueError("format must not be an empty string")

        # Разбираем и конвертим в strftime/Unix
        strftime_pattern, is_unix_seconds, is_unix_millis = parse_format_pattern(pattern)

        if not (is_unix_seconds or is_unix_millis):
            # Если не Unix — чекаем через strftime
            try:
                _ = datetime.now().strftime(strftime_pattern)
            except Exception as e:
                raise ValueError(f"Invalid format pattern (failed in strftime): {e}")

        # В БД храним ориганл (YYYY-MM-DD, X)
        return pattern

# ####


VariableConfig = Annotated[
    Union[SimpleVariableConfig, TimeVariableConfig],
    Field(discriminator='type')
]


class VariablesDetailsBase(BaseModel):
    variable_name: Annotated[
        str,
        StringConstraints(
            max_length=255,
            pattern=r'^[a-zA-Z0-9_]+$',  # Только латиница, цифры и подчёркивание
        )
    ]
    variable_config: VariableConfig
    variable_description: Optional[str] = None

    @field_validator('variable_name')
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        if ' ' in v:
            raise ValueError("The variable name must not contain spaces!")
        if not re.fullmatch(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(
                "The variable name must contain only Latin letters, numbers and underscores!"
            )
        return v


class VariablesDetailsCreate(VariablesDetailsBase):
    variables_kit_id: UUID4


class VariablesDetailsRead(VariablesDetailsBase):
    variable_details_id: UUID4
    variables_kit_id: UUID4
    computed_value: Optional[str] = None

    class Config:
        from_attributes = True


class VariablesDetailsUpdate(BaseModel):
    variable_name: Optional[
        Annotated[
            str,
            StringConstraints(
                max_length=255,
                pattern=r'^[a-zA-Z0-9_]+$',
            )
        ]
    ] = None
    variable_config: Optional[VariableConfig] = None
    variable_description: Optional[str] = None

    @field_validator('variable_name')
    @classmethod
    def validate_variable_name(cls, v: str | None) -> str | None:
        if v is None:
            return None  # Пропускаем, если поле не передано
        if ' ' in v:
            raise ValueError("The variable name must not contain spaces!")
        if not re.fullmatch(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError(
                "The variable name must contain only Latin letters, numbers and underscores!"
            )
        return v
