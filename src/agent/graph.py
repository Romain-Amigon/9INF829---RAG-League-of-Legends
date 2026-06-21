import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import AgentState
from agent.nodes import Nodes

logger = logging.getLogger(__name__)


def route_after_planner(state):
    if state.get("next_step") == "end":
        return "end"
    return "gather"


def route_after_validator(state):
    if state["next_step"] == "retry":
        return "synthesis"
    return "end"


def create_graph(llm, retriever):
    workflow = StateGraph(AgentState)
    nodes = Nodes(llm=llm, retriever=retriever)

    workflow.add_node("planner", nodes.planner)
    workflow.add_node("gather", nodes.gather_context)
    workflow.add_node("synthesis", nodes.synthesis)
    workflow.add_node("validator", nodes.validator)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "gather": "gather",
            "end": END,
        },
    )

    workflow.add_edge("gather", "synthesis")
    workflow.add_edge("synthesis", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "synthesis": "synthesis",
            "end": END,
        },
    )

    memory = MemorySaver()
    logger.info("Graphe non-exclusif (planner → gather → synthèse → validateur) créé avec checkpointer")
    return workflow.compile(checkpointer=memory)