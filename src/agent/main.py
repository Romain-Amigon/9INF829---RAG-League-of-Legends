import os
import asyncio
import logging
import traceback
from dotenv import load_dotenv
from pathlib import Path
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

global_memory = MemorySaver()

async def get_response(prompt: str, thread_id: str = "session_1"):
    use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
    
    if use_groq:
        logger.info("Initializing model via Groq (Cloud)")
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    else:
        logger.info("Initializing model via Ollama (Local)")
        llm = ChatOllama(model="llama3.1", temperature=0.0)

    url_serveur = "http://localhost:8000/sse"
    logger.info(f"Connexion au serveur MCP via {url_serveur}...")
    
    final_answer = None
    reflections = []
    
    try:
        async with sse_client(url_serveur, timeout=600.0) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                tools = await load_mcp_tools(session)
                
                system_prompt = """"You are a League of Legends expert assistant.
                Your primary source of truth is the provided search tool (RAG). Always look for information there first and prioritize its contents.
                If the tool returns relevant information, use it to build your answer.
                If the tool returns incomplete, noisy, or no information about the champion or strategy requested, you are allowed to use your own extensive internal knowledge about League of Legends to complement the answer, fill in the blanks, or provide a complete guide.
                When mixing sources, maintain factual accuracy regarding League of Legends mechanics (spells, items, match-ups).
                If the tool returns no information, state clearly: 'I don\'t have data on this request.'
                Do not guess or hallucinate facts."""

                agent_executor = create_react_agent(
                    llm, 
                    tools, 
                    checkpointer=global_memory, 
                    prompt=system_prompt
                )
                
                config = {"configurable": {"thread_id": thread_id}}
                inputs = {"messages": [("user", prompt)]}
                
                output = await agent_executor.ainvoke(inputs, config=config)
                
                if "messages" in output and len(output["messages"]) > 0:
                    for msg in output["messages"][1:-1]:
                        if msg.type == "ai" and msg.tool_calls:
                            reflections.append(f"🛠️ Appel de l'outil : {msg.tool_calls[0]['name']}")
                            reflections.append(f"📥 Paramètres : {msg.tool_calls[0]['args']}")
                        elif msg.type == "tool":
                            content_preview = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                            reflections.append(f"📄 Résultat RAG :\n{content_preview}")

                    final_answer = output["messages"][-1].content
                    
    except Exception as e:
        is_taskgroup = "TaskGroup" in str(type(e)) or "TaskGroup" in str(e)
        
        if is_taskgroup and final_answer is not None:
            pass
        else:
            logger.error(f"CRASH LLM:\n{traceback.format_exc()}")
            
            if hasattr(e, 'exceptions'):
                real_errors = "\n".join([str(sub_e) for sub_e in e.exceptions])
                final_answer = f"Erreur de modèle :\n{real_errors}"
            else:
                final_answer = f"Erreur LLM : {str(e)}"
                
    if final_answer is None:
        final_answer = "Une erreur critique s'est produite."

    return final_answer, reflections

if __name__ == "__main__":
    async def main():
        print("Posez une question (tapez 'exit' pour quitter) :")
        while True:
            question = input("> ")
            if question.lower() in ["exit", "quit"]:
                break
                
            reponse, traces = await get_response(question)
            for t in traces:
                print(t)
            print(f"\n🤖 {reponse}\n")
            
    asyncio.run(main())