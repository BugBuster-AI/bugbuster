"""
Playwright codegen LLM prompts (draft + repair). Edit here; logic stays in llm_steps.py.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from codegen.codegen_limits import (
    MAX_A11Y_SNAPSHOT_CHARS,
    MAX_PAGE_HTML_CHARS,
    MAX_PRIOR_JS_CHARS,
    MAX_PRIOR_STEPS_CHARS,
    MAX_TRACE_BLOCK_CHARS,
    MAX_VLM_ACTION_BLOCK_CHARS,
    MAX_VLM_LOG_CHARS,
    MAX_VLM_BEFORE_FULL_HTML_CHARS,
    MAX_VLM_FOCUSED_DOM_PROMPT_CHARS,
)

# Bump when instructions change materially (stored in codegen metadata).
PROMPT_VERSION = "codegen_mvp_v32"

# Синхронизируйте детали с tests/«Регламент генерации локаторов для ИИ-агента автотестирования (Playwright + JavaScript).txt»
LOCATOR_POLICY_REFERENCE = (
    "Human-oriented locator reference (RU): tests/«Регламент генерации локаторов для ИИ-агента автотестирования (Playwright + JavaScript).txt». "
    "This codegen pipeline overrides it with CSS/XPath-only rules below (no getBy* helpers). POM does not apply."
)

# Краткие правила в system (English); длинный RU-регламент не дублируем — см. LOCATOR_POLICY_REFERENCE.
LOCATOR_REGULATION_SHORT = """
Locator strategy (Playwright JS, linear code only — no Page Object classes):
- **Disallowed — do not emit:** `page.getByRole`, `page.getByTestId`, `page.getByText`, `page.getByLabel`, `page.getByPlaceholder`, `page.getByAltText`, `page.getByTitle`, or any `.getBy*` on `page` or on locators. This pipeline uses explicit selectors only.
- **Required:** build every locator with `page.locator('...')` and chained `.locator('...')` using **CSS selectors** or **XPath** (each XPath segment must use the `xpath=` prefix, e.g. `page.locator('xpath=//button[1]')`).
- **Stable attributes (prefer in CSS):** `[id="..."]`, `[data-testid="..."]`, `[data-test="..."]`, `[data-cy="..."]`, `[name="..."]`, `[type="..."]`, `[href*="..."]`, `[aria-label="..."]`. Priority when several exist: data-testid > data-test > data-cy > data-qa > data-id > id; attributes may live on an ancestor — anchor on that node, then chain with narrower `.locator(...)`.
- **Text matching without getByText:** `locator('text=Exact')`, `locator('text=/pattern/i')`, or XPath `contains(., '...')` / `normalize-space()`; or CSS with Playwright `:has-text()` where appropriate.
- **Narrow scope:** chain from a container (`#header`, `[role="main"]`, `form`, section CSS/XPath) when multiple matches are possible. Use `.filter({ visible: true })` when duplicates or hidden nodes are likely.
- POM / component classes: not used; output only `await` expressions on `page` / `request`.

Repair / timeout: do not repeat the same failed selector; re-pick a different CSS/XPath path using HTML/a11y/trace hints — not a one-token tweak of the same chain.
"""

_SYSTEM_PROMPT_HEAD = """You are a senior test automation engineer. Target: Playwright test API in JavaScript (async/await, use `page` / `request` directly — no Page Object classes in output).
Output rules (hard contract — invalid output aborts the run; there is no fuzzy parser):
- Your entire reply MUST be one JSON object and nothing else: no markdown, no ``` fences, no commentary, no leading/trailing prose or whitespace beyond normal JSON.
- The payload MUST be valid RFC 8259 JSON parseable as-is by a standard json.loads / JSON.parse (proper escaping of quotes and newlines inside strings).
- Include exactly one top-level key "js_fragment" (string). Optionally add "notes" (string) once — use each key at most once.
- js_fragment must be valid JavaScript using `page` (Playwright Page) and/or `request` (APIRequestContext).
- Do not call page.goto; the harness already opens the test case URL before your fragment runs.
- **One top-level statement per line:** After each `await` statement, use a newline before the next `await`. Never put two or more `await ...;` sequences on the same physical line (forbidden: `await expect(a).toX(); await expect(b).toY();` on one line).
- If the API is in json_object / JSON mode, the message body is still only that one object — never wrap it or add a chain-of-thought outside the object.

"""

_SYSTEM_PROMPT_TAIL = """Reference policy: """ + LOCATOR_POLICY_REFERENCE + """

""" + LOCATOR_REGULATION_SHORT + """

Layout vs DOM (when the step reads or acts on text that sits near a visible label, caption, or heading):
- Visual proximity on the screenshot does **not** imply a simple DOM relationship (next sibling, following-sibling, “the div under the line of text”, etc.).

Draft and repair multimodal reasoning:
- NL step: intent and element type.
- Images: where the target sits (before/after from VLM; failure screenshot on repair).
- **Draft:** when **VLM full-page HTML BEFORE this step** and/or **focused DOM before step** (url + candidates) are provided, use them as primary ground truth for locator candidates (data-*, id, role, aria) before relying on screenshots alone.
- **Repair:** rely on the **serialized page HTML at validation failure** (`Page HTML snapshot at validation failure`) plus the **Playwright MCP accessibility snapshot**. VLM coordinates and trace hint disambiguate intent — they do not replace the failure-time DOM when the page state has changed after the VLM run.

Repair protocol (when fixing after MCP/Playwright error — apply in order):
1) Identify the target element using the **page HTML at validation failure** and the **MCP accessibility snapshot**. Use VLM coordinates and/or trace hint (selector/position from the successful VLM run) only to disambiguate which node matches the NL intent — coordinates are in the same viewport as the test case.
2) Build a Playwright locator from that node’s stable attributes using **only** `page.locator` + CSS or `xpath=` (no getBy* helpers), not by renaming variables or tweaking the same broken chain.
3) Emit a new js_fragment; cosmetic edits alone are not a valid fix.

Playwright selector engines (critical — wrong engine causes runtime errors like "Unexpected token ':' while parsing css selector"):
- `page.locator('...')` and `someLocator.locator('...')` use the CSS engine by default. A string like `following-sibling::div` or `//div` is NOT valid CSS; Playwright will try to parse it as CSS and fail.
- To use XPath: you MUST use the xpath engine prefix, e.g. `page.locator('xpath=//div')`, or chain: `page.locator('text=Label').locator('xpath=./following-sibling::div')`. Relative XPath after a locator should often start with `./`.
- Never pass bare XPath axes (`following-sibling::`, `ancestor::`, `//`, `@href`) inside `.locator('...')` unless the argument starts with `xpath=`.
- Chaining: if the left-hand side is already `page.locator('xpath=…')` or any xpath-based locator, the next `.locator('following-sibling::div')` is still parsed as CSS unless you write `.locator('xpath=./following-sibling::div')`. There is no “inherit xpath engine” — each chained `.locator` needs `xpath=` when using axes.
- Prefer shorter CSS when it is stable; use XPath when CSS cannot express the relationship (axes, text(), position). Do not use getBy* APIs — see locator strategy above.
- For CSS: standard CSS selectors only inside `.locator('css-here')` or default `locator('css-here')`.

