"""Telegram agent module for personal finance assistance."""

import os
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from models import AgentState
from tools import add_expense, add_income, generate_monthly_report

load_dotenv()

llm = ChatOllama(
    model="qwen3:4b",
    temperature=0,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)


tools = [add_expense, add_income, generate_monthly_report]
llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    """Node that calls the Ollama model with the conversation history"""

    messages = list(state["messages"])
    if len(messages) == 1:
        system_msg = SystemMessage(content="""You are a personal finance assistant. Your ONLY job is to record transactions immediately.

        RULES - follow strictly:
        - When the user mentions spending money: call add_expense RIGHT AWAY. Do not ask for confirmation.
        - When the user mentions receiving money: call add_income RIGHT AWAY. Do not ask for confirmation.
        - NEVER ask the user to confirm the category or payment method. Decide yourself and record it.
        - NEVER say "¿quieres que registre...?" or "¿confirmas...?". Just do it.
        - If the category is ambiguous, pick the closest one and proceed.
        - After recording, reply with one short confirmation line in Spanish. Nothing more.
        - All amounts are in Argentinian pesos (ARS).
        Also, when successful, return the monthly report using the generate_monthly_report tool.""")
        
        messages = [system_msg] + messages

    print(f"[Ollama] Sending {len(messages)} message(s) to qwen3:4b...")
    response = llm_with_tools.invoke(messages)
    print(f"[Ollama] Response received. Tool calls: {[tc['name'] for tc in response.tool_calls] if response.tool_calls else 'none'}")

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
    workflow.add_node("generate_report", generate_report)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    workflow.add_conditional_edges(
        "tools",
        should_generate_report,
        {
            "generate_report": "generate_report",
            "agent": "agent"
        }
    )
    
    workflow.add_edge("generate_report", "agent")
    
    return workflow.compile()


def generate_report(state: AgentState):
    """Node to automatically generate the monthly report after add_expense or add_income"""
    report = generate_monthly_report.invoke({})
    return {"messages": [report]}


def should_generate_report(state: AgentState):
    """Check if the last tool was add_expense or add_income to trigger report.
    After ToolNode runs, messages[-1] is the ToolMessage (result),
    and messages[-2] is the AIMessage that requested the tool call.
    """
    messages = state["messages"]
    if len(messages) < 2:
        return "agent"
    ai_message = messages[-2]
    if hasattr(ai_message, "tool_calls") and ai_message.tool_calls:
        tool_name = ai_message.tool_calls[0]["name"]
        tool_result = messages[-1].content if hasattr(messages[-1], "content") else ""
        print(f"[Tool] {tool_name} result: {tool_result}")
        if tool_name in ["add_expense", "add_income"]:
            return "generate_report"
    return "agent"