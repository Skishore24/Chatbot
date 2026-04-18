import os
import chromadb

# Absolute path so server works regardless of working directory
CHROMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

# --- Data Loading ---
def load_and_split():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "company.txt")
    
    if not os.path.exists(path):
        print(f"WARNING: Context file not found at {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    size = 500      # Optimized chunk size
    overlap = 100   # Smoother transitions

    for i in range(0, len(text), size - overlap):
        chunk = text[i:i + size]
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())

    return chunks

# --- Vector DB Management ---
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="genkit")

def add_documents(docs):
    try:
        # Proper way to clear collection in ChromaDB
        if collection.count() > 0:
            print("Refreshing Vector DB...")
            # We delete by IDs instead of where={}
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)

        if not docs:
            print("No documents to add.")
            return

        print(f"Adding {len(docs)} chunks to Vector DB...")
        collection.add(
            documents=docs,
            ids=[f"id_{i}" for i in range(len(docs))]
        )
    except Exception as e:
        print("STORE ERROR (Add):", e)

def search(query):
    try:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

        docs = results.get("documents", [[]])[0]
        if not docs:
            return ""

        # Remove duplicates and join
        unique_docs = list(dict.fromkeys(docs))
        return "\n".join(unique_docs).strip()

    except Exception as e:
        print("STORE ERROR (Search):", e)
        return ""