Prefer short js_fragment: a small sequence of await calls for ONE NL step.
- Never emit long repetitive chains (e.g. ten identical `.locator('xpath=./following-sibling::div')`). Use one or two locators, or XPath with a position predicate if needed. Repetition blows the token limit and breaks JSON.

When repairing after a timeout, switching only innerText vs textContent, or renaming variables, does NOT count as a new locating strategy — you must change anchors/parents/selectors.

Placeholders {{name}} in the NL step (TYPE / fill / вставить …):
- These are **case authoring placeholders**, not literal text to type into inputs.
- Earlier steps in the same scenario assign captured values to JavaScript bindings, e.g. `const login = await ...` and `const password = await ...`.
- For fill/type steps you MUST pass the **identifier** as an expression: `await page....fill(login)` or `.fill(password)` — **no quotes** around the variable name.
- **Wrong:** `.fill('{{login}}')`, `.fill("{{password}}")` — that types brace characters and breaks the test.
- **Right:** `.fill(login)` / `.fill(password)` when those `const` names exist upstream in the accumulated script. Match the placeholder token: `{{login}}` → identifier `login`, `{{password}}` → `password`.
- If the NL uses a different label (e.g. test_user) but the placeholder is `{{login}}`, still use the JS name that matches the placeholder (`login`), unless the NL explicitly defines another binding name in the same step.

Single function scope (avoid SyntaxError: Identifier has already been declared):
- All step fragments concatenate into **one** `async (page) => { ... }`. There is only one function scope — not one scope per step.
- **Case-variable literals:** The harness may insert `const name = "<value>";` **at most once per placeholder name** for the whole scenario (first step that needs the literal). Later steps with the same `{{name}}` reuse the identifier — **do not** emit another `const name = ...` for that placeholder.
- **Per-step prefix:** `prior_js_prefix` may include such a `const` line when this step's NL still references `{{name}}` and the name was not yet bound (not for READ capture targets — those are declared in the step fragment as `const name = await ...`).
- For **READ** steps that store into `{{name}}`, **do not** expect a prior `const name` for that placeholder — emit a single `const name = await ...` (or equivalent) in your fragment for that binding.
- If an earlier line already declares `name`, a later step must **not** emit `const name` again — use the identifier only or assign without `const` per normal JS rules.
- If two READ steps must store into the same logical name, only the first may use `const`; later steps assign without redeclaring.
"""

SYSTEM_PROMPT = _SYSTEM_PROMPT_HEAD + _SYSTEM_PROMPT_TAIL

# Expected-result steps: assertions only (web-first expect), same locator rules as action codegen (no getBy*).
_SYSTEM_PROMPT_ER_TAIL = """Reference policy: """ + LOCATOR_POLICY_REFERENCE + """

""" + LOCATOR_REGULATION_SHORT + """

This step type is **expected_result**: output **only UI assertions** for the natural-language expectation. Do **not** navigate (`page.goto`), do **not** perform clicks/fill/keyboard unless the NL explicitly requires a harmless wait for readiness via **web-first** locators + `expect` (prefer asserting visible state instead of acting).

**User-visible behavior:** Prefer checks that mirror what the user sees (text, labels, roles via CSS `[role=...]`, `[aria-label]`, stable `data-*`, visible copy). Avoid brittle layout-only chains (`div > div > li`) unless unavoidable; if you must use a fragile XPath/CSS path, add a short `//` comment in js_fragment explaining why.

**Web-first assertions (mandatory):** Use Playwright **`expect(locator)`** / **`expect(page)`** matchers with auto-wait — **not** `expect(await locator.isVisible()).toBe(true)` or other synchronous patterns without retries. Allowed matchers include: `toBeVisible`, `toBeHidden`, `toBeChecked`, `toBeEnabled`, `toBeDisabled`, `toBeFocused`, `toHaveText`, `toContainText`, `toHaveValue`, `toHaveURL`, `toHaveTitle`; for disappearance use `expect(locator).not.toBeVisible()` (optionally with `{ timeout: ... }`).

**Second argument to expect:** Pass a short human-readable message string as the second argument to `expect(..., 'message')` for CI readability.

