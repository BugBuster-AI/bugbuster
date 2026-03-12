def prompt__td_kf_act_intro(task_descrip, ui_name, language):
    return f"""# Task

Rewrite the user actions from logs and screenshots into a description of test steps.
You need to pay special attention to describing the elements the user interacts with on the screen.

---

# User Interface

The workflow takes place inside the software called **{ui_name}**. Use your knowledge of {ui_name} to help complete the task.
Description: {task_descrip}

---

# Workflow Demonstration

You are provided with:

* A sequence of annotated screenshots (with red crosses or other highlights) showing the user's actions in context.
* User interactions with the interface, annotated with a red cross cursor and the corresponding action.
* A series of actions recorded in a simple DSL (domain-specific language).
* If there is an interaction with a specific element, such as a click, text input, mouse hover, or another action, you need to determine which element it refers to and describe it **from the broader context to the more specific one**. **Example**: “In the product card of the pink hoodie, click the ‘Add to Cart’ button.”
* If the action involves scrolling or hovering, you need to take the description from the next step. For example, if we see a scroll action followed by a click on the pink hoodie card, then you should write: “Scroll to the product card of the pink hoodie.”

Your task is to **translate** these DSL actions into a test case description.

---

## Special instructions for working with images

### 1. **Compare sequential screenshots** to determine:

* Menus, pop-ups, or dropdown lists that appeared without a direct `CLICK` in the DSL.
* If a new menu or window appeared in the next screenshot without a click, add a **`HOVER`** action between steps to explain its appearance.
* Do not replace existing clicks with hovers — only add missing ones.
* In `HOVER`, always specify the element to hover over in order to display the next element.
* **Important**: The DSL may not capture all actions, so use logic to fill in missing steps.
  For example: if the user changed a color, opened a list, or changed the product quantity, but the DSL doesn’t have this, add the missing steps as separate atomic actions.

### 2. **Look for scrolling**:

* If the new screenshot shows a different part of the interface and the logs do not include a click or hover that explains this, add a **`SCROLL`** or **`INNER_SCROLL`** action.
* Use “scroll to the next element” in the action description, referring to the relevant element.
* If there is inner scrolling (e.g., in a dropdown list), use `INNER_SCROLL`.
* In `SCROLL` and `INNER_SCROLL`, always specify the element you are scrolling to, and you can take the element description from the next action.

### 3. **Positional descriptions**:

* Always add an ordinal number or the position of the element (order number, row, column, etc.).
* If there are multiple similar elements (icons, buttons, links), always provide a detailed description:

  * “Star icon, fifth in order, located between the settings icon and the search icon.”
  * “Secondary ‘Add to Cart’ button in the product list.”
* Even if the element is unique, provide enough context to avoid ambiguity.

### 4. **Element naming**:

* Use visible labels (e.g., “Sign In”) or a unique identifier.
* If there is no text, use a description of its function + position (e.g., “menu icon in the top right corner”).
* Do not use HTML/CSS.

### 5. **Never** disclose personal data.

### 6. **Multi-level menus**:

* If a submenu appears without a click, add a `HOVER` action on the parent element.

### 7. **If a click is on an icon and there are multiple icons**, specify the ordinal number or a detailed description.

### 8. **Text input**:

* If text input happened in a single field and there were no further checks, combine into one step and take the final input from the last action in the DSL.

### 9. **Screenshot is the primary source of truth**:

* The DSL log is only a technical hint. Always derive element names, labels, and context from the screenshot.
* Look at the red cross/marker on the screenshot to identify the exact element the user interacted with.
* Describe each action so precisely that it **cannot be interpreted in any other way**. Always include:
  - The visible label or text of the element
  - The surrounding context (which form, section, panel, menu, or page area it belongs to)
  - Enough detail to distinguish this element from any similar elements on the page

**Good examples** (unambiguous):
- "Click the 'Sign In' button in the login form" — clear which button and where
- "Type 'admin' in the 'Username' input field of the login form" — clear which field and what to type
- "Click the 'Generative AI' icon in the feature cards section on the main page" — clear which icon and its location
- "Select 'Guides' from the top navigation dropdown menu" — clear which menu item and where

**Bad examples** (ambiguous, never write like this):
- "Click the button" — which button?
- "Enter text in the field" — which field? what text?
- "Click the link" — which link?
- "Navigate to the page" — how exactly?

---

We follow the rule **one instruction — one action**.
**Example**:

```json
{{
  "instructions": [
    "Scroll down to the 'MCP guide' button in the 'Getting Started' section",
    "Click the 'MCP guide' button in the 'Getting Started' section"
  ]
}}
```

---

Response format:
{{
    "thoughts": "<Describe  in detail every element the user interacted with, but only last screenshot>",
    "observation": "<Check the conditions for adding hover, scroll, or inner scroll>",
    "instructions": [
        "<Describe the actions that need to be repeated to achieve the same result as the user. Write in {language}>"
    ]
}}
"""



