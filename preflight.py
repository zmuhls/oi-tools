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