**No hard sleeps:** Never use `page.waitForTimeout` or arbitrary sleep ms; wait via assertions / locator auto-waiting.

**Multiple conditions:** If the NL requires several independent checks in one step, prefer **`expect.soft(...)`** per check so all mismatches surface. Keep the fragment compact — no long duplicated locator chains.

**No duplicate full locator chains:** Do **not** emit multiple separate `await expect(page.locator(...).locator(...)…)` lines that repeat the **same** full chain (same sequence of `page.locator` / `.locator` segments) with only a different matcher, unless the NL explicitly requires several distinct expectations on that **exact** same resolved element. A common mistake is several lines that only differ by the matcher but share one long, identical chain — that is wrong. Prefer: **one** chain bound to `const target = page.locator(...).locator(...)` and then multiple `await expect.soft(target).to…`, or a **single** assertion that matches the NL intent. Different rows/items must use **different** locators (e.g. `.filter({ hasText: … })`, `nth`, or a data attribute), not copy-paste of the same chain.

**Structured lists and tables — data vs chrome:** When the NL refers to **removal of an entry**, **no rows**, or **empty content**, target **repeatable row/item nodes** (the data layer), not **static chrome**: column headers, section titles, or labels that remain on screen when the list is empty. Asserting `not.toBeVisible()` on such chrome is often **unsatisfiable**. Prefer locators for **actual line items** or **row/card** containers, or use **count**-style checks (e.g. zero matching rows) instead of hiding a header cell.

**expect.poll:** Use only when the NL implies a value that stabilizes asynchronously; include `{ timeout, intervals, message }` with a clear `message`.

**Do not** use `toHaveScreenshot` / visual regression in this pipeline. Do **not** use `test.step` or `test.info().attach` — the harness wraps your fragment; emit only linear `await` statements.

**JSON contract:** Same as other codegen — single JSON object with `"js_fragment"` (string) and optional `"notes"`. The js_fragment must assume `expect` is **already in scope** (injected by the test harness alongside `page` and `request`).

