import logging
from langchain_core.messages import HumanMessage

from agent.graph import create_graph
from agent.nodes import setup_llm, setup_retriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_app = None

def _get_app():
    global _app
    if _app is None:
        logger.info("Initialisation du graphe multi-agents...")
        llm = setup_llm()
        retriever = setup_retriever()
        _app = create_graph(llm, retriever)
        logger.info("Graphe prêt.")
    return _app


async def get_response(prompt: str, thread_id: str = "session_1"):
    app = _get_app()
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {
        "messages": [HumanMessage(content=prompt)],
        "current_question": prompt,
        "iteration_count": 0,
    }

    final_answer = "Une erreur s'est produite."
    reflections = []

    try:
        output = await app.ainvoke(inputs, config=config)

        if output.get("traces"):
            reflections = list(output["traces"])

        if output.get("iteration_count"):
            reflections.append(f"🔁 Itérations validateur : {output['iteration_count']}")

        msgs = output.get("messages", [])
        if msgs:
            last = msgs[-1]
            final_answer = last.content if hasattr(last, "content") else str(last)

    except Exception as e:
        logger.exception("Erreur d'exécution du graphe")
        final_answer = f"Erreur : {e}"

    return final_answer, reflections


if __name__ == "__main__":
    import asyncio

    async def cli():
        print("Multi-agents prêt. 'exit' pour quitter.")
        while True:
            q = input("> ")
            if q.lower() in ("exit", "quit"):
                break
            ans, traces = await get_response(q, thread_id="cli")
            print("\n--- TRACES ---")
            for t in traces:
                print(f"  {t}")
            print("\n--- RÉPONSE ---")
            print(ans, "\n")

    asyncio.run(cli())