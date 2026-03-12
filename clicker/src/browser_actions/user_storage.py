import sys

sys.path.append('.')
import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional, Tuple, Union

from dateutil.relativedelta import relativedelta
from fuzzywuzzy import process
from pydantic import (
    BaseModel,
    Field,
    TypeAdapter,
    field_validator,
)
from typing_extensions import Annotated

from core.config import logger

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


def get_base_local_datetime(base: TimeBaseType,
                            local_now: datetime) -> datetime:
    """
    base считается в ЛОКАЛЬНОМ времени юзера
    local_now — наивный datetime в utc_offset

    "currentDate": "YYYY-MM-DD",
    "today": "YYYY-MM-DD",
    "yesterday": "YYYY-MM-DD",
    "tomorrow": "YYYY-MM-DD",
    "currentTime": "HH:mm:ss",
    "dateTime": "YYYY-MM-DD HH:mm:ss",
    "startOfDay": "YYYY-MM-DD HH:mm:ss",
    "endOfDay": "YYYY-MM-DD HH:mm:ss",
    "timestamp": "X"

    """
    # начало локального дня
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    if base in ("currentTime", "dateTime", "timestamp"):
        dt_local = local_now
    elif base in ("today", "currentDate"):
        dt_local = day_start
    elif base == "yesterday":
        dt_local = day_start - timedelta(days=1)
    elif base == "tomorrow":
        dt_local = day_start + timedelta(days=1)
    elif base == "startOfDay":
        dt_local = day_start
    elif base == "endOfDay":
        dt_local = day_start.replace(hour=23, minute=59, second=59, microsecond=0)
    else:
        dt_local = local_now

    return dt_local