Playwright selector engines (same as action codegen):
- `page.locator('...')` uses CSS unless the string starts with `xpath=`. Never put XPath axes inside `.locator('...')` without the `xpath=` prefix on that segment.
"""

SYSTEM_PROMPT_EXPECTED_RESULT = _SYSTEM_PROMPT_HEAD + _SYSTEM_PROMPT_ER_TAIL

STRICT_MODE_VIOLATION_PROTOCOL = """
Strict mode violation protocol (when the error contains **strict mode violation** and **`resolved to N elements:`**):
1) Recognize that the failing locator matched **more than one** element — it is invalid for strict Playwright expectations; you must replace or narrow it.
2) Find the block after `resolved to N elements:` (numbered lines `1) ...`, `2) ...`). Treat that list as a **catalog of candidate DOM matches** — use it **before** guessing from screenshots alone.
3) Pick the candidate that matches the NL intent and/or the expected assertion text.
4) Rebuild the locator so it resolves to **exactly one** element. Prefer a narrower anchor (stable container, `[data-*]`, `[id]`, distinctive class on the target) over blind `.first()`. Use `.first()` / `.nth(i)` / `.filter({ visible: true })` only as an explicit disambiguation when no better unique path exists.
5) Do **not** re-emit the same ambiguous locator with cosmetic edits — you must narrow the resolution path.
6) Lines like `aka getByText('...')` / `aka getByRole(...)` are **hints only**. Do **not** copy `getBy*` into the output — translate to `locator('text=...')`, CSS `[role="..."]`, `[aria-label="..."]`, or chained `locator` + `xpath=` per this pipeline’s rules.
"""

REPAIR_ER_HOW_TO_FIX = """How to fix (assertion / locator — obey all; CSS/XPath only, no getBy*):
1) Use the **page HTML snapshot at validation failure** and the **MCP accessibility snapshot** to see real DOM at error time.
2) Rebuild locators with **only** `page.locator` / chained `.locator` using CSS or `xpath=` — never getByRole/getByText/getByTestId.
3) If the failure is a **strict mode violation** or **timeout waiting for** an assertion target, change the locator or narrow with `.filter({ visible: true })` / `.first()` / a better anchor — not a cosmetic tweak of the same chain.
4) If the error is a **wrong expectation** (e.g. text mismatch), align `toHaveText` / `toContainText` with the NL and visible DOM; use `expect.soft` when several assertions should all run.
5) If the error mentions CSS parsing and XPath-like fragments, add the `xpath=` prefix on that segment.
6) Do not reproduce banned wait chains from the runner log verbatim — rebuild the locator chain from the snapshots.
7) If **js_fragment** repeats the same full locator chain on multiple lines, **merge** into one shared `const … = page.locator(…)` (or one `expect.soft` block) unless the NL truly needs separate checks on different elements — do not leave redundant duplicate chains.
8) If the error is `not.toBeVisible` / `Expected: not visible` but **Received: visible** on a **table header**, **column title**, or other **static list/table chrome**, the locator likely does not match what the NL describes: move the assertion to **data rows** or use a **count** of item rows — do not keep refining the same header/chrome locator.
""" + STRICT_MODE_VIOLATION_PROTOCOL


def vlm_playwright_trace_block(excerpt: Optional[str]) -> str:
    """Сырой фрагмент trace.trace (JSONL→компактные строки) для одного шага VLM-прогона."""
    if not excerpt or not str(excerpt).strip():
        return ""
    text = str(excerpt).strip()
    max_c = MAX_TRACE_BLOCK_CHARS
    if len(text) > max_c:
        text = text[:max_c] + "\n...[trace block truncated]"
    return (
        "\nPlaywright trace excerpt from the SAME successful VLM run (low-level API calls around this step; "
        "use to align selectors, text, and order — do not invent steps not reflected here):\n"
        f"---\n{text}\n---\n"
    )


def vlm_focused_dom_before_block(text: Optional[str]) -> str:
    """Focused JSON + snippet from successful VLM run (DOM before step)."""
    if not text or not str(text).strip():
        return ""
    t = str(text).strip()
    max_c = MAX_VLM_FOCUSED_DOM_PROMPT_CHARS
    if len(t) > max_c:
        t = t[:max_c] + "\n...[vlm focused dom truncated]"
    return (
        "\nVLM run — focused DOM snapshot BEFORE this step (authoritative for locator candidates; "
        "same viewport as the test case; use with images for intent):\n"
        f"---\n{t}\n---\n"
    )


def vlm_before_full_html_block(html_raw: Optional[str]) -> str:
    """Полный HTML до шага из успешного VLM-прогона — для draft вместе с focused DOM и скринами."""
    if not html_raw or not str(html_raw).strip():
        return ""
    h = html_raw.strip()
    max_c = MAX_VLM_BEFORE_FULL_HTML_CHARS
    if len(h) > max_c:
        h = h[:max_c] + "\n...html truncated"
    return (
        "\nVLM run — full page HTML BEFORE this step (authoritative DOM for this step; same viewport as the test case; "
        "pair with the MCP accessibility snapshot below; secrets may appear — treat as confidential):\n"
        f"---\n{h}\n---\n"
    )


def global_trace_summary_block(summary: Optional[str]) -> str:
    if not summary or not str(summary).strip():
        return ""
    t = str(summary).strip()
    return (
        "\nGlobal trace summary (same VLM run — beginning and end of compact API lines):\n"
        f"---\n{t}\n---\n"
    )


def vlm_run_log_block(log_excerpt: Optional[str]) -> str:
    if not log_excerpt or not str(log_excerpt).strip():
        return ""
    t = str(log_excerpt).strip()
    if len(t) > MAX_VLM_LOG_CHARS:
        t = t[:MAX_VLM_LOG_CHARS] + "\n...[log block truncated]"
    return (
        "\nTail of VLM agent run log (same run; debugging context — may be noisy):\n"
        f"---\n{t}\n---\n"
    )


def format_vlm_run_step_context(
    run_step: Optional[dict],
    *,
    read_capture_hint: Optional[str] = None,
) -> str:
    """Компактный блок: action и action_details из успешного VLM-шага (run_cases.steps)."""
    if not run_step or not isinstance(run_step, dict):
        return ""
    lines: List[str] = []
    act = run_step.get("action")
    if act is not None:
        lines.append(f"VLM action: {act}")
    if read_capture_hint is not None and str(read_capture_hint).strip():
        lines.append(
            "READ reference value (from run metadata when available — align captured text with this): "
            f"{read_capture_hint!r}"
        )
    ad = run_step.get("action_details")
    if isinstance(ad, dict):
        if ad.get("coords") is not None:
            lines.append(f"VLM action_details.coords (viewport pixels, same as test viewport): {ad.get('coords')!r}")
        if ad.get("text") is not None and str(ad.get("text")).strip():
            lines.append(f"VLM action_details.text: {ad.get('text')!r}")
        wt = ad.get("wait_time")
        if wt is not None:
            lines.append(f"VLM action_details.wait_time: {wt!r}")
        sd = ad.get("scroll_data")
        if isinstance(sd, dict) and (sd.get("deltaY") or sd.get("source")):
            lines.append(f"VLM action_details.scroll_data: {json.dumps(sd, ensure_ascii=False)[:400]}")
    block = "\n".join(lines).strip()
    if len(block) > MAX_VLM_ACTION_BLOCK_CHARS:
        block = block[:MAX_VLM_ACTION_BLOCK_CHARS] + "…"
    if not block:
        return ""
    return (
        "\nSuccessful VLM run — step instrumentation (ground truth for what the agent did; align locators and timing):\n"
        f"---\n{block}\n---\n"
    )


def prior_scenario_steps_block(flat_items_before: List[Dict[str, Any]]) -> str:
    """Список шагов сценария до текущего (порядок и step_uid для плейсхолдеров)."""
    if not flat_items_before:
        return ""
    lines: List[str] = []
    for it in flat_items_before:
        uid = it.get("step_uid", "")
        kind = it.get("kind", "")
        nl = (it.get("nl") or "").strip()
        if kind == "expected_result":
            lines.append(f"- step_uid={uid!r} [expected_result] {nl[:220]}")
        elif kind == "api":
            lines.append(f"- step_uid={uid!r} [api]")
        else:
            lines.append(f"- step_uid={uid!r} {nl[:400]}")
    text = "\n".join(lines)
    if len(text) > MAX_PRIOR_STEPS_CHARS:
        text = text[:MAX_PRIOR_STEPS_CHARS] + "\n...[prior steps truncated]"
    return (
        "\nScenario steps BEFORE this one (order matters; reuse const names from prior generated JS for {{placeholders}}):\n"
        f"---\n{text}\n---\n"
    )


def prior_js_prefix_block(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p:
        return ""
    if len(p) > MAX_PRIOR_JS_CHARS:
        p = "...[accumulated JS truncated]\n" + p[-MAX_PRIOR_JS_CHARS:]
    return (
        "\nJavaScript already generated for this scenario (runs before your fragment — reuse identifiers):\n"
        f"---\n{p}\n---\n"
    )


def draft_user_message(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    vlm_trace_excerpt: Optional[str] = None,
    vlm_run_step_context: Optional[str] = None,
    prior_steps_text: Optional[str] = None,
    prior_js_prefix: Optional[str] = None,
    global_trace_summary: Optional[str] = None,
    vlm_run_log: Optional[str] = None,
    vlm_focused_dom_before: Optional[str] = None,
    vlm_before_full_html: Optional[str] = None,
) -> str:
    trace_block = vlm_playwright_trace_block(vlm_trace_excerpt)
    vlm_ctx = vlm_run_step_context or ""
    prior_st = prior_steps_text or ""
    prior_js = prior_js_prefix_block(prior_js_prefix or "")
    gsum = global_trace_summary_block(global_trace_summary)
    vlog = vlm_run_log_block(vlm_run_log)
    dom_focus = vlm_focused_dom_before_block(vlm_focused_dom_before)
    dom_full = vlm_before_full_html_block(vlm_before_full_html)
    return f"""JSON only. step_uid={step_uid!r}
