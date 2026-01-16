from pydantic import BaseModel
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class TelegramMessage(BaseModel):
    message: dict

class AgentState(TypedDict):
    """State that the agent maintains during conversation"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    chat_id: int

class FinanceEntry(BaseModel):
    """Represents a financial transaction"""
    type: str  # "expense" or "income"
    amount: float
    description: str
    category: str = "general"