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