NL step: {nl!r}
Start URL for the scenario: {base_url!r}
Viewport: {viewport_w}x{viewport_h} (coordinates in VLM blocks, if any, use this same viewport).
Images: first is screen BEFORE the action, second is AFTER (reference from successful VLM run).
{dom_focus}{dom_full}{vlm_ctx}{prior_st}{prior_js}{gsum}{vlog}{trace_block}Generate js_fragment: Playwright JS statements (await ...) implementing this step.
Follow locator strategy in the system message (CSS and xpath= only; no getByRole/getByTestId/getByText/…); no Page Object classes.
If this step is typing/filling and the NL contains {{something}}, use the JavaScript identifier `something` in .fill() / .type() (e.g. .fill(login)), not the string '{{something}}'.
Remember: .locator('x') is CSS unless the string starts with xpath= — never put XPath axes inside quotes without that prefix.
Keep js_fragment compact: no long repeated identical .locator chains; omit "notes" or keep it under 200 characters so JSON always fits.
Your whole reply must be only the JSON object — parsers will not salvage markdown or truncated strings."""


def draft_user_message_expected_result(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    vlm_trace_excerpt: Optional[str] = None,
    vlm_run_step_context: Optional[str] = None,
    prior_steps_text: Optional[str] = None,
    prior_js_prefix: Optional[str] = None,
    global_trace_summary: Optional[str] = None,
    vlm_run_log: Optional[str] = None,
    vlm_focused_dom_before: Optional[str] = None,
    vlm_before_full_html: Optional[str] = None,
) -> str:
    """Draft user message for expected_result: assertions only."""
    trace_block = vlm_playwright_trace_block(vlm_trace_excerpt)
    vlm_ctx = vlm_run_step_context or ""
    prior_st = prior_steps_text or ""
    prior_js = prior_js_prefix_block(prior_js_prefix or "")
    gsum = global_trace_summary_block(global_trace_summary)
    vlog = vlm_run_log_block(vlm_run_log)
    dom_focus = vlm_focused_dom_before_block(vlm_focused_dom_before)
    dom_full = vlm_before_full_html_block(vlm_before_full_html)
    return f"""JSON only. step_uid={step_uid!r}
