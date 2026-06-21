import os
import json
import re
import logging
import subprocess
import httpx
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_tavily import TavilySearch

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


def setup_llm():
    use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
    if use_groq:
        logger.info("LLM via Groq (Cloud)")
        return ChatGroq(model="llama-3.1-8b-instant", temperature=0.0)
    logger.info("LLM via Ollama (Local)")
    return ChatOllama(model="llama3.1", temperature=0.0)


def setup_retriever(persist_dir=None):
    if persist_dir is None:
        persist_dir = str(project_root / "src" / "data" / "rag" / "vectors")
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    return index.as_retriever(similarity_top_k=7)


def build_history(state, max_turns=4):
    msgs = state.get("messages", [])
    if not msgs:
        return ""
    recent = msgs[-(max_turns * 2):]
    lines = []
    for m in recent:
        content = m.content if hasattr(m, "content") else str(m)
        role = getattr(m, "type", "")
        speaker = "User" if role == "human" else "Assistant"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


# --- FONCTION AJOUTÉE : Nettoyage du JSON ---
def _parse_target(raw):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    champion = ""
    position = ""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            champion = (data.get("champion") or "").strip()
            position = (data.get("position") or "").strip().lower()
        except Exception:
            pass
    if position not in ("top", "jungle", "mid", "adc", "support"):
        position = ""
    return champion.upper(), position


def _parse_plan(raw):
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    plan = {
        "irrelevant": False,
        "rag_persona": "MATCHUP",
        "use_opgg": False,
        "opgg_intent": "analysis",
        "use_web": False,
    }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            plan["irrelevant"] = bool(data.get("irrelevant", False))
            if "MACRO" in str(data.get("rag_persona", "")).upper():
                plan["rag_persona"] = "MACRO"
            plan["use_opgg"] = bool(data.get("use_opgg", False))
            intent = str(data.get("opgg_intent", "")).lower()
            if intent in ("analysis", "matchup", "tier", "synergy"):
                plan["opgg_intent"] = intent
            plan["use_web"] = bool(data.get("use_web", False))
        except Exception:
            pass
    return plan


OPGG_INTENT_TOOLS = {
    "analysis": "lol_get_champion_analysis",
    "matchup": "lol_get_lane_matchup_guide",
    "tier": "lol_list_lane_meta_champions",
    "synergy": "lol_get_champion_synergies",
}

OPGG_NO_CHAMPION_TOOLS = {"lol_list_lane_meta_champions"}


def _build_opgg_args(tool_name, champion, position):
    if tool_name == "lol_get_champion_analysis":
        return {
            "game_mode": "ranked",
            "champion": champion,
            "position": position or "top",
            "desired_output_fields": [
                "data.summary.average_stats.{win_rate,pick_rate,ban_rate,tier}",
                "data.core_items.{ids_names[],win}",
                "data.weak_counters[].{champion_name,win_rate}",
            ],
        }
    if tool_name == "lol_list_lane_meta_champions":
        return {"game_mode": "ranked", "position": position or "top"}
    return {"game_mode": "ranked", "champion": champion, "position": position or "top"}


MATCHUP_BRIEF = (
    "Your focus is the laning phase: matchups, trading patterns, "
    "micro-mechanics, and how to play a specific lane."
)
MACRO_BRIEF = (
    "Your focus is macro strategy: wave management, objectives "
    "(dragon, Baron Nashor), rotations, vision, and team play."
)


