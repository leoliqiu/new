# Lightweight Playwright Screenshot Decision Engine

## Objective

Implement a lightweight screenshot decision system for Python + Playwright that automatically determines when a screenshot should be taken during web testing or exploration.

The goal is to capture only meaningful application states without adding heavy runtime overhead.

The system should:

1. Avoid screenshots after every action.
2. Avoid full DOM comparisons.
3. Avoid image-diff processing in the first version.
4. Inspect only after actions likely to cause meaningful state changes.
5. Use a lightweight semantic page-state scan.
6. Take screenshots only when important state changes are detected.
7. Always capture validation errors, application errors, and failures.
8. Avoid duplicate screenshots of previously seen states.

## Technology

Use:

- Python 3.11+
- Playwright for Python
- asyncio Playwright API preferred
- dataclasses
- hashlib
- pathlib
- json
- pytest compatible

Do not require external AI services, OCR, image comparison, or full DOM serialization.

## High-Level Flow

```text
Playwright Action
        |
        v
Should this action be inspected?
        |
   +----+----+
   |         |
  NO        YES
   |         |
Continue     v
        Capture lightweight BEFORE state
                 |
                 v
           Perform action
                 |
                 v
          Wait for stabilization
                 |
                 v
        Capture lightweight AFTER state
                 |
                 v
            Compare states
                 |
                 v
       Calculate screenshot score
                 |
          +------+------+
          |             |
      score >= 5      score < 5
          |             |
          v             v
     Screenshot       Continue
```

## Performance Principle

Do not inspect after every action. Inspect only after actions likely to change application state.

```python
CHECK_AFTER_ACTIONS = {
    "click",
    "select",
    "submit",
    "navigate",
}

SKIP_CHECK_AFTER_ACTIONS = {
    "fill",
    "type",
    "scroll",
    "hover",
    "focus",
}
```

Allow this behavior to be configurable.

## Project Structure

```text
screenshot_engine/
    __init__.py
    models.py
    state_collector.py
    comparator.py
    decision_engine.py
    screenshot_manager.py
    stabilizer.py
    config.py

tests/
    test_comparator.py
    test_decision_engine.py
    test_state_fingerprint.py

screenshots/
    metadata/
```

## Configuration

```python
from dataclasses import dataclass, field


@dataclass
class ScreenshotConfig:
    threshold: int = 5

    inspect_actions: set[str] = field(
        default_factory=lambda: {
            "click",
            "select",
            "submit",
            "navigate",
        }
    )

    capture_initial: bool = True
    capture_final: bool = True
    capture_navigation: bool = True
    capture_validation: bool = True
    capture_errors: bool = True

    stabilization_timeout_ms: int = 2000
    stabilization_interval_ms: int = 150

    ignore_selectors: list[str] = field(
        default_factory=lambda: [
            ".spinner",
            ".loading",
            "[role='progressbar']",
            ".tooltip",
        ]
    )
```

## Page State Model

Create a lightweight semantic state.

```python
from dataclasses import dataclass, field


@dataclass
class PageState:
    url: str = ""
    title: str = ""
    headings: list[str] = field(default_factory=list)
    visible_fields: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    workflow_status: str | None = None
    state_id: str = ""
```

Do not store complete HTML, every DOM attribute, every visible element, animation state, cursor position, or hidden elements.

## Lightweight State Collector

Implement:

```python
async def collect_page_state(page) -> PageState:
    ...
```

Prefer one `page.evaluate()` call to collect semantic information.

Collect:

- URL
- title
- visible headings
- visible input/select/textarea identities
- visible dialogs/modals
- visible validation or error messages
- optional workflow status

Example JavaScript collection logic:

```javascript
() => {
    const visible = (el) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        return style.display !== "none" &&
               style.visibility !== "hidden" &&
               rect.width > 0 &&
               rect.height > 0;
    };

    const textOf = (selector) =>
        [...document.querySelectorAll(selector)]
            .filter(visible)
            .map(el => (el.innerText || el.textContent || "").trim())
            .filter(Boolean);

    const fields = [...document.querySelectorAll("input, select, textarea")]
        .filter(visible)
        .map(el =>
            el.getAttribute("aria-label") ||
            el.getAttribute("name") ||
            el.getAttribute("placeholder") ||
            el.id ||
            el.tagName
        )
        .filter(Boolean);

    return {
        headings: textOf("h1, h2, h3, [role='heading']"),
        fields,
        dialogs: textOf("[role='dialog'], [aria-modal='true']"),
        errors: textOf("[role='alert'], .error, .validation-error, .field-error, .alert-danger")
    };
}
```

