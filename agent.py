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
    """Node that calls the OpenAI model with the conversation history"""
    
    messages = list(state["messages"])
    if len(messages) == 1:
        system_msg = SystemMessage(content="""You are a Spanish helpful personal finance assistant. 
        You help users track their Argentinian pesos (ARS) expenses and income by recording them in a Google Sheet.
        
        When users mention spending money, use the add_expense tool.
        When users mention receiving money, use the add_income tool.
        
        Be friendly and confirm what you've recorded. Ask for clarification if needed.""")
        messages = [system_msg] + messages
    
    
    
    response = llm_with_tools.invoke(messages)
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
    """Check if the last tool was add_expense or add_income to trigger report"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        if tool_name in ["add_expense", "add_income"]:
            return "generate_report"
    return "agent"