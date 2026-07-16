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

import json

from pydantic import BaseModel, Field


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