Keep collection inexpensive.

## Ignore Noisy UI

Do not allow transient UI to create screenshot decisions.

Ignore or normalize:

- loading spinners
- progress indicators
- tooltips
- hover states
- clocks
- timers
- timestamps where possible
- random generated IDs
- hidden elements
- animations

## Stable State Fingerprint

Create:

```python
def create_state_id(state: PageState) -> str:
    ...
```

Use only meaningful information:

```python
fingerprint = {
    "url": state.url,
    "headings": sorted(state.headings),
    "fields": sorted(state.visible_fields),
    "dialogs": sorted(state.dialogs),
    "errors": sorted(state.errors),
    "workflow_status": state.workflow_status,
}
```

Serialize deterministically and hash with SHA-256.

## State Comparison

```python
from dataclasses import dataclass, field


@dataclass
class StateChanges:
    url_changed: bool = False
    new_headings: list[str] = field(default_factory=list)
    new_fields: list[str] = field(default_factory=list)
    new_dialogs: list[str] = field(default_factory=list)
    new_errors: list[str] = field(default_factory=list)
    workflow_status_changed: bool = False
    new_state: bool = False
```

Implement:

```python
def compare_states(
    before: PageState,
    after: PageState,
    seen_states: set[str],
) -> StateChanges:
    ...
```

Compare only meaningful structural changes.

## Screenshot Scoring

Use a simple weighted system.

```python
DEFAULT_WEIGHTS = {
    "url_changed": 5,
    "new_dialog": 4,
    "validation_error": 5,
    "application_error": 10,
    "new_section": 3,
    "workflow_status_changed": 5,
    "new_state": 2,
}

SCREENSHOT_THRESHOLD = 5
```

## Screenshot Decision Model

```python
from dataclasses import dataclass, field


@dataclass
class ScreenshotDecision:
    should_capture: bool
    score: int
    category: str | None = None
    reasons: list[str] = field(default_factory=list)
```

## Screenshot Categories

```text
INITIAL
NAVIGATION
STATE_CHANGE
VALIDATION
ERROR
FINAL
```

## Decision Logic

Suggested rules:

- URL changed: +5, category `NAVIGATION`
- New dialog: +4
- New fields or section: +3
- Validation error: +5, category `VALIDATION`
- Application error: +10, always capture, category `ERROR`
- Workflow status changed: +5, category `STATE_CHANGE`
- New unseen state: +2

Capture when score is greater than or equal to the threshold, except forced error/failure conditions.

## Example Decisions

```text
fill First Name
-> inspection skipped
-> no screenshot
```

```text
select Risk Rating = High
-> 8 new fields
-> new section +3
-> new state +2
-> total = 5
-> screenshot STATE_CHANGE
```

```text
click Continue
-> validation message appears
-> +5
-> screenshot VALIDATION
```

```text
navigate to another page
-> URL changes
-> +5
-> screenshot NAVIGATION
```

## Action Model

```python
from dataclasses import dataclass


@dataclass
class BrowserAction:
    action_type: str
    target: str | None = None
    value: str | None = None
    locator: str | None = None
```

Supported action types:

```text
click
fill
type
select
check
uncheck
submit
navigate
scroll
hover
keyboard
custom
```

## Main Screenshot Engine

```python
class ScreenshotDecisionEngine:

    def __init__(self, config, output_dir="screenshots"):
        self.config = config
        self.output_dir = output_dir
        self.seen_states = set()
        self.sequence = 0
```

Expose:

```python
await engine.start(page)
await engine.execute(page, action, callback)
await engine.finish(page)
```

## Execute Wrapper

This is the most important component.

```python
async def execute(self, page, action: BrowserAction, callback):

    if action.action_type not in self.config.inspect_actions:
        await callback()
        return

    before = await collect_page_state(page)

    await callback()

    await wait_for_stable_page(page)

    after = await collect_page_state(page)

    changes = compare_states(
        before,
        after,
        self.seen_states,
    )

    decision = evaluate_screenshot(
        before,
        after,
        changes,
        threshold=self.config.threshold,
    )

    if decision.should_capture:
        await self.capture(
            page,
            after,
            decision,
            action,
        )

    self.seen_states.add(after.state_id)
```

## Stabilization

Do not use long fixed sleeps.

Implement:

```python
async def wait_for_stable_page(page):
    ...
```

Use:

1. `document.readyState`
2. known loader disappearance
3. lightweight semantic signature
4. wait about 150 ms
5. compare semantic signature again
6. return immediately once stable
7. use about 2 seconds as a maximum timeout, not a fixed delay