class Nodes:
    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever
        self.tavily_tool = TavilySearch(max_results=3)

    async def _rewrite_query(self, question, history):
        if not history:
            return question
        rewrite_prompt = f"""Given the conversation history and the current question, rewrite the current question as a standalone question that includes any subject referenced by pronouns like "him", "it", "that".
Return ONLY the rewritten question, nothing else.

History:
{history}

Current question: {question}"""
        rewritten = await self.llm.ainvoke(rewrite_prompt)
        return rewritten.content.strip()

    # --- MÉTHODE AJOUTÉE : Extraction avec le LLM ---
    async def _extract_opgg_target(self, question):
        extract_prompt = f"""Extract the League of Legends champion and lane from this question.
        Return ONLY a valid JSON object with keys "champion" and "position".
        - "champion": champion name strictly in UPPER_SNAKE_CASE (e.g., DR_MUNDO). Remove apostrophes (e.g., KHAZIX). Leave "" if no champion is named.
        - "position": one of top, jungle, mid, adc, support, or "" if not specified.

        Example 1: "What is Garen's winrate?" -> {{"champion": "GAREN", "position": ""}}
        Example 2: "best build for lee sin jungle" -> {{"champion": "LEE_SIN", "position": "jungle"}}

        Question: {question}"""
        resp = await self.llm.ainvoke(extract_prompt)
        return _parse_target(resp.content)

    def _run_opgg(self, tool_name, arguments):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(current_dir, "opgg_fetcher.py")
            process_result = subprocess.run(
                ["python", script_path, tool_name, json.dumps(arguments)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            api_data = process_result.stdout.strip()
            if not api_data or "Erreur" in api_data:
                return api_data or "Aucune donnée renvoyée.", f"OP.GG indisponible : {api_data}"
            return (
                f"Données OP.GG ({tool_name}) :\n{api_data}",
                f"OP.GG OK ({tool_name})",
            )
        except subprocess.TimeoutExpired:
            return "Délai d'attente dépassé pour OP.GG.", "Timeout"
        except Exception as e:
            return f"Erreur d'exécution du sous-processus : {e}", "Crash Subprocess"

    def _merge_contexts(self, source_contexts):
        labels = {
            "RAG": "[BASE LOCALE — RAG]",
            "OPGG": "[STATS LIVE — OP.GG]",
            "WEB": "[WEB — Tavily]",
        }
        blocks = []
        for key in ("RAG", "OPGG", "WEB"):
            if key in source_contexts:
                blocks.append(f"{labels[key]}\n{source_contexts[key]}")
        return "\n\n".join(blocks) if blocks else "Aucun contexte fourni."

    async def planner(self, state):
        question = state.get("current_question", "")
        if not question and state.get("messages"):
            last = state["messages"][-1]
            question = last.content if hasattr(last, "content") else str(last)

        history = build_history(state)
        search_query = await self._rewrite_query(question, history)

        prompt = f"""You are a routing supervisor for a League of Legends assistant.
The local knowledge base (RAG) is ALWAYS consulted. Your job is to decide the rest.

Return ONLY a JSON object with these keys:
- "irrelevant": true ONLY if the question has nothing to do with League of Legends, is just a greeting, or is completely unclear. Otherwise false.
- "rag_persona": "MATCHUP" (laning phase, trades, micro-mechanics, how to play a matchup) or "MACRO" (wave management, objectives, rotations, vision, team strategy).
- "use_opgg": true ONLY if the question needs live numbers such as current winrates, pick/ban rates, tier lists, optimal builds, or statistical counters.
- "opgg_intent": one of "analysis" (one champion's stats/build/counters), "matchup" (lane matchup guide), "tier" (best champions of a lane this patch), "synergy" (champions that pair well together). Only meaningful when use_opgg is true.
- "use_web": true ONLY if the question needs exact facts such as precise ability effects (Q/W/E/R), lore, patch notes, or esports results.

Use the conversation history to resolve references.

Conversation history:
{history}

Example: {{"irrelevant": false, "rag_persona": "MATCHUP", "use_opgg": true, "opgg_intent": "analysis", "use_web": false}}

Current question: {question}"""

        response = await self.llm.ainvoke(prompt)
        plan_data = _parse_plan(response.content)

        # --- NOUVELLE LOGIQUE POUR LES QUESTIONS HORS-SUJET ---
        if plan_data["irrelevant"]:
            msg = AIMessage(content="Désolé, je suis un assistant strictement spécialisé dans League of Legends 🎮. Je ne peux répondre qu'aux questions concernant le jeu ! Pourriez-vous reformuler votre question ?")
            trace = "Planner: question hors-sujet ou peu claire -> fin directe."
            return {
                "current_question": question,
                "messages": [msg],
                "traces": [trace],
                "next_step": "end",
            }

        persona = plan_data["rag_persona"]
        sources = [f"RAG_{persona}"]
        if plan_data["use_opgg"]:
            sources.append("OPGG")
        if plan_data["use_web"]:
            sources.append("WEB")

        plan = [f"RAG ({persona})"]
        if plan_data["use_opgg"]:
            plan.append(f"OP.GG live ({plan_data['opgg_intent']})")
        if plan_data["use_web"]:
            plan.append("Web/Tavily")
        plan += ["Synthèse", "Validation"]

        trace = f"Planner: persona={persona}, sources={sources}, opgg_intent={plan_data['opgg_intent']}"

        return {
            "current_question": question,
            "search_query": search_query,
            "rag_persona": persona,
            "opgg_intent": plan_data["opgg_intent"],
            "sources": sources,
            "plan": plan,
            "traces": [trace],
            "next_step": "gather",
        }

    async def gather_context(self, state):
        search_query = state.get("search_query") or state.get("current_question", "")
        sources = state.get("sources", [])

        source_contexts = {}
        traces = []

        docs = self.retriever.retrieve(search_query)
        source_contexts["RAG"] = "\n".join([doc.text for doc in docs])
        traces.append(f"Source RAG: {len(docs)} documents (requête: '{search_query}').")

        if "OPGG" in sources:
            intent = state.get("opgg_intent", "analysis")
            tool_name = OPGG_INTENT_TOOLS.get(intent, "lol_get_champion_analysis")
            champion, position = await self._extract_opgg_target(search_query)
            if tool_name not in OPGG_NO_CHAMPION_TOOLS and not champion:
                opgg_text, note = "Aucun champion identifié dans la question.", "Pas de champion ciblé"
            else:
                arguments = _build_opgg_args(tool_name, champion, position)
                opgg_text, note = self._run_opgg(tool_name, arguments)
            source_contexts["OPGG"] = opgg_text
            traces.append(f"Source OP.GG ({note}).")

        if "WEB" in sources:
            try:
                tavily_results = self.tavily_tool.invoke({"query": search_query})
                source_contexts["WEB"] = str(tavily_results)
                traces.append("Source Web: Tavily OK.")
            except Exception as e:
                logger.error(f"Erreur Tavily: {e}")
                source_contexts["WEB"] = "Web search failed."
                traces.append("Source Web: échec Tavily.")

        merged = self._merge_contexts(source_contexts)

        return {
            "source_contexts": source_contexts,
            "context": merged,
            "traces": traces,
            "next_step": "synthesis",
        }

    async def synthesis(self, state):
        question = state.get("current_question", "")
        history = build_history(state)
        context = state.get("context", "Aucun contexte fourni.")
        persona = state.get("rag_persona", "MATCHUP")
        persona_brief = MATCHUP_BRIEF if persona == "MATCHUP" else MACRO_BRIEF

        feedback = ""
        if state.get("errors"):
            feedback = f"\nYour previous answer was rejected. Fix this:\n{state['errors'][-1]}\n"

        prompt = f"""You are an expert League of Legends assistant.
        {persona_brief}

        The Context below is assembled from one or more labeled sources:
        - [BASE LOCALE — RAG]: curated knowledge base.
        - [STATS LIVE — OP.GG]: live statistics. Rates are decimals, so 0.51 means 51%.
        - [WEB — Tavily]: exact facts from web search.

        CRITICAL INSTRUCTION: Build your answer using ONLY the facts present in the Context.
        You may combine information across the labeled sources. If the exact answer is not present in any source, say so explicitly instead of inventing it.

        Conversation history:
        {history}

        Context:
        {context}

        Question: {question}
        {feedback}"""

        response = await self.llm.ainvoke(prompt)
        trace = f"Synthèse exécutée (persona={persona})."

        return {
            "draft_response": response.content,
            "traces": [trace],
            "next_step": "validator",
        }

    async def validator(self, state):
        question = state.get("current_question", "")
        draft = state.get("draft_response", "")
        context = state.get("context", "Aucun contexte fourni.")
        iterations = state.get("iteration_count", 0)

        if iterations >= 2:
            trace = "Validateur: limite d'itérations atteinte, réponse acceptée par défaut."
            return {
                "messages": [AIMessage(content=draft)],
                "traces": [trace],
                "next_step": "end",
            }

        prompt = f"""You are a strict Evaluator for a League of Legends assistant.
Your ONLY job is to check if the RESPONSE is faithful to the CONTEXT provided.
The CONTEXT may contain several labeled sources ([BASE LOCALE — RAG], [STATS LIVE — OP.GG], [WEB — Tavily]). A claim is valid if it is supported by ANY of these blocks.
In OP.GG data, rates are decimals (0.51 means 51%); converting a decimal to a percentage is NOT a hallucination.
CRITICAL: DO NOT use your internal knowledge. If the RESPONSE matches the CONTEXT, you must accept it, even if you personally think it is wrong.

QUESTION: {question}

CONTEXT USED BY THE EXPERT:
{context}

RESPONSE TO EVALUATE: {draft}

VERDICT (single line):
- Start with OK if the response answers the question using ONLY the context, or correctly explains the info is missing.
- Start with REJECT ONLY if the response contradicts the CONTEXT, or hallucinates outside information not found in any source.
After the verdict word, give a one-sentence reason referencing the context."""

        response = await self.llm.ainvoke(prompt)
        verdict = response.content.strip()

        if verdict.upper().startswith("REJECT"):
            trace = f"Validateur: REJET (iteration {iterations}). Raison: {verdict}"
            return {
                "errors": [verdict],
                "traces": [trace],
                "iteration_count": iterations + 1,
                "next_step": "retry",
            }

        trace = f"Validateur: réponse ACCEPTÉE. {verdict}"
        return {
            "messages": [AIMessage(content=draft)],
            "traces": [trace],
            "iteration_count": iterations + 1,
            "next_step": "end",
        }