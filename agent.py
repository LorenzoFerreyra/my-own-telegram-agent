from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from models import AgentState
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from tools import add_expense, add_income
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)


tools = [add_expense, add_income]
llm_with_tools = llm.bind_tools(tools)

def call_model(state: AgentState):
    """Node that calls the OpenAI model with the conversation history"""
    
    messages = list(state["messages"])
    if len(messages) == 1:
        system_msg = SystemMessage(content="""You are a Spanish helpful personal finance assistant. 
        You help users track their expenses and income by recording them in a Google Sheet.
        
        When users mention spending money, use the add_expense tool.
        When users mention receiving money, use the add_income tool.
        
        Be friendly and confirm what you've recorded. Ask for clarification if needed.""")
        messages = [system_msg] + messages
    
    
    response = llm_with_tools.invoke(messages)
    
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
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()
