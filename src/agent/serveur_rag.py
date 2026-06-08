import sys
import os
import traceback
from pathlib import Path

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["PORT"] = "8000"

sys.stderr.write("⚙️ Démarrage du serveur MCP RAG...\n")
sys.stderr.flush()

try:
    from mcp.server.fastmcp import FastMCP
    from llama_index.core import StorageContext, load_index_from_storage, Settings
    from llama_index.embeddings.fastembed import FastEmbedEmbedding

    mcp = FastMCP("LoL_RAG_Server")

    project_root = Path(__file__).resolve().parents[2]
    persist_dir = str(project_root / "src" / "data" / "rag" / "vectors")
    
    sys.stderr.write(f"📂 Dossier vectoriel ciblé : {persist_dir}\n")
    sys.stderr.flush()

    Settings.embed_model = FastEmbedEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )

    if os.path.exists(persist_dir):
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
        retriever = index.as_retriever(similarity_top_k=7)
        sys.stderr.write("✅ Base de données chargée avec succès.\n")
        sys.stderr.flush()
    else:
        sys.stderr.write(f"❌ ERREUR FATALE : Base introuvable à {persist_dir}\n")
        sys.exit(1)

    @mcp.tool()
    def search_lol_knowledge(query: str) -> str:
        sys.stderr.write(f"🔍 Recherche en cours : {query}\n")
        sys.stderr.flush()
        docs = retriever.retrieve(query)
        if not docs:
            return "No information found."
        return "\n---\n".join([doc.text for doc in docs])

    if __name__ == "__main__":
        sys.stderr.write("🚀 Serveur MCP prêt sur port 8000...\n")
        sys.stderr.flush()
        mcp.run(transport='sse')

except Exception as e:
    sys.stderr.write(f"❌ ERREUR CRITIQUE: {str(e)}\n")
    sys.stderr.write(traceback.format_exc() + "\n")
    sys.exit(1)