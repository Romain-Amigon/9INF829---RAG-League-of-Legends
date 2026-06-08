import os
import json
from tqdm import tqdm
from dotenv import load_dotenv
from llama_index.llms.ollama import Ollama
from llama_index.llms.groq import Groq
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.node_parser import SentenceSplitter

load_dotenv()

def main():
    data_dir = "src/data/rag"
    persist_dir = "src/data/rag/vectors"

    print("⚙️ Configuration du modèle d'Embedding...")
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        device="cpu"
    )

    # Initialisation du LLM pour générer le JSON
    use_groq = os.getenv("USE_GROQ", "false").lower() == "true"
    if use_groq:
        print("🚀 Utilisation de Groq pour la génération des métadonnées.")
        # On force le format JSON si l'API le supporte
        llm = Groq(model="llama-3.1-8b-instant", temperature=0.0)
    else:
        print("🐢 Utilisation de Ollama en local.")
        # Ollama possède un mode JSON natif très pratique
        llm = Ollama(model="llama3", request_timeout=180.0, temperature=0.0, json_mode=True)

    print(f"\n📂 Chargement des documents depuis '{data_dir}'...")
    documents = SimpleDirectoryReader(data_dir).load_data()
    
    # 1. Découpage manuel des documents
    splitter = SentenceSplitter(chunk_size=256, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(documents)
    
    print(f"📄 {len(nodes)} morceaux de texte (chunks) à analyser.")
    print("⏳ Génération des métadonnées (JSON) un par un pour éviter les crashs...")

    # 2. Boucle for classique avec barre de progression
    for node in tqdm(nodes, desc="Extraction Métadonnées"):
        text = node.get_content()
        
        # Le prompt strict demandant un JSON
        prompt = f"""Analyse ce texte issu de League of Legends et extrais les informations au format JSON.
        Texte : "{text}"
        
        Tu dois répondre UNIQUEMENT avec un objet JSON valide contenant exactement deux clés :
        - "champion": Le nom du champion principal mentionné (ou "Aucun" si aucun n'est mentionné).
        - "categorie": Choisis UNE SEULE catégorie parmi : [Build, Stratégie, Lore, Esport, Autre].
        """
        
        try:
            # Appel basique et bloquant (pas d'asynchrone)
            response = llm.complete(prompt)
            
            # Nettoyage de la réponse au cas où le LLM ajoute du texte autour du JSON
            raw_json = response.text.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json.replace("```json", "").replace("```", "").strip()
                
            # Conversion du texte en dictionnaire Python
            metadata = json.loads(raw_json)
            
            # Injection des métadonnées dans le nœud
            node.metadata["champion"] = metadata.get("champion", "Aucun")
            node.metadata["categorie"] = metadata.get("categorie", "Autre")
            
        except Exception as e:
            # Si le LLM rate son JSON sur un chunk, on ne fait pas crasher tout le programme !
            # On met des valeurs par défaut et on passe au suivant.
            node.metadata["champion"] = "Erreur"
            node.metadata["categorie"] = "Autre"

    print("\n💾 Création de l'index vectoriel et sauvegarde sur le disque...")
    index = VectorStoreIndex(nodes)
    index.storage_context.persist(persist_dir=persist_dir)
    
    print("✅ Ingestion terminée avec succès !")

if __name__ == "__main__":
    main()