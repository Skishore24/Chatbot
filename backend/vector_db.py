import chromadb

# ✅ safest option for free hosting (NO disk usage)
client = chromadb.Client()

collection = client.get_or_create_collection(name="genkit")


def add_documents(docs):
    try:
        if collection.count() > 0:
            print("⚠️ Skipping insert (already exists)")
            return

        for i, doc in enumerate(docs):
            collection.add(
                documents=[doc],
                ids=[str(i)]
            )

        print("✅ Documents added to vector DB")

    except Exception as e:
        print("❌ VECTOR DB ERROR:", e)


def search(query):
    try:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

        docs = results.get("documents", [[]])[0]

        if not docs:
            return ""

        return "\n".join(docs)

    except Exception as e:
        print("❌ SEARCH ERROR:", e)
        return ""
