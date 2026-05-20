from langgraph.graph import StateGraph, END
import logging
from src.agent.state import AgentState
from src.agent.nodes import Nodes

logger = logging.getLogger(__name__)

def create_graph(agent_instance, engines_dict, retriever=None):
    workflow = StateGraph(AgentState)
    
    nodes = Nodes(agent=agent_instance, engines=engines_dict, retriever=retriever)
    
    workflow.add_node("router", nodes.initial_router)
    workflow.add_node("textual_rag", nodes.rag_search)
    workflow.add_node("assistant", nodes.call_model)
    workflow.add_node("validator", nodes.check_pandas_syntax)
    workflow.add_node("executor", nodes.execute_tool)
    workflow.add_node("debater", nodes.critique_response)
    
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges(
        "router",
        lambda state: state["next_step"],
        {
            "rag_only": "textual_rag",
            "pandas_with_rag": "assistant"
        }
    )
    
    workflow.add_conditional_edges(
        "textual_rag",
        lambda state: state["next_step"],
        {
            "assistant": "assistant",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "assistant",
        lambda state: state["next_step"],
        {
            "execute": "validator",
            "generation": "textual_rag",
            "end": END
        }
    )    
    
    workflow.add_conditional_edges(
        "validator",
        lambda state: state["next_step"],
        {
            "execute": "executor",
            "retry": "assistant"
        }
    )
    
    workflow.add_conditional_edges(
        "executor",
        lambda state: state["next_step"],
        {
            "generation": "textual_rag",
            "retry": "assistant"
        }
    )
    
    logger.info("Graph successfully created (assistant -> validator -> executor -> augmented generation -> END)")
    return workflow.compile()