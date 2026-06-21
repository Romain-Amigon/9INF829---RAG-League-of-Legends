from typing import Annotated, Sequence, TypedDict, List, Dict
import operator
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def add_list_items(left: list, right: list) -> list:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_question: str
    search_query: str
    plan: list[str]
    sources: List[str]
    source_contexts: Dict[str, str]
    context: str
    draft_response: str
    traces: Annotated[List[str], add_list_items]
    errors: Annotated[List[str], add_list_items]
    rag_persona: str
    opgg_intent: str
    next_step: str
    iteration_count: int