## Screenshot Manager

Use Playwright:

```python
await page.screenshot(
    path=str(path),
    full_page=True,
)
```

Filename examples:

```text
001_INITIAL_start.png
002_STATE_CHANGE_high_risk.png
003_VALIDATION_required_field.png
004_NAVIGATION_review_page.png
005_FINAL_complete.png
```

## Screenshot Metadata

Create one JSON metadata file per screenshot.

```json
{
  "sequence": 2,
  "category": "STATE_CHANGE",
  "score": 5,
  "reasons": [
    "8 new fields appeared",
    "new application state detected"
  ],
  "url": "https://example.com/risk",
  "state_id": "abc123",
  "action": {
    "action_type": "select",
    "target": "Risk Rating",
    "value": "High"
  },
  "screenshot": "002_STATE_CHANGE_high_risk.png"
}
```

Directory layout:

```text
screenshots/
    001_INITIAL_start.png
    002_STATE_CHANGE_high_risk.png
    metadata/
        001_INITIAL_start.json
        002_STATE_CHANGE_high_risk.json
```

## Initial Screenshot

At test or exploration start:

```python
await engine.start(page)
```

If enabled, capture one `INITIAL` screenshot and store its state ID.

## Final Screenshot

At completion:

```python
await engine.finish(page)
```

Capture `FINAL` only when the final state differs from the last captured state.

## Always Capture

Always capture for:

- application error
- uncaught page error
- unexpected browser dialog
- timeout
- failed assertion
- failed expected transition
- pytest failure

These bypass the normal score threshold.

## Pytest Failure Hook

Provide optional pytest integration:

```text
pytest failure
    -> engine.capture_error()
    -> screenshot + metadata
```

The screenshot engine must not hide or replace the original test failure.

## Logging

Example:

```text
[ScreenshotEngine]

Action:
select Risk Rating = High

Inspect:
YES

State:
A12D -> B78F

Changes:
+ 8 fields
+ heading: High Risk Information

Score:
new section +3
new state   +2

TOTAL:
5

Decision:
CAPTURE

Category:
STATE_CHANGE
```

For skipped actions:

```text
Action:
fill First Name

Inspect:
NO

Decision:
SKIP STATE CHECK
```

## Important Performance Requirements

The implementation must:

- avoid screenshots for every action
- avoid full DOM serialization
- avoid pixel comparison
- avoid OCR
- avoid repeated individual Playwright locator calls
- use one JavaScript evaluation where practical
- immediately skip low-risk actions
- use short stabilization checks
- stop waiting immediately once stable

## Do Not Implement in V1

Do not implement these unless specifically requested:

```text
visual screenshot comparison
OpenCV
OCR
AI screenshot classification
full DOM diff
state graph generation
workflow graph generation
coverage heatmaps
visual regression testing
ML-based importance scoring
```

Keep V1 lightweight.

## Acceptance Scenario

Given:

```text
Open Risk Assessment
Fill Name
Fill Description
Select Risk = High
New High Risk section appears
Check checkbox
Click Continue
Validation appears
Complete missing field
Click Continue
Navigate to Review page
Submit
Confirmation appears
```

Expected screenshot behavior:

```text
Open Risk Assessment
📸 INITIAL

Fill Name
NO screenshot

Fill Description
NO screenshot

Select Risk = High
📸 STATE_CHANGE

Check checkbox
NO screenshot

Click Continue
📸 VALIDATION

Complete missing field
NO screenshot

Click Continue
📸 NAVIGATION

Submit
📸 FINAL
```

## Expected Runtime Pattern

For about 100 browser actions, target roughly:

```text
40-60 actions skipped entirely
40-60 lightweight semantic comparisons
5-15 real screenshots
0 full DOM comparisons
0 image comparisons
```

Exact numbers depend on the application.

## Unit Tests

Create tests for:

- ordinary fill action: state inspection skipped, no screenshot
- URL change: score >= 5, `NAVIGATION`
- new conditional section: score >= 5, `STATE_CHANGE`
- validation: `VALIDATION`
- application error: `ERROR`, always capture
- duplicate state: normally no screenshot
- duplicate final state: no extra final screenshot

## Future Expansion

Design the classes so these can be added later without redesigning the engine:

```text
state graph
workflow discovery
test-case generation
qTest evidence mapping
Playwright trace correlation
visual comparison
coverage analysis
```

Do not implement them now.

## Final Design Principle

The screenshot engine should answer:

> Did this action create a meaningful application state that is useful as testing evidence?

It should not answer:

> Did anything on the screen change?

Optimize for meaningful evidence and low runtime overhead.
