import chromadb

client = chromadb.PersistentClient(path="/tmp/chroma_db")
collection = client.get_or_create_collection(name="genkit")


def add_documents(docs):
    if collection.count() > 0:
        print("⚠️ Data already exists, skipping insert")
        return

    for i, doc in enumerate(docs):
        collection.add(
            documents=[doc],
            ids=[str(i)]
        )


# 🔥 IMPROVED SEARCH (SMART RAG)
def search(query):
    try:
        results = collection.query(
            query_texts=[query],
            n_results=5
        )

        docs = results.get("documents", [[]])[0]

        if not docs:
            return ""

        # ✅ Remove duplicates
        unique_docs = list(dict.fromkeys(docs))

        # ✅ Keep only best 3 chunks (reduce noise)
        top_docs = unique_docs[:3]

        # ✅ Clean + join properly
        context = "\n".join(top_docs)

        return context.strip()

    except Exception as e:
        print("VECTOR SEARCH ERROR:", e)
        return ""
