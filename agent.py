"""Telegram agent module for personal finance assistance."""

import json
import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from models import AgentState
from tools import add_expense, add_income, generate_monthly_report

load_dotenv()

MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

llm = ChatDeepSeek(
    model=MODEL_NAME,
    temperature=0,
)


tools = [add_expense, add_income, generate_monthly_report]
llm_with_tools = llm.bind_tools(tools)


SYSTEM_PROMPT = SystemMessage(
    content="""You are a personal finance assistant. Your ONLY job is to record transactions immediately.

RULES - follow strictly:
- When the user mentions spending money: call add_expense RIGHT AWAY. Do not ask for confirmation.
- When the user mentions receiving money: call add_income RIGHT AWAY. Do not ask for confirmation.
- NEVER ask the user to confirm the category or payment method. Decide yourself and record it.
- NEVER say "quieres que registre...?" or "confirmas...?". Just do it.
- If the category is ambiguous, pick the closest one and proceed.
- Record each transaction ONLY ONCE: call add_expense or add_income at most one time per user message.
- If a tool result says the transaction was already recorded ("ya fue registrado"), do NOT call the tool again. Just tell the user it was already saved.
- After recording, reply with one short confirmation line in Spanish. Nothing more.
- All amounts are in Argentinian pesos (ARS).
- When the user asks for a report, balance, or summary: call generate_monthly_report RIGHT AWAY.
- Always respond in Spanish.

FORMATTING RULES:
- NEVER use emojis in your responses. No emoticons either.
- NEVER use Markdown formatting. No bold (**text**), no italic (*text*), no headers (#), no code blocks, no horizontal rules (---).
- Use plain text only. For lists, use simple dashes (-) without nesting.
- Keep responses clean and readable as plain text."""
)


def dedupe_tool_calls(tool_calls: list) -> list:
    """Drop repeated tool calls (same tool, same args) within a single model response,
    keeping only the first occurrence."""
    seen = set()
    unique = []
    for tc in tool_calls:
        key = (tc["name"], json.dumps(tc.get("args", {}), sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        unique.append(tc)
    return unique


def call_model(state: AgentState):
    """Node that calls the DeepSeek model with the conversation history"""

    messages = [SYSTEM_PROMPT] + list(state["messages"])

    print(f"[DeepSeek] Sending {len(messages)} message(s) to {MODEL_NAME}...")
    response = llm_with_tools.invoke(messages)
    print(
        f"[DeepSeek] Response received. Tool calls: {[tc['name'] for tc in response.tool_calls] if response.tool_calls else 'none'}"
    )

    if response.tool_calls:
        unique_calls = dedupe_tool_calls(response.tool_calls)
        if len(unique_calls) < len(response.tool_calls):
            print(
                f"[Guardrail] Dropped {len(response.tool_calls) - len(unique_calls)} duplicate tool call(s)"
            )
            response.tool_calls = unique_calls

    if hasattr(response, "content") and "</think>" in response.content:
        response.content = response.content.split("</think>")[-1].strip()

    return {"messages": [response]}


def should_continue(state: AgentState):
    """Decide if we should use tools or end"""
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def build_graph():
    """Build the LangGraph workflow"""
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
