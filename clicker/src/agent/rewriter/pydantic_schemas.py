from typing import Annotated, ClassVar, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ClickAction(BaseModel):
    action_type: Literal["CLICK"] = Field(..., description="Action type")
    element_description: str = Field(
        ...,
        description='Comprehensive description of the element including name, type, position, and other distinguishing attributes like color or size. Example: "Login button at the top right corner", "Red delete icon next to the user name".',
    )


class TypeAction(BaseModel):
    action_type: Literal["TYPE"] = Field(..., description="Action type")
    text_to_type: str = Field(
        ..., description="Text to type. Should be kept exactly as is."
    )
    element_description: str = Field(
        ...,
        description='Comprehensive description of the input element including name, type, position, and other distinguishing attributes like size. Example: "Email address input field", "Search box at the top of the page".',
    )


class HoverAction(BaseModel):
    action_type: Literal["HOVER"] = Field(..., description="Action type")
    element_description: str = Field(
        ...,
        description='Comprehensive description of the element including name, type, position, and other distinguishing attributes like color or size. Example: "Settings dropdown menu", "User avatar in the top bar".',
    )



class ClearAction(BaseModel):
    action_type: Literal["CLEAR"] = Field(..., description="Action type")
    element_description: str = Field(
        ...,
        description='Comprehensive description of the input element including name, type, position, and other distinguishing attributes like size. Example: "Password field", "Search input in the navigation bar".',
    )


class PressAction(BaseModel):
    action_type: Literal["PRESS"] = Field(
        ..., description="Action used to press a keyboard key or combination of keys."
    )
    key_to_press: str = Field(
        ...,
        description="Key or combination of keys to press. Example: 'Enter', 'Ctrl+KeyA', 'Shift+Tab'.",
    )

    VALID_KEYS: ClassVar[List[str]] = [
        "Backquote",
        "Minus",
        "Equal",
        "Backslash",
        "Backspace",
        "Tab",
        "Delete",
        "Escape",
        "ArrowDown",
        "End",
        "Enter",
        "Home",
        "Insert",
        "PageDown",
        "PageUp",
        "ArrowRight",
        "ArrowUp",
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
        "F9",
        "F10",
        "F11",
        "F12",
        "Digit0",
        "Digit1",
        "Digit2",
        "Digit3",
        "Digit4",
        "Digit5",
        "Digit6",
        "Digit7",
        "Digit8",
        "Digit9",
        "KeyA",
        "KeyB",
        "KeyC",
        "KeyD",
        "KeyE",
        "KeyF",
        "KeyG",
        "KeyH",
        "KeyI",
        "KeyJ",
        "KeyK",
        "KeyL",
        "KeyM",
        "KeyN",
        "KeyO",
        "KeyP",
        "KeyQ",
        "KeyR",
        "KeyS",
        "KeyT",
        "KeyU",
        "KeyV",
        "KeyW",
        "KeyX",
        "KeyY",
        "KeyZ",
        "Shift",
        "Control",
        "Alt",
        "Meta",
        "ShiftLeft",
        "ControlOrMeta",
    ]



class ScrollAction(BaseModel):
    action_type: Literal["SCROLL"] = Field(
        ..., description="Action used to scroll the page to the target element."
    )
    scroll_target: str = Field(
        ...,
        description='Comprehensive description of the scroll target element including name, type, position, and other distinguishing attributes like color or size. Example: "Table at the bottom of the page", "Comments section".',
    )



class InnerScrollAction(BaseModel):
    action_type: Literal["INNER_SCROLL"] = Field(
        ...,
        description="Action used to scroll scrollable container to the target element.",
    )
    container_description: str = Field(
        ...,
        description='Comprehensive description of the scrollable container including name, type, position, and other distinguishing attributes. Example: "Language selection dropdown", "Left sidebar with user list".',
    )
    scroll_target: str = Field(
        ...,
        description='Name/text of the target element to scroll into view. Example: "Русский", "Today\'s meeting", "\'Telegramm\' icon".',
    )


class WaitAction(BaseModel):
    action_type: Literal["WAIT"] = Field(
        ...,
        description="Action used to wait for a specific element to appear or just wait for a certain time period.",
    )
    wait_time: float = Field(
        default=30,
        description="Time to wait in SECONDS, if not specified, use default value of 30 seconds.",
    )
    element_description: Optional[str] = Field(
        None,
        description='Optional: Comprehensive description of the element to wait for. Only include if user asked to wait for specific element. Example: "Loading spinner", "Confirmation dialog".',
    )



class NewTabAction(BaseModel):
    action_type: Literal["NEW_TAB"] = Field(..., description="Action type")
    tab_name: str = Field(..., description="URL for new tab.")


class SwitchTabAction(BaseModel):
    action_type: Literal["SWITCH_TAB"] = Field(..., description="Action type")
    tab_name: str = Field(..., description="URL or title of tab to switch to.")



class ReadAction(BaseModel):
    action_type: Literal["READ"] = Field(..., description="Action type")
    instruction: str = Field(
        ...,
        description="What text to read/extract from the screen. Keep exactly as provided by user.",
    )
    storage_key: str = Field(
        ...,
        description='Variable name to store the read text under, without curly braces. Example: for {{verification_code}} use "verification_code".',
    )


class PasteAction(BaseModel):
    action_type: Literal["PASTE"] = Field(..., description="Action type")
    element_description: str = Field(
        ...,
        description='Comprehensive description of the input element to paste into including name, type, position, and other distinguishing attributes. Example: "Verification code input field", "Order number text box".',
    )
    storage_key: str = Field(
        ...,
        description="Key of the previously stored text to paste. Must match a storage_key from a previous READ action.",
    )


class SelectAction(BaseModel):
    action_type: Literal["SELECT"] = Field(
        ...,
        description="Action used to select an option from a dropdown or select element.",
    )
    element_description: str = Field(
        ...,
        description='Comprehensive description of the select/dropdown element including name, type, position, and other distinguishing attributes. Example: "Sort by dropdown", "Language selection menu".',
    )
    option_value: str = Field(
        ...,
        description='Value or visible text of the option to select from the dropdown. Keep exactly as provided by user. Example: "date", "Ипотека для IT".',
    )


class UnsupportedAction(BaseModel):
    action_type: Literal["UNSUPPORTED"] = Field(
        ..., description="Action used to indicate that the step is not a valid action."
    )
    reason: str = Field(
        ...,
        description="Explanation of why this action is unsupported. For example, if the step is not a valid action for inputs like 'Swipe image to the right' return explanation of why it's not a valid action.",
    )


Action = Annotated[
    Union[
        ClickAction,
        TypeAction,
        HoverAction,
        ClearAction,
        PressAction,
        ScrollAction,
        InnerScrollAction,
        WaitAction,
        NewTabAction,
        SwitchTabAction,
        ReadAction,
        PasteAction,
        SelectAction,
        UnsupportedAction,
    ],
    Field(discriminator="action_type"),
]


class ActionPlan(BaseModel):
    """
    Legacy-compatible action plan schema.
    Includes PASTE to keep old backend payloads parseable.
    """
    actions: List[Action] = Field(..., description="List of actions.")


RewriterAction = Annotated[
    Union[
        ClickAction,
        TypeAction,
        HoverAction,
        ClearAction,
        PressAction,
        ScrollAction,
        InnerScrollAction,
        WaitAction,
        NewTabAction,
        SwitchTabAction,
        ReadAction,
        SelectAction,
        UnsupportedAction,
    ],
    Field(discriminator="action_type"),
]


class RewriterActionPlan(BaseModel):
    """
    Strict rewriter output schema.
    Does not allow PASTE.
    """
    actions: List[RewriterAction] = Field(..., description="List of actions.")


class MultiActionSteps(BaseModel):
    step_numbers: List[int] = Field(
        default_factory=list,
        description="List of step numbers that contain multiple actions/instructions."
    )