Expected result (natural language): {nl!r}
Start URL for the scenario: {base_url!r}
Viewport: {viewport_w}x{viewport_h} (coordinates in VLM blocks, if any, use this same viewport).
Images: first is screen BEFORE the step, second is AFTER (reference from successful VLM run).
{dom_focus}{dom_full}{vlm_ctx}{prior_st}{prior_js}{gsum}{vlog}{trace_block}Generate js_fragment: **only** Playwright **assertions** — `expect(...)` on locators from `page.locator` / `.locator` (CSS or xpath=). The harness provides `expect` in scope together with `page` and `request`. Do not call `page.goto`. Do not emit actions unless the NL absolutely requires a readiness wait expressed as assertions.
Follow locator strategy in the system message (CSS and xpath= only; no getByRole/getByTestId/getByText/…); no Page Object classes.
Use `expect.soft` when the NL lists several independent conditions. Add a short message string as the second argument to each `expect` where helpful.
**Do not** emit multiple lines that repeat the **same** full `page.locator(…).locator(…)` chain — use one `const` for the chain and several `expect.soft` on it, or one assertion per **distinct** locator target (see system prompt).
When the NL implies **no rows** or **removed entries**, assert on **item rows** or row counts — not on static column headers or labels that stay visible when the list is empty (see system prompt).
Keep js_fragment compact; omit "notes" or keep it under 200 characters so JSON always fits.
Your whole reply must be only the JSON object — parsers will not salvage markdown or truncated strings."""


def playwright_css_xpath_hint(playwright_error: str) -> str:
    """Extra user hint when MCP error is CSS parser choking on XPath-like text."""
    e = (playwright_error or "").lower()
    if "parsing css selector" not in e and "unexpected token" not in e:
        return ""
    if "following-sibling" not in e and "//" not in playwright_error:
        return ""
    return (
        "\nEngine hint from THIS error: a chained call used `.locator('following-sibling::...')` "
        "without the `xpath=` prefix, so Playwright treated it as CSS. "
        "Fix: use `.locator('xpath=./following-sibling::div')` (or one combined `page.locator('xpath=//...')`). "
        "Never chain bare `following-sibling::` inside quotes without `xpath=`.\n"
    )


def accessibility_snapshot_block(snap_raw: str) -> str:
    """Wrap trimmed a11y snapshot for the repair user message."""
    snap_raw = snap_raw.strip()
    max_c = MAX_A11Y_SNAPSHOT_CHARS
    if len(snap_raw) > max_c:
        snap_raw = snap_raw[:max_c] + "\n...snapshot truncated"
    return (
        "\nAccessibility snapshot — Playwright MCP `browser_snapshot` (captured when validation failed; "
        "use together with the page HTML snapshot above when present; may omit decorative nodes):\n"
        f"---\n{snap_raw}\n---\n"
    )


def page_html_block(html_raw: str) -> str:
    """Trimmed серийный HTML (page.content) на момент ошибки — для привязки локаторов к реальным узлам."""
    html_raw = html_raw.strip()
    max_c = MAX_PAGE_HTML_CHARS
    if len(html_raw) > max_c:
        html_raw = html_raw[:max_c] + "\n...html truncated"
    return (
        "\nPage HTML snapshot at validation failure (serialised document; secrets may appear — treat as confidential):\n"
        f"---\n{html_raw}\n---\n"
    )


def vlm_repair_grounding_block(
    *,
    viewport_w: int,
    viewport_h: int,
    vlm_coords: Optional[Any],
    trace_hint: Optional[str],
) -> str:
    """Координаты VLM и одна строка-подсказка из trace для repair."""
    parts: List[str] = []
    if vlm_coords is not None:
        parts.append(
            f"VLM viewport coordinates (successful run; same viewport {viewport_w}x{viewport_h}): {vlm_coords!r}"
        )
    th = (trace_hint or "").strip()
    if th:
        parts.append(f"Trace hint (selector/position from VLM trace excerpt): {th}")
    if not parts:
        return ""
    return "\nGrounding from successful VLM run (use with HTML/a11y to pick the same element):\n---\n" + "\n".join(parts) + "\n---\n"


REPAIR_HOW_TO_FIX = """How to fix (obey all — DOM-first, CSS/XPath only):
1) Open the **page HTML snapshot at validation failure** and the **MCP accessibility snapshot**. Find the concrete DOM node that matches the NL intent for this step.
2) Use VLM coordinates and/or the trace hint (selector/position) only to decide which node was targeted — same viewport as the test case; do not invent a different element.
3) Build a new locator with **only** `page.locator` / chained `.locator` using CSS or `xpath=` — **never** getByRole / getByTestId / getByText / getByLabel / etc.
4) If the log says "waiting for" / TimeoutError, the previous selector matched zero visible elements. Re-emitting the same chain as Reference is wrong; MCP will fail again.
5) You MUST change the locating strategy vs Reference: different anchor, parent section, `.filter({ visible: true })` / `.nth()`, or a single `page.locator('xpath=...')` from a stable root — not a one-token edit of the same pattern.
6) If Reference used `locator('text=...').locator('xpath=...')` and it timed out, do NOT reuse that pair; re-anchor from the page HTML / accessibility tree (wrapper, list, region, stable id, data-*).
7) If the error mentions CSS parsing and XPath-like fragments (e.g. "following-sibling::"), the engine was CSS — fix with `xpath=` prefix on that segment.
8) Anchor-first: split the runner "waiting for" chain into (anchor = first call) + (tail = rest). If the timeout waits on the anchor (first segment), fix the anchor first — changing only the tail while keeping the same broken anchor is invalid.
9) Stable data-* on the node or ancestor: use CSS attribute selectors only, e.g. `page.locator('[data-testid="..."]')`, `page.locator('[data-cy="section"]').locator('xpath=.//button[contains(., "Submit")]')` — priority: data-testid > data-test > data-cy > data-qa > data-id > id.
10) Full-chain rebuild: in a compound locator (anchor.inner.inner…), ANY segment can be the broken one. Rebuild the **entire** chain from the page HTML snapshot — do not keep a broken prefix. The new js_fragment must not reproduce any segment of the banned wait chains.
""" + STRICT_MODE_VIOLATION_PROTOCOL

REPAIR_ESC_PRIOR_MULTIPLE_FAILURES = (
    "\nSeveral different locators already failed. Stop inferring structure from label text + sibling axes; "
    "use the page HTML snapshot and MCP accessibility snapshot to anchor on the element that actually contains the target "
    "(stable id, data-testid, data-* on ancestor container, role/region), then read or interact from there.\n"
)

REPAIR_BAN_INTRO = (
    "\nHard ban — the new js_fragment must NOT contain the same resolution path the runner already waited on "
    "(changing only innerText/textContent/await layout is not enough):\n---\n"
)

REPAIR_BAN_OUTRO = (
    "---\nPick a different anchor: parent container, `[data-*]` / `[id]` on ancestor, "
    "or `page.locator('xpath=//…')` from root with a unique path seen in snapshot/images. "
    "No getBy* helpers. Rebuild the full chain from scratch — do not reuse the old prefix.\n"
)

REPAIR_PRIOR_CHAINS_HEADER = (
    "\nThis step already timed out or errored on ALL of the following runner wait chains — do not reproduce any:\n"
)

REPAIR_REFERENCE_HEADER = """Reference js_fragment that FAILED (do not copy; rewrite):
---
"""

REPAIR_REFERENCE_FOOTER = """---
Output one full replacement js_fragment as a valid JSON object only (same contract as system prompt). Omit "notes" or keep under 280 ASCII characters."""

# Повтор при невалидном JSON (нет эвристического восстановления — только новый ответ модели).
STRICT_JSON_RETRY_USER_MESSAGE = (
    "INVALID_JSON_PREVIOUS_REPLY. Output nothing but a single valid JSON object: "
    'start with { and end with }. Required key: "js_fragment" (string). Optional: "notes" (string). '
    "No markdown, no code fences, no text before or after. Escape newlines inside js_fragment as \\n."
)


def repair_anchor_policy_block(
    *,
    anchor_must_change: bool,
    anchor_first_hint: Optional[str],
) -> str:
    if not anchor_must_change and not (anchor_first_hint or "").strip():
        return ""
    parts: List[str] = []
    if (anchor_first_hint or "").strip():
        parts.append(
            f"Runner wait-chain anchor (first segment): {anchor_first_hint.strip()!r} — validate this locator against the page HTML snapshot and MCP accessibility snapshot before refining the tail."
        )
    if anchor_must_change:
        parts.append(
            "anchor_invalid=true: the same anchor already failed repeatedly — you MUST replace the anchor (first segment / root locator), not only tweak inner text=/locator/nth on a broken parent."
        )
    if not parts:
        return ""
    return "\nAnchor policy:\n" + "\n".join(parts) + "\n"


def strict_mode_hints_block(strict_mode_hints: Optional[str]) -> str:
    """Отдельный раздел user message для repair при strict mode violation (см. format_strict_mode_hints_from_playwright_error)."""
    h = (strict_mode_hints or "").strip()
    if not h:
        return ""
    return (
        "\nStrict mode violation hints extracted from the error (use these first):\n"
        f"---\n{h}\n---\n"
    )


def repair_user_message(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    repair_round: int,
    err_clip: str,
    css_xpath_hint: str,
    esc_prior: str,
    ban_block: str,
    snap: str,
    prev_clip: str,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    strict_mode_hints: Optional[str] = None,
) -> str:
    mcp_dom = ""
    if mcp_page_html and str(mcp_page_html).strip():
        mcp_dom = page_html_block(str(mcp_page_html))
    grounding = vlm_repair_grounding_block(
        viewport_w=viewport_w,
        viewport_h=viewport_h,
        vlm_coords=vlm_coords,
        trace_hint=trace_hint,
    )
    anchor_block = repair_anchor_policy_block(
        anchor_must_change=anchor_must_change,
        anchor_first_hint=anchor_first_hint,
    )
    sm_block = strict_mode_hints_block(strict_mode_hints)
    return f"""JSON only (repair). Whole reply = one valid JSON object; no markdown or extra text. step_uid={step_uid!r}
