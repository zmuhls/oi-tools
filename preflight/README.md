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
