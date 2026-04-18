import os


def load_and_split():
    path = os.path.join("data", "company.txt")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    size = 400      # 🔥 bigger chunk = better meaning
    overlap = 120   # 🔥 smoother context

    for i in range(0, len(text), size - overlap):
        chunk = text[i:i + size]

        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())

    return chunks