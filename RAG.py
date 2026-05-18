from dotenv import load_dotenv
import json
import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# =========================
# CONFIG
# =========================
DATA_PATH = "../scrapper/transcriptions_league_of_legends.json"
INDEX_PATH = "faiss.index"
CHUNKS_PATH = "chunks.pkl"

CHUNK_SIZE = 500
OVERLAP = 80

# Embedding model (léger et efficace)
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# LLM (tu peux changer si besoin)
load_dotenv()

client = OpenAI()


# =========================
# CHUNKING
# =========================
def chunk_text(text, size=500, overlap=80):
    chunks = []
    start = 0

    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap

    return chunks


# =========================
# BUILD INDEX (si pas existant)
# =========================
def build_index():
    print("🔧 Construction de l'index FAISS...")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        docs = json.load(f)

    all_chunks = []
    metadata = []

    for doc in docs:
        text = doc.get("transcription", "")
        chunks = chunk_text(text, CHUNK_SIZE, OVERLAP)

        for c in chunks:
            all_chunks.append(c)
            metadata.append({
                "title": doc.get("titre", ""),
                "url": doc.get("url", ""),
                "video_id": doc.get("id", ""),
                "text": c
            })

    embeddings = embed_model.encode(all_chunks, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)

    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print("✅ Index créé")


# =========================
# LOAD INDEX
# =========================
def load_index():
    index = faiss.read_index(INDEX_PATH)

    with open(CHUNKS_PATH, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata


# =========================
# RETRIEVAL
# =========================
def retrieve(query, index, metadata, k=5):
    q_emb = embed_model.encode([query]).astype("float32")

    distances, indices = index.search(q_emb, k)

    return [metadata[i] for i in indices[0]]


# =========================
# PROMPT
# =========================
def build_prompt(query, docs):
    context = "\n\n".join([
        f"[{d['title']}] {d['text']}"
        for d in docs
    ])

    return f"""
Tu es un expert de League of Legends.

Tu utilises uniquement le contexte fourni (transcriptions de vidéos YouTube).

CONTEXTE:
{context}

QUESTION:
{query}

Réponds clairement, avec des conseils utiles pour un joueur.
"""


# =========================
# LLM
# =========================
def ask_llm(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu es un coach expert League of Legends."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# =========================
# MAIN
# =========================
if __name__ == "__main__":

    # 1. build index si besoin
    if not os.path.exists(INDEX_PATH):
        build_index()

    # 2. load
    index, metadata = load_index()

    print("\n🎮 RAG LoL prêt ! Pose ta question :\n")

    while True:
        query = input(">>> ")

        docs = retrieve(query, index, metadata)
        prompt = build_prompt(query, docs)

        answer = ask_llm(prompt)

        print("\n🤖 Réponse :\n")
        print(answer)
        print("\n" + "-"*50 + "\n")