import os
import sys
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from typing import Annotated, TypedDict, List, Union
import time

from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import logging

from llama_index.llms.ollama import Ollama
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

def add_reflections(left: list, right: list) -> list:
    if left is None:
        left = []
    if right is None:
        right = []
    return left + right

class AgentState(TypedDict):
    messages: Annotated[List[Union[dict, str]], add_messages]
    current_question: str
    iteration_count: int
    next_step: str
    reflections: Annotated[List[str], add_reflections]

class Nodes:
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

    def rag_generation(self, state: AgentState):
        time.sleep(0.1)
        
        history = state["messages"]
        question = state.get("current_question", "")
        if not question:
            question = history[-1].content if hasattr(history[-1], 'content') else str(history[-1])
            
        iterations = state.get("iteration_count", 0)

        if iterations >= 2:
            return {
                "messages": ["I could not generate a satisfactory answer after several attempts. Can you rephrase?"],
                "next_step": "end",
                "iteration_count": iterations + 1,
                "reflections": ["--- FORCED STOP ---\nIteration limit reached."]
            }

        docs = self.retriever.retrieve(question)
        context = "\n".join([doc.text for doc in docs])
        
        feedback = ""
        if len(history) > 1:
            last_msg_content = history[-1].content if hasattr(history[-1], 'content') else str(history[-1])
            if "🔄 REVISION REQUIRED:" in last_msg_content:
                feedback = f"\nWARNING: Your previous answer was rejected. Improve it based on this feedback:\n{last_msg_content}\n"

        conversation_history = ""
        for msg in history[:-1]:
            content = msg.content if hasattr(msg, 'content') else str(msg)
            if not content.startswith("🔄") and not content.startswith("\n════"):
                conversation_history += f"- {content}\n"

        prompt = f"""You are a League of Legends expert assistant.
        Answer the following question using ONLY the provided context and the conversation history.
        
        Conversation history:
        {conversation_history}
        
        Context:
        {context}
        
        Question: {question}
        {feedback}
        
        Answer clearly and concisely."""
        
        response = self.llm.complete(prompt)
        trace = [f"--- RAG PROMPT ---\n{prompt}", f"--- RAG RESPONSE ---\n{response.text}"]
        
        return {
            "messages": [response.text],
            "next_step": "debater",
            "iteration_count": iterations + 1,
            "reflections": trace
        }

    def critique_response(self, state: AgentState):
        history = state["messages"]
        initial_question = state.get("current_question", "")
        last_response = history[-1].content if hasattr(history[-1], 'content') else str(history[-1])
        
        prompt_critique = f"""You are a simple validation filter, NOT a fact-checker. 

Evaluate the RESPONSE based ONLY on these rules:
1. Assume all data in the RESPONSE is 100% correct (it comes from a private RAG database). If it mentions "Ambessa" or any other name, accept it as true. Do not fact-check.
2. Accept partial answers. If it gives a strategy without a champion, or a champion without a strategy, it is VALID.
3. Reject (❌) ONLY if the response completely ignores the topic.

QUESTION: {initial_question}
RESPONSE: {last_response}

VERDICT: You MUST output exactly ONE character first: ✅ if valid, or ❌ if rejected. You can add a 5-word maximum explanation after."""
        
        try:
            critique = self.llm.complete(prompt_critique)
            critique_text = critique.text.strip() if hasattr(critique, 'text') else str(critique).strip()
            
            if critique_text.startswith("✅"):
                return {
                    "messages": [f"\n═════════════════════════════\n✅ RESPONSE ACCEPTED\n═════════════════════════════\n{last_response}\n\n🗣️ Critique: {critique_text}"],
                    "next_step": "end"
                }
            else:
                return {
                    "messages": [f"🔄 REVISION REQUIRED:\n{critique_text}"],
                    "next_step": "retry"
                }
        except Exception as e:
            return {
                "messages": [f"❌ Critical error: {str(e)}"],
                "next_step": "end"
            }
def create_graph(llm, retriever):
    workflow = StateGraph(AgentState)
    nodes = Nodes(llm=llm, retriever=retriever)
    
    workflow.add_node("rag_generation", nodes.rag_generation)
    workflow.add_node("debater", nodes.critique_response)
    
    workflow.set_entry_point("rag_generation")
    
    workflow.add_conditional_edges(
        "rag_generation",
        lambda state: state["next_step"],
        {
            "debater": "debater",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "debater",
        lambda state: state["next_step"],
        {
            "end": END,
            "retry": "rag_generation"
        }
    )
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

def setup_llm():
    return Ollama(model="llama3", request_timeout=120.0, temperature=0.0)

def setup_retriever(data_dir="../../data/rag", persist_dir="../../data/rag/vectors"):
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device="cpu"
    )
    
    Settings.chunk_size = 512
    Settings.chunk_overlap = 50

    if not os.path.exists(persist_dir):
        documents = SimpleDirectoryReader(data_dir).load_data()
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=persist_dir)
    else:
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
        
    return index.as_retriever(similarity_top_k=7)

def run(app, prompt, thread_id="session_1"):
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "messages": [prompt],
        "current_question": prompt,
        "iteration_count": 0
    }   
    final_response = "An error occurred."
    final_reflections = []

    try:
        output = app.invoke(inputs, config=config)
        
        if "reflections" in output:
            final_reflections = output["reflections"]
        
        if "messages" in output and len(output["messages"]) > 0:
            last_msg = output["messages"][-1]
            if hasattr(last_msg, 'content'):
                final_response = str(last_msg.content).strip()
            else:
                final_response = str(last_msg).strip()
                
    except Exception as e:
        print(f"❌ Execution error: {e}")

    return final_response, final_reflections