def prompt__td_kf_act_close():
    return """
# Instructions for Final Output

Now, based on:
1) The DSL actions given,
2) The screenshot-by-screenshot analysis,
3) The rules outlined above,

**Write a structured list of actions** that completes the workflow. Each action is an **object** with the following structure (all fields are required, but may be empty strings if not applicable):

- `action_type` (Optional): Must be one of `"CLICK"`, `"TYPE"`, `"HOVER"`, `"SCROLL"`, `"CLEAR"`, `"PRESS"`, or `"INNER_SCROLL"`.
- `element_type` (Optional): The UI element’s type or role, e.g. `"button"`, `"input field"`, `"dropdown"`, `"menu"`. If uncertain, `""`.
- `element_name` (Optional): The textual or functional label of the element (e.g., `"Log in"`, `"username"`, `"Add to Cart"`). If no label is shown, use a short descriptive phrase (e.g., `"color picker"`, `"menu"`, etc.). 
- `positional_description` (Optional): A **highly specific** phrase clarifying the element’s location among similar or neighboring elements, icons, emojies, buttons with order number e.g. For 'Star' icon (nemu item): `"the fifth one in order, is located between the settings icon and the search icon."`. Doesn't contain element name, only location. 
  - If the element is obviously unique (e.g., a big “Log In” button in the center), you may keep it short but still be explicit. 
  - If the element is repeated or has multiple occurrences, use an ordinal reference or an adjacency reference (e.g. “the second item from the left in the top navigation bar”). 
  - If element is on the grid or between other elements you MUST use ordinal number or other descriptive phrase to disambiguate e.g. "located top left corner, eleventh button from the right side of the header bar."
  - Resist using minimal or vague descriptors. Provide enough detail to prevent confusion.
- `text_to_type` (Optional): If `action_type = "TYPE"`, specify the text typed. (Required for TYPE actions.)
- `key_to_press` (Optional): If `action_type = "PRESS"`, specify which key.
- `scroll_element_name` (Optional): If `action_type = "INNER_SCROLL"`, specify which element is being scrolled inside.

### Additional Points to Remember

1. **Always add `HOVER`** when a menu or popup appears in a new screenshot without a clear `CLICK` trigger in the DSL.  
2. **Do not** replace a recorded `CLICK` with a `HOVER`. Instead, insert `HOVER` only if the user must have hovered over a parent or higher-level menu to make a sub-menu appear.  
3. **Add `SCROLL`** or `INNER_SCROLL` if the user must have scrolled the interface (or an internal scrollable area) to reveal new elements.  
4. **Positional descriptions** must be sufficiently detailed to disambiguate similar or repeated elements.  
5. Keep the final output as valid JSON, with a top-level object:  
```json
{
  "actions": [
    {
      "action_type": "...",
      "element_type": "...",
      "element_name": "...",
      "positional_description": "...",
      "text_to_type": "...",
      "key_to_press": "...",
      "scroll_element_name": "..."
    },
    ...
  ]
}
```
6. Avoid any mention of raw HTML/CSS.  
7. Do not reveal any personal or sensitive data from the screenshots.  
8. If an action clearly occurred, but it’s absent in the DSL, **add it** to the action list (for example, changing a dropdown selection or adjusting a slider).  
9. The final “actions” array must reflect the actual user sequence, with any necessary `HOVER` or scrolling inserted.

10. Filled ouput example:
```json
{
    "actions": [
        {
            "action_type": "CLICK",
            "element_type": "checkbox",
            "element_name": "Remember me"
        },
        {
            "action_type": "CLICK",
            "element_name": "Log in"
        },
        {
            "action_type": "HOVER",
            "element_type": "menu",
            "element_name": "Products"
        },
        {
            "action_type": "CLICK",
            "element_type": "menu",
            "element_name": "Products"
        },
        {
            "action_type": "CLICK",
            "element_type": "subsection",
            "element_name": "Products",
            "positional_description": "under the 'Products' menu in the left sidebar"
        },
        {
            "action_type": "SCROLL",
            "element_name": "Endless Night"
        },
            "action_type": "CLICK",
            "element_type": "menu_item",
            "element_name": "Star icon",
            "positional_description": "the fifth one in order, is located between the settings icon and the search icon.” or “the topmost of the two product links"
        },
        {
            "action_type": "CLICK",
            "element_type": "emoji",
            "element_name": "car",
            "positional_description": "at the second row, fifth column, the fifth in order, is located between bus and truck emojis."
        }
        {
            "action_type": "CLICK",
            "element_type": "button",
            "element_name": "Edit",
            "positional_description": "located second row, fourth item from the left, under the product image."
        },
        {
            "action_type": "INNER_SCROLL",
            "element_type": "dropdown",
            "element_name": "Edition",
            "scroll_element_name": "ebook"
        }
    ]
}
```

**Note**: Omit any unused optional fields (e.g., do not include `"text_to_type"` if the action type is `"CLICK"`).  
**Note**: Pay attention to general changes on the sreen to properly identify actions taken by user even if no intermediate screenshot provided.

Do not forget to add 'HOVER' actions when needed.

**Now, please generate the final** `ActionList` **JSON** (exactly matching the schema above) using the best interpretation of the screenshots + DSL actions:
"""
