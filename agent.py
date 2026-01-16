from langgraph.graph import StateGraph
from models import AgentState

def call_model(state: AgentState):

    pass

def build_graph():
    workflow = StateGraph(AgentState)
    
    return workflow.compile()