def apply_utc_offset(dt_utc: datetime, utc_offset: Optional[str]) -> datetime:
    """
    Переводим в часовой пояс юзера или utc
    Если utc_offset не задан, считаем, что это +0:00
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)

    # если offset не задан — работаем в UTC+0 как локальном времени
    if utc_offset is None:
        return dt_utc.replace(tzinfo=None)

    m = re.fullmatch(r'^([+-])(\d{2}):(\d{2})$', utc_offset)
    if not m:
        return dt_utc.replace(tzinfo=None)

    sign, hh, mm = m.groups()
    hours = int(hh)
    minutes = int(mm)
    delta = timedelta(hours=hours, minutes=minutes)
    if sign == '-':
        delta = -delta

    target_dt = dt_utc + delta
    # локальный datetime юзера без таймзоны, для сдвигов ок
    return target_dt.replace(tzinfo=None)


def apply_shifts(dt: datetime, shifts: Optional[list[TimeShift]]) -> datetime:
    """сдвиги из массива shifts
        применяются от больших к меньшим:
        - y (years) - добавляются/вычитаются годы
        - M (months) - добавляются/вычитаются месяцы
        - d (days) - добавляются/вычитаются дни
        =========
        - h (hours) - добавляются/вычитаются часы
        - m (minutes) - добавляются/вычитаются минуты
        - s (seconds) - добавляются/вычитаются секунды
        Отрицательные значения вычитают соответствующий период."""

    if not shifts:
        return dt

    years = 0
    months = 0
    days = 0
    seconds = 0  # h/m/s в секундах

    for shift in shifts:
        v = shift.value
        u = shift.unit
        if u == "y":
            years += v
        elif u == "M":
            months += v
        elif u == "d":
            days += v
        elif u == "h":
            seconds += v * 3600
        elif u == "m":
            seconds += v * 60
        elif u == "s":
            seconds += v

    if years or months or days:
        dt = dt + relativedelta(years=years, months=months, days=days)

    if seconds:
        dt = dt + timedelta(seconds=seconds)

    return dt


def format_datetime_with_pattern(dt: datetime, pattern: str) -> str:
    """
    dt — ЛОКАЛЬНОЕ время (наивное).
    X / x считаем как Unix-время от этого момента"""

    strftime_pattern, is_unix_seconds, is_unix_millis = parse_format_pattern(pattern)

    if is_unix_seconds:
        # трактуем dt как UTC-момент для timestamp()
        return str(int(dt.replace(tzinfo=timezone.utc).timestamp()))
    if is_unix_millis:
        return str(int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000))

    return dt.strftime(strftime_pattern)


def compute_time_value(config: TimeVariableConfig,
                       now_utc: Optional[datetime] = None) -> str:
    # текущее время в UTC
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    elif now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    # Переводим UTC в часовой пояс юзера, если есть
    local_now = apply_utc_offset(now_utc, config.utc_offset)

    # расчет базового значения, например  yesterday
    base_local = get_base_local_datetime(config.base, local_now)

    # Сдвиги
    dt_shifted = apply_shifts(base_local, config.shifts)

    # Формат (кастомный или дефолтный для base)
    pattern = config.format or BASE_DEFAULT_FORMAT[config.base]
    return format_datetime_with_pattern(dt_shifted, pattern)


def compute_variable_value(variable_config: VariableConfig,
                           now_utc: Optional[datetime] = None) -> Optional[str]:
    if isinstance(variable_config, SimpleVariableConfig):
        return variable_config.value
    if isinstance(variable_config, TimeVariableConfig):
        return compute_time_value(variable_config, now_utc=now_utc)
    return None


variable_config_adapter = TypeAdapter(VariableConfig)


def compute_variable_value_from_raw_config(raw_config: Any,
                                           now_utc: Optional[datetime] = None) -> Optional[str]:
    """
    variable_config  JSON из БД:
      {"type": "time", "base": "...", ...} или {"type": "simple", "value": "..."}.

    Преобразовываем в VariableConfig
    """
    # валидация по нужному подтипу (simple / time)
    variable_config = variable_config_adapter.validate_python(raw_config)

    return compute_variable_value(variable_config, now_utc=now_utc)


class UserStorage:
    """
    новый формат value > Dict
    "user_storage": {

        "now_utc4469": {
            "type": "time",
            "base": "currentTime",
            "utc_offset": "+3:00",
            "shifts": [
                {
                    "value": -1,
                    "unit": "d"
                },
                {
                    "value": 2,
                    "unit": "h"
                }
            ],
            "format": "YYYY-MM-DD HH:mm",
            "is_const": true
        },
        "now_utc4470": {
            "type": "time",
            "base": "currentTime",
            "utc_offset": "-12:45",
            "shifts": [
                {
                    "value": -1,
                    "unit": "d"
                },
                {
                    "value": 2,
                    "unit": "h"
                }
            ],
            "format": "YYYY-MM-DD HH:mm",
            "is_const": false
        },
        "login": {
            "type": "simple",
            "value": "string"
        }

        }
    }"""
    def __init__(self, initial_data: dict = None):
        self.data = initial_data if initial_data is not None else {}

    def set(self, key, value):
        # ! через установку мы всегда ставим значение как simple
        # учесть если это изменится, например через апи шаги можно будет поставить не только response
        self.data[key] = {"type": "simple", "value": value}
        logger.info(f"UserStorage set {key=}: {value}")

    def update(self, key, value):
        if key in self.data:
            if isinstance(self.data[key], dict):
                self.data[key]["value"] = value
        else:
            logger.info("Key not found in storage.")

    def delete(self, key):

        if key in self.data:
            del self.data[key]
        else:
            logger.info("Key not found in storage.")

    def get_value(self, key, strict=True, score_threshold=60):

        variable_config = None

        if strict:
            variable_config = self.data.get(key, None)
        else:
            keys = list(self.data.keys())
            if keys:
                best_match = process.extractOne(key, keys)
                if best_match and best_match[1] > score_threshold:
                    print("best_match", best_match)
                    variable_config = self.data[best_match[0]]

        if isinstance(variable_config, dict):
            is_const = variable_config.get("is_const", False)
            # динамическая переменная - расчитаем актуальное значение для time
            if not is_const:
                calc_value = compute_variable_value_from_raw_config(variable_config)
                variable_config["value"] = calc_value

            return variable_config.get("value", None)

        return None

    # async def value_to_browser_clipboard(self, page: Page, value: str):
    #     if not page.url.startswith('https'):
    #         raise Exception("Clipboard working only https. Use fill or type")
    #     await page.evaluate("text => navigator.clipboard.writeText(text)", value)

    # async def get_value_from_browser_clipboard(self, page: Page) -> str:
    #     if not page.url.startswith('https'):
    #         raise Exception("Clipboard working only https. Use fill or type")
    #     return await page.evaluate("() => navigator.clipboard.readText()")


async def main():
    from playwright.async_api import async_playwright
    from tab_manager import TabManager

    storage = UserStorage({'login': 'test_from_clipboard', 'password': '123456Test'})

    # crud
    storage.add('url', 'google.ru')

    storage.update('eyery', 'eryery')
    storage.update('url', 'yandex.ru')

    storage.delete('dyhd')
    storage.delete('url')

    # search
    print(storage.get_value('url', strict=True))
    print(storage.get_value('log', strict=False))
    print(storage.get_value('lg', strict=False))

    # clipboard
    ####################################
    width = 1024
    height = 768
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context(
            permissions=['geolocation'],
            viewport={"width": width, "height": height},
            locale="en-US",
            bypass_csp=True,
            ignore_https_errors=True,
            # record_video_dir=f"test_video",
            # record_video_size={"width": width, "height": height},
            extra_http_headers={
                "Accept": "image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
            }
        )

        tab_manager = TabManager(context)
        page = await tab_manager.initialize_pages()

        #########################################

        await tab_manager.navigate("https://ya.ru", page)

        # use clipboard
        # 1. get_value from storage
        val = storage.get_value('log', strict=False)
        # 2. put value to clipboard

        await storage.value_to_browser_clipboard(page, val)

        # 3. check browser clipboard
        test_val = await storage.get_value_from_browser_clipboard(page)
        print(test_val == val, test_val)

        # await page.mouse.click(float(x_abs), float(y_abs))
        await page.click('input#text')

        # paste from   clipboard
        await page.wait_for_timeout(100)
        await page.keyboard.press('Control+v')

        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