NL: {nl!r}
Follow the locator strategy in the system message (CSS/xpath= only; no getBy*; re-pick selectors — do not copy Reference); no Page Object classes.
If NL mentions fill/type with brace placeholders (e.g. {{{{login}}}}): use JS identifiers (e.g. .fill(login)), never literal strings '{{{{login}}}}' / '{{{{password}}}}'.
Multimodal images (same message, when provided): (1) screen before the scripted action (2) after (3) failure screenshot from Playwright `page.screenshot` at error time — align intent with the serialized page HTML at validation failure (if present) and the MCP accessibility snapshot below; use VLM coords/trace hint only as disambiguation.
URL: {base_url!r} Viewport: {viewport_w}x{viewport_h}
Repair attempt number: {repair_round} (the runner already rejected earlier versions — treat Reference below as a failed approach, not a template to reuse).
{mcp_dom}{snap}{grounding}
Playwright / MCP validation error (verbatim):
---
{err_clip}
---
{sm_block}
{REPAIR_HOW_TO_FIX}
{anchor_block}{css_xpath_hint}{esc_prior}
{ban_block}
{REPAIR_REFERENCE_HEADER}{prev_clip}
{REPAIR_REFERENCE_FOOTER}"""


def repair_user_message_expected_result(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    repair_round: int,
    err_clip: str,
    css_xpath_hint: str,
    esc_prior: str,
    ban_block: str,
    snap: str,
    prev_clip: str,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    strict_mode_hints: Optional[str] = None,
) -> str:
    """Repair user message for expected_result steps (assertions)."""
    mcp_dom = ""
    if mcp_page_html and str(mcp_page_html).strip():
        mcp_dom = page_html_block(str(mcp_page_html))
    grounding = vlm_repair_grounding_block(
        viewport_w=viewport_w,
        viewport_h=viewport_h,
        vlm_coords=vlm_coords,
        trace_hint=trace_hint,
    )
    anchor_block = repair_anchor_policy_block(
        anchor_must_change=anchor_must_change,
        anchor_first_hint=anchor_first_hint,
    )
    sm_block = strict_mode_hints_block(strict_mode_hints)
    return f"""JSON only (repair). Whole reply = one valid JSON object; no markdown or extra text. step_uid={step_uid!r}
