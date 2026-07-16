# Preflight (ask_user Chips) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-file Open WebUI Workspace tool that asks the user one question at a time with clickable answer chips via the `chat:message:follow_ups` event.

**Architecture:** One Python file (`preflight.py`) containing a standard Open WebUI `Tools` class with one method, `ask_user`, plus a module-level pure helper `_normalize_options`. No custom HTML, no state — sequential multi-question flows happen conversationally, driven by the tool's return string telling the model to wait for the reply.

**Tech Stack:** Python 3.11+, pydantic v2 (`BaseModel`/`Field` for Valves — Open WebUI ships it), pytest with `asyncio.run` for tests (no pytest-asyncio dependency).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-15-preflight-chips-design.md` — the plan implements it exactly; anything the spec lists as out of scope stays out.
- The tool never raises to the caller: every failure path returns a guidance string.
- Options: parse JSON array first, else comma-split; strip, drop empties, dedupe preserving order, truncate each to 80 chars, cap at `valves.max_options` (default 6).
- Event emitted is exactly `{"type": "chat:message:follow_ups", "data": {"follow_ups": [...]}}`.
- Commits: lowercase, ≤100 chars, no co-author line (user's global git rules).
- `preflight.py` must remain a single self-contained file (it gets pasted into Workspace > Tools), importable locally for tests.

---

### Task 1: Option normalization helper

**Files:**
- Create: `preflight.py`
- Test: `tests/test_normalize_options.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `_normalize_options(options: str | list, max_options: int = 6) -> list[str]` — module-level function in `preflight.py`. Task 2's `ask_user` calls it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_normalize_options.py
from preflight import _normalize_options


def test_json_array_string():
    assert _normalize_options('["Yes", "No", "Maybe"]') == ["Yes", "No", "Maybe"]


def test_comma_separated_string():
    assert _normalize_options("Yes, No, Maybe") == ["Yes", "No", "Maybe"]


def test_already_a_list():
    assert _normalize_options(["Yes", "No"]) == ["Yes", "No"]


def test_strips_and_drops_empties():
    assert _normalize_options('["  Yes  ", "", "  ", "No"]') == ["Yes", "No"]


def test_dedupes_preserving_order():
    assert _normalize_options("B, A, B, C, A") == ["B", "A", "C"]


def test_truncates_long_options_to_80_chars():
    long = "x" * 100
    result = _normalize_options([long, "short"])
    assert result[0] == "x" * 80
    assert result[1] == "short"


def test_caps_at_max_options():
    opts = [f"opt{i}" for i in range(10)]
    assert _normalize_options(opts, max_options=6) == opts[:6]


def test_json_garbage_falls_back_to_comma_split():
    assert _normalize_options('{"not": "a list"') == ['{"not": "a list"']


def test_json_non_list_falls_back_to_comma_split():
    # valid JSON but not a list: treat the raw string as comma-separated
    assert _normalize_options('"just a string"') == ['"just a string"']


