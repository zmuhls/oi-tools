# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of Open WebUI Workspace tools (github.com/zmuhls/oi-tools). Each tool lives in its own subdirectory as a **single self-contained Python file** that gets pasted into Open WebUI at **Workspace > Tools > + New Tool** — so a tool file must never import from sibling files or the repo, only from stdlib and packages Open WebUI ships (e.g. pydantic v2).

Currently one tool: `preflight/` — asks the user a question with clickable answer chips.

Pushing requires the `zmuhls` GitHub account: `gh auth switch -u zmuhls`, push, then `gh auth switch -u milwrite` to restore the usual active account.

## Commands

Run a tool's tests from inside its directory (the tool module must be importable from cwd):

```bash
cd preflight && python3 -m pytest tests/ -v
python3 -m pytest tests/test_ask_user.py::test_emits_follow_ups_event -v   # single test
```

Tests avoid pytest-asyncio by wrapping async tool methods in `asyncio.run()`.

## Tool architecture and Open WebUI constraints

Every tool file follows Open WebUI's contract: a module docstring metadata header (`title:`, `description:`, `version:`), a `Tools` class with a nested `Valves(BaseModel)` config, and async methods whose **docstrings become the function-calling spec** — the docstring is the trigger surface that determines when models call the tool, so write it as instructions to the model. Tool methods return strings addressed to the model (e.g. telling it to wait for the user's reply); they never raise — every failure path returns a guidance string.

Hard-won platform facts (verified against Open WebUI docs; they invalidate obvious-seeming designs):

- HTML in response markdown is sanitized — in-message `<button>` elements are never clickable.
- The only documented iframe→parent channel for Rich UI `embeds` is `iframe:height`. An embedded card **cannot** send text to the chat; injection via postMessage guesses or parent-DOM access does not work.
- The supported way to render clickable options is the `chat:message:follow_ups` event: chips render under the assistant message and clicking one sends that text as the user's next message.
- Author for Native (Agentic) Mode: `status`, `notification`, `citation`, `follow_ups`, and `embeds` events work; `message`/`chat:message:delta` are Legacy-only — don't rely on them.

## Process artifacts

Each tool keeps its design spec and implementation plan under `<tool>/docs/superpowers/{specs,plans}/`, and its install steps plus a manual sandbox test checklist in `<tool>/README.md` (there is no automated integration test against a live Open WebUI instance — chip rendering and the click→message loop must be verified manually in the sandbox).