Expected result NL: {nl!r}
Follow the locator strategy in the system message (CSS/xpath= only; no getBy*; re-pick selectors — do not copy Reference); output **assertions only** (`expect` + `page.locator`). The harness provides `expect` in scope. Do not call `page.goto`.
If NL mentions placeholders, respect identifiers from prior_js_prefix / accumulated scenario.
Multimodal images (when provided): (1) before (2) after (3) failure screenshot — align with page HTML at validation failure and MCP accessibility snapshot.
URL: {base_url!r} Viewport: {viewport_w}x{viewport_h}
Repair attempt number: {repair_round} (earlier js_fragment failed MCP validation — rewrite assertions/locators).
{mcp_dom}{snap}{grounding}
Playwright / MCP validation error (verbatim):
---
{err_clip}
---
{sm_block}
{REPAIR_ER_HOW_TO_FIX}
{anchor_block}{css_xpath_hint}{esc_prior}
{ban_block}
{REPAIR_REFERENCE_HEADER}{prev_clip}
{REPAIR_REFERENCE_FOOTER}"""


REPAIR_ER_SINGLE_HIDDEN_VISIBLE_HINT = """If the error shows **Expected: hidden** and **Received: visible** (or the reverse), the chain may already point at the intended node — the mismatch is often the **matcher** (`toBeHidden` vs `toBeVisible`) or the NL intent, not only rewriting `.locator(...)`. Prefer aligning the assertion with the error and the page HTML/a11y snapshot before inventing a new chain. **Exception:** if the resolved node is **structural chrome** (column header, static label, table caption) that remains visible when the list is empty, `not.toBeVisible` against that node is **unsatisfiable** — retarget to **data rows** / **line items** per the NL, or use a **count** of rows, not the chrome element."""

REPAIR_ER_SINGLE_REFERENCE_FOOTER = """---
Output one JSON object only. The string js_fragment must contain **exactly one** physical line: one complete `await expect(...).to...;` (or `await expect.soft(...).to...;`) statement. No other statements, no blank lines inside js_fragment. Omit "notes" or keep under 200 ASCII characters."""

REPAIR_ER_SINGLE_REST_FRAGMENT_HEADER = """Rest of this expected_result js_fragment (unchanged lines — do not duplicate or rewrite; only fix the single line above):
---
"""


def repair_user_message_expected_result_single_assertion(
    *,
    step_uid: str,
    nl: str,
    base_url: str,
    viewport_w: int,
    viewport_h: int,
    repair_round: int,
    err_clip: str,
    css_xpath_hint: str,
    esc_prior: str,
    ban_block: str,
    snap: str,
    failed_locator_inner: str,
    original_assertion_line: str,
    rest_of_fragment_excerpt: str,
    vlm_coords: Optional[Any] = None,
    trace_hint: Optional[str] = None,
    anchor_must_change: bool = False,
    anchor_first_hint: Optional[str] = None,
    mcp_page_html: Optional[str] = None,
    failed_locator_chain_text: Optional[str] = None,
    strict_mode_hints: Optional[str] = None,
) -> str:
    """Repair **one** assertion line in expected_result; остальной фрагмент передаётся только как контекст."""
    mcp_dom = ""
    if mcp_page_html and str(mcp_page_html).strip():
        mcp_dom = page_html_block(str(mcp_page_html))
    grounding = vlm_repair_grounding_block(
        viewport_w=viewport_w,
        viewport_h=viewport_h,
        vlm_coords=vlm_coords,
        trace_hint=trace_hint,
    )
    anchor_block = repair_anchor_policy_block(
        anchor_must_change=anchor_must_change,
        anchor_first_hint=anchor_first_hint,
    )
    rest_ex = (rest_of_fragment_excerpt or "").strip()
    if len(rest_ex) > 2400:
        rest_ex = rest_ex[:2400] + "\n...[truncated]"
    rest_block = ""
    if rest_ex:
        rest_block = f"\n{REPAIR_ER_SINGLE_REST_FRAGMENT_HEADER}{rest_ex}\n---\n"
    chain_block = ""
    if failed_locator_chain_text and str(failed_locator_chain_text).strip():
        chain_block = (
            f"\nFailed locator chain from Playwright **Locator:** line (verbatim — this is the full chain that failed):\n"
            f"---\n{str(failed_locator_chain_text).strip()}\n---\n"
        )
    hv_hint = ""
    el = (err_clip or "").lower()
    if "expected:" in el and "received:" in el and ("hidden" in el or "visible" in el):
        hv_hint = f"\n{REPAIR_ER_SINGLE_HIDDEN_VISIBLE_HINT}\n"

    sm_block = strict_mode_hints_block(strict_mode_hints)

    return f"""JSON only (targeted single-line repair). Whole reply = one valid JSON object; no markdown or extra text. step_uid={step_uid!r}
Expected result NL: {nl!r}
Follow the locator strategy in the system message (CSS/xpath= only; no getBy*). The harness provides `expect` in scope. Do not call `page.goto`.

**Scope (critical):** MCP failed on **one** assertion. Rewrite **only** the line below that corresponds to the failed chain. Do **not** change other lines of this step.
{chain_block}
Failed locator — first segment or short label (use with the chain above):
---
{failed_locator_inner}
---
{hv_hint}
Original assertion line to replace (one line; rebuild locator/assertion as needed):
---
{original_assertion_line}
---
{rest_block}
URL: {base_url!r} Viewport: {viewport_w}x{viewport_h}
Repair attempt number: {repair_round} (targeted line repair after MCP validation error).
{mcp_dom}{snap}{grounding}
Playwright / MCP validation error (verbatim):
---
{err_clip}
---
{sm_block}
{REPAIR_ER_HOW_TO_FIX}
{anchor_block}{css_xpath_hint}{esc_prior}
{ban_block}
{REPAIR_ER_SINGLE_REFERENCE_FOOTER}"""


def log_codegen_context_flags(
    *,
    phase: str,
    step_uid: str,
    has_vlm_trace: bool,
    has_vlm_action: bool,
    has_prior_steps: bool,
    has_prior_js: bool,
    has_global_trace: bool,
    has_vlm_log: bool,
    has_vlm_coords: bool = False,
    has_trace_hint: bool = False,
    has_vlm_dom_focus: bool = False,
    has_vlm_before_full: bool = False,
    has_mcp_page_html: bool = False,
) -> str:
    """Строка для лога: какие блоки контекста непустые."""
    parts = [
        f"phase={phase}",
        f"step_uid={step_uid}",
        f"trace_excerpt={'1' if has_vlm_trace else '0'}",
        f"vlm_action={'1' if has_vlm_action else '0'}",
        f"prior_steps={'1' if has_prior_steps else '0'}",
        f"prior_js={'1' if has_prior_js else '0'}",
        f"global_trace={'1' if has_global_trace else '0'}",
        f"vlm_log={'1' if has_vlm_log else '0'}",
        f"vlm_coords={'1' if has_vlm_coords else '0'}",
        f"trace_hint={'1' if has_trace_hint else '0'}",
        f"vlm_dom_focus={'1' if has_vlm_dom_focus else '0'}",
        f"mcp_page_html={'1' if has_mcp_page_html else '0'}",
    ]
    if phase == "draft":
        parts.append(f"vlm_before_full={'1' if has_vlm_before_full else '0'}")
    return "codegen context: " + " ".join(parts)