def test_non_string_list_items_coerced():
    assert _normalize_options([1, 2, None, "three"]) == ["1", "2", "three"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zacharymuhlbauer/dev/tools && python3 -m pytest tests/test_normalize_options.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'preflight'`

- [ ] **Step 3: Write minimal implementation**

Create `preflight.py` (the class and metadata header come in Tasks 2–3; this task only needs the helper — put it after a minimal docstring header so the file is importable):

```python
"""
title: Preflight
description: Ask the user a question with prepackaged clickable answer buttons rendered as native follow-up chips
version: 0.1.0
license: MIT
"""

import json


def _normalize_options(options, max_options: int = 6) -> list:
    """Parse options into a clean list of chip labels.

    Accepts a JSON array string, a comma-separated string, or a list.
    Strips whitespace, drops empties/None, dedupes preserving order,
    truncates each option to 80 chars, caps at max_options.
    """
    if isinstance(options, str):
        parsed = None
        try:
            candidate = json.loads(options)
            if isinstance(candidate, list):
                parsed = candidate
        except (ValueError, TypeError):
            pass
        if parsed is None:
            parsed = options.split(",")
    elif isinstance(options, list):
        parsed = options
    else:
        parsed = [options]

    seen = set()
    result = []
    for item in parsed:
        if item is None:
            continue
        text = str(item).strip()[:80]
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= max_options:
            break
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/zacharymuhlbauer/dev/tools && python3 -m pytest tests/test_normalize_options.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add preflight.py tests/test_normalize_options.py
git commit -m "add option normalization helper for ask_user chips tool"
```

---

### Task 2: Tools class with ask_user method

**Files:**
- Modify: `preflight.py` (append below `_normalize_options`)
- Test: `tests/test_ask_user.py`

**Interfaces:**
- Consumes: `_normalize_options(options, max_options)` from Task 1.
- Produces: `Tools` class with `Valves(max_options: int = 6)` and `async def ask_user(self, question: str, options: str, __event_emitter__=None) -> str`. This is the complete public surface Open WebUI registers.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ask_user.py
import asyncio

from preflight import Tools


def make_recorder():
    events = []

    async def emitter(event):
        events.append(event)

    return events, emitter


def run(coro):
    return asyncio.run(coro)


def test_emits_follow_ups_event():
    tools = Tools()
    events, emitter = make_recorder()
    run(tools.ask_user("What size?", '["S", "M", "L"]', __event_emitter__=emitter))
    assert events == [
        {
            "type": "chat:message:follow_ups",
            "data": {"follow_ups": ["S", "M", "L"]},
        }
    ]


def test_return_string_lists_options_and_says_wait():
    tools = Tools()
    _, emitter = make_recorder()
    result = run(tools.ask_user("Size?", "S, M, L", __event_emitter__=emitter))
    assert "S | M | L" in result
    assert "clickable buttons" in result
    assert "next message will be their selection" in result
    assert "only after they respond" in result


def test_fewer_than_two_options_returns_guidance_and_emits_nothing():
    tools = Tools()
    events, emitter = make_recorder()
    result = run(tools.ask_user("Size?", '["OnlyOne"]', __event_emitter__=emitter))
    assert events == []
    assert "at least two" in result.lower()


def test_empty_options_returns_guidance():
    tools = Tools()
    events, emitter = make_recorder()
    result = run(tools.ask_user("Size?", "", __event_emitter__=emitter))
    assert events == []
    assert "at least two" in result.lower()


def test_no_emitter_falls_back_to_numbered_list():
    tools = Tools()
    result = run(tools.ask_user("Size?", "S, M, L"))
    assert "1. S" in result
    assert "2. M" in result
    assert "3. L" in result
    assert "could not be rendered" in result.lower()


def test_respects_max_options_valve():
    tools = Tools()
    tools.valves.max_options = 3
    events, emitter = make_recorder()
    run(tools.ask_user("Pick", "a, b, c, d, e", __event_emitter__=emitter))
    assert events[0]["data"]["follow_ups"] == ["a", "b", "c"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/zacharymuhlbauer/dev/tools && python3 -m pytest tests/test_ask_user.py -v`
Expected: FAIL with `ImportError: cannot import name 'Tools'`

- [ ] **Step 3: Write minimal implementation**

Append to `preflight.py` (and add `from pydantic import BaseModel, Field` to the imports at the top, next to `import json`):

```python
class Tools:
    """Ask the user questions with clickable answer chips."""

    class Valves(BaseModel):
        max_options: int = Field(
            default=6,
            description="Maximum number of answer chips to show (chips get cramped beyond 6).",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def ask_user(
        self,
        question: str,
        options: str,
        __event_emitter__=None,
    ) -> str:
        """
        Ask the user a question with prepackaged clickable answer buttons.

        Use whenever you ask the user a question that has a small set of
        natural answers — confirmations, preferences, multiple choice.
        Present choices as buttons instead of asking open-ended. Ask one
        question at a time: state the question in your response, call this
        tool with the answer choices, then stop and wait for the user's
        reply before asking anything else.

        :param question: The question you are asking the user. State it in
            your response text as well; this tool only renders the answers.
        :param options: 2-6 answer choices, as a JSON array
            (e.g. '["Yes","No","Maybe"]') or a comma-separated string
            (e.g. "Yes, No, Maybe").
        """
        opts = _normalize_options(options, self.valves.max_options)

        if len(opts) < 2:
            return (
                "Error: could not render answer buttons — provide at least "
                "two distinct answer choices as a JSON array or "
                "comma-separated string, then call ask_user again."
            )

        if __event_emitter__ is None:
            numbered = "\n".join(f"{i + 1}. {o}" for i, o in enumerate(opts))
            return (
                "Answer buttons could not be rendered in this context. "
                "Present these options to the user as a numbered list and "
                f"ask them to reply with their choice:\n{numbered}"
            )

        await __event_emitter__(
            {
                "type": "chat:message:follow_ups",
                "data": {"follow_ups": opts},
            }
        )

        return (
            "Presented options to the user as clickable buttons: "
            f"{' | '.join(opts)}. Their next message will be their "
            "selection. Ask your next question only after they respond."
        )
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `cd /Users/zacharymuhlbauer/dev/tools && python3 -m pytest tests/ -v`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add preflight.py tests/test_ask_user.py
git commit -m "add ask_user tool method emitting follow-up chips"
```

---

### Task 3: System-prompt snippet header and sandbox test checklist

**Files:**
- Modify: `preflight.py` (extend the module docstring)
- Create: `README.md`

**Interfaces:**
- Consumes: the complete `preflight.py` from Tasks 1–2.
- Produces: the final paste-ready file plus install/test instructions. Nothing downstream.

- [ ] **Step 1: Extend the module docstring with the system-prompt snippet**

Replace the module docstring at the top of `preflight.py` with:

```python
"""
title: Preflight
description: Ask the user a question with prepackaged clickable answer buttons rendered as native follow-up chips
version: 0.1.0
license: MIT

SYSTEM-PROMPT SNIPPET — paste into any model config (Workspace > Models >
System Prompt) that should use this tool:

    When you need input from the user and the answer is one of a few
    options, call the ask_user tool to render clickable answer buttons.
    State the question in your response, pass the answer choices to the
    tool, and ask one question at a time — wait for the user's reply
    before asking the next.

HOW IT WORKS: emits Open WebUI's native `chat:message:follow_ups` event.
The choices render as clickable chips under the assistant message;
clicking one sends that text as the user's next message. No custom HTML,
no injection — Native (Agentic) Mode compatible.
"""
```

- [ ] **Step 2: Run all tests to confirm nothing broke**

Run: `cd /Users/zacharymuhlbauer/dev/tools && python3 -m pytest tests/ -v`
Expected: 16 passed

- [ ] **Step 3: Write README with install and manual sandbox test checklist**

```markdown
# preflight

Open WebUI Workspace tool: ask the user one question at a time with
clickable answer chips, via the native `chat:message:follow_ups` event.
Design spec: `docs/superpowers/specs/2026-07-15-preflight-chips-design.md`.

## Install

1. Open WebUI: **Workspace > Tools > + New Tool**
2. Paste the full contents of `preflight.py`, save.
3. Enable the tool per-model (**Workspace > Models > edit > Tools**) or
   per-chat (the **+** icon next to the input box).
4. Paste the system-prompt snippet from the top of `preflight.py`
   into the model's system prompt.

## Manual sandbox test checklist

- [ ] Single question: ask the model something option-shaped ("should we
      meet Monday or Tuesday?"); chips render under the response; clicking
      one sends it as your message.
- [ ] Sequential flow: prompt "help me pick a pizza — ask me one question
      at a time"; the model asks question 2 only after your chip click.
- [ ] Malformed options: the tool returns guidance (never crashes) if the
      model passes one or zero options; the model recovers and retries.
- [ ] Trigger test: with the snippet installed, an option-shaped question
      triggers a tool call without the user mentioning the tool.

## Local tests

    python3 -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add preflight.py README.md
git commit -m "add system prompt snippet header and readme with sandbox test checklist"
```
