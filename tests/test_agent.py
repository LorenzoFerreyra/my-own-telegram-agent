"""Tests for pure decision functions in agent.py.

We don't import agent.py at module-import time because that instantiates a
ChatDeepSeek client. Instead we import lazily inside each test — good enough
for a local suite that just runs pytest.
"""

from types import SimpleNamespace


def _msg(tool_calls=None, content=""):
    """Cheap stand-in for a LangChain message."""
    return SimpleNamespace(tool_calls=tool_calls or [], content=content)


def test_should_continue_routes_to_tools_when_tool_calls_present():
    from agent import should_continue

    state = {"messages": [_msg(tool_calls=[{"name": "add_expense", "args": {}}])]}
    assert should_continue(state) == "tools"


def test_should_continue_ends_when_no_tool_calls():
    from agent import should_continue

    state = {"messages": [_msg(content="listo")]}
    assert should_continue(state) == "end"


def test_should_continue_ends_when_message_has_no_tool_calls_attribute():
    from agent import should_continue

    bare = object()  # no .tool_calls attribute at all
    assert should_continue({"messages": [bare]}) == "end"


def test_should_continue_looks_at_last_message_only():
    from agent import should_continue

    state = {
        "messages": [
            _msg(tool_calls=[{"name": "add_expense"}]),  # earlier tool call
            _msg(content="respondí sin tool call"),  # last message: no tool calls
        ]
    }
    assert should_continue(state) == "end"


# ── dedupe_tool_calls guardrail ─────────────────────────────────────

def test_dedupe_drops_identical_tool_calls():
    from agent import dedupe_tool_calls

    call = {"name": "add_expense", "args": {"amount": 5000, "description": "pizza"}}
    result = dedupe_tool_calls([call, dict(call), dict(call)])
    assert result == [call]


def test_dedupe_keeps_calls_with_different_args():
    from agent import dedupe_tool_calls

    a = {"name": "add_expense", "args": {"amount": 5000, "description": "pizza"}}
    b = {"name": "add_expense", "args": {"amount": 7000, "description": "taxi"}}
    assert dedupe_tool_calls([a, b]) == [a, b]


def test_dedupe_keeps_different_tools_with_same_args():
    from agent import dedupe_tool_calls

    a = {"name": "add_expense", "args": {"amount": 5000, "description": "pizza"}}
    b = {"name": "add_income", "args": {"amount": 5000, "description": "pizza"}}
    assert dedupe_tool_calls([a, b]) == [a, b]


def test_dedupe_ignores_args_key_order():
    from agent import dedupe_tool_calls

    a = {"name": "add_expense", "args": {"amount": 5000, "description": "pizza"}}
    b = {"name": "add_expense", "args": {"description": "pizza", "amount": 5000}}
    assert len(dedupe_tool_calls([a, b])) == 1
