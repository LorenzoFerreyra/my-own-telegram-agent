"""Tests for pure decision functions in agent.py.

We don't import agent.py at module-import time because that instantiates a
ChatOllama client. Instead we import lazily inside each test — good enough
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
