# ask_user — Interactive Question Chips for Open WebUI

**Date:** 2026-07-15
**Status:** Approved

## Problem

We want models in the CUNY AI Lab Open WebUI sandbox to ask users questions with
prepackaged, clickable answer buttons, and to receive the user's selection back
reliably. An earlier draft rendered a custom HTML questionnaire card via the
`embeds` event and tried to inject selections into the chat input with
`postMessage` guesses and cross-origin DOM access. Verified against current
Open WebUI docs, none of those channels exist: the only documented
iframe-to-parent message is `iframe:height`, and HTML in response markdown is
sanitized, so in-message `<button>` elements are never clickable.

Open WebUI's native equivalent of the pattern every frontier platform uses
(structured options rendered by trusted client UI) is the follow-ups event:

```python
await __event_emitter__({
    "type": "chat:message:follow_ups",
    "data": {"follow_ups": ["Small", "Medium", "Large"]},
})
```

Chips render directly under the assistant message; clicking one sends that text
as the user's next message. Native-mode compatible; persists with the message.

## Decision

Chips-only, sequential. One Workspace tool, one method, no custom HTML, no
state. Multi-question flows happen conversationally: the model calls the tool
once per turn and waits for the user's reply before asking the next question.

## Design

### Component

A single Python file registered at **Workspace > Tools > + New Tool** in
Open WebUI. Standard `Tools` class with `Valves`.

### Interface

```python
async def ask_user(
    self,
    question: str,
    options: str,
    __event_emitter__=None,
) -> str
```

- `question`: the question text. The model states the question in its own
  response prose; the tool does not render it.
- `options`: 2–6 answer choices. Accepts a JSON array (`'["Yes","No"]'`) or a
  comma-separated string (`"Yes, No"`). Parsed defensively — models send both.
- Emits one `chat:message:follow_ups` event with the parsed options.
- Returns a confirmation string to the model, e.g.:

  > Presented options to the user as clickable buttons: Small | Medium |
  > Large. Their next message will be their selection. Ask your next question
  > only after they respond.

  The return value drives the sequential flow: it tells the model to stop and
  wait rather than continue asking.

### Option normalization

1. Try `json.loads`; if the result is a list, use it.
2. Otherwise split on commas.
3. Strip whitespace, drop empties, deduplicate preserving order.
4. Truncate each option to 80 characters (chips send their literal text).
5. Cap at `valves.max_options` (default 6), dropping extras.

### Error handling

- Fewer than 2 valid options after normalization: return an error string
  instructing the model to retry with at least two distinct choices. Never
  raise.
- `__event_emitter__` unavailable (non-chat contexts): return the options as a
  numbered text list so the interaction still works, and say so in the return
  value.

### Trigger surface

Two layers make the tool easy for models to reach for:

1. **Docstring** (becomes the function-calling spec): "Use whenever you ask
   the user a question that has a small set of natural answers —
   confirmations, preferences, multiple choice. Present choices as buttons
   instead of asking open-ended. Ask one question at a time."
2. **System-prompt snippet** shipped in a comment at the top of the file, for
   pasting into sandbox model configs: "When you need input from the user and
   the answer is one of a few options, call ask_user to render clickable
   answer buttons. Ask one question at a time and wait for the reply before
   asking the next."

### Valves

- `max_options: int = 6` — chips get cramped beyond six.

Nothing else. Native client rendering means no colors, sizing, or submit
behavior to configure.

## Out of scope

- Multi-select (chips are single-click single-send by platform design).
- Custom-styled cards, progress bars, confetti (no supported answer channel).
- Required/optional question metadata, question IDs, batch questionnaires.

## Testing

Manual, in the sandbox:

1. Single question renders chips; clicking sends the choice as user message.
2. Sequential flow: model asks Q2 only after Q1's reply.
3. Malformed `options` (empty, one option, non-JSON garbage) returns guidance
   instead of crashing.
4. System-prompt snippet reliably triggers tool calls on an option-shaped
   question.
