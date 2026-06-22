# League of Legends RAG Assistant

Romain Amigon AMIR14020300   &   Maxime Demarle DEMM29040100

Ce projet implémente un système RAG (Retrieval-Augmented Generation) agentique basé sur l'univers de League of Legends.

## 📋 Prérequis et Installation

Assurez-vous d'avoir Python 3.10 ou supérieur installé, idéalement dans un environnement virtuel (Conda ou venv).

1. Clonez ce dépôt et placez-vous à la racine du projet.
2. Installez l'ensemble des dépendances nécessaires via la commande suivante :

```bash
pip install mcp langchain-mcp-adapters langchain-groq langchain-ollama langgraph llama-index llama-index-embeddings-huggingface sentence-transformers streamlit python-dotenv

```

ou

```bash
pip install -r requirements.txt
```

## ⚙️ Configuration

Si vous souhaitez utiliser Groq, créez un fichier `.env` à la racine de votre projet pour configurer le modèle de langage (LLM) que l'agent utilisera. Sinon le projet utilise en natif Ollama

```env
USE_GROQ=true
GROQ_API_KEY=votre_cle_api_ici

```

*Note : Si vous souhaitez utiliser Llama 3 en local avec Ollama, passez `USE_GROQ` à `false` (assurez-vous que l'application Ollama tourne sur votre machine).*

---

## 🚀 Guide d'Utilisation

L'exécution du projet se fait en trois étapes consécutives, toutes exécutées **depuis la racine du projet**.

### 1. Préparation des données (Transform)

Si vous avez un script pour nettoyer ou préparer vos données brutes avant l'ingestion, exécutez-le en premier. *(Remplacez la commande ci-dessous par le nom exact de votre script de transformation si nécessaire)*.

```bash
python src/transform.py

```

*Assurez-vous que les textes nettoyés soient bien placés dans le dossier `src/data/rag/`.*

### 2. Ingestion des données (Création du RAG)

Ce script va lire vos documents, les découper, générer des métadonnées (fichiers JSON) via le LLM, et créer la base de données vectorielle.

```bash
python src/ingest.py

```

*Un dossier `src/data/rag/vectors/` sera automatiquement généré à l'issue de cette étape.*

### 3. Lancement de l'Application (Streamlit + Serveur MCP)

Lancer le serveur depuis src/agent avec

```bash
python serveur_rag.py
```

```bash
streamlit run src/interface.py

```

Une fenêtre s'ouvrira dans votre navigateur web. L'assistant IA se connectera silencieusement à la base vectorielle locale et sera prêt à répondre à vos questions sur League of Legends !

!!! Le premier prompt peut prendre beaucoup de temps car c'est le moment où tout est chargé (modele et graphe).

---

## 🏗️ Architecture Technique

* **Interface :** Streamlit
* **Orchestration Agentique :** LangGraph
* **Outils & Connexion :** Model Context Protocol (MCP) via `langchain-mcp-adapters`
* **Base Vectorielle :** LlamaIndex avec Embeddings locaux (`sentence-transformers`)
* **LLM :** Groq (Llama-3.1-8b) ou Ollama (Llama-3.1)
