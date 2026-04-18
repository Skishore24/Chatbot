import requests
from config import OLLAMA_URL, MODEL_NAME
from memory import get_history, save_user_info, get_user_info
from vector_db import search
from lead import detect_lead


def clean(text):
    return " ".join(str(text).split()) if text else ""


def is_genkit_query(query):
    q = query.lower().strip()

    if "genkit" in q:
        return True

    blocked = [
        "elon musk", "celebrity", "weather",
        "news", "movie", "song", "cricket",
        "football", "politics", "science", "math"
    ]

    if any(b in q for b in blocked):
        return False

    return True


def stream_answer(query, session_id):

    # ── Memory ─────────────────────────────
    save_user_info(session_id, query)
    user = get_user_info(session_id)
    name = user.get("name", "")

    # ── Filter ─────────────────────────────
    if not is_genkit_query(query):
        yield "I can help only with Genkit related queries."
        return

    # ── Vector Search ──────────────────────
    context = search(query)

    if not context:
        context = """
Genkit is a digital solutions company.

Services:
- Website development
- AI chatbot development
- Mobile app development
- UI/UX design
- E-commerce solutions

Contact: genkit.tech@gmail.com
"""

    # ── History ────────────────────────────
    history = get_history(session_id)

    # ── Personalization ────────────────────
    prefix = f"{name}, " if name else ""

    # ── Prompt ─────────────────────────────
    system_prompt = f"""
You are Genkit AI Assistant.

Rules:
- Answer ONLY using given context
- Talk only about Genkit
- Use simple and clear English
- Keep response short (2–3 lines)
- Sound natural like ChatGPT
- No headings or labels
- If not found → say "Please contact Genkit"

Context:
{context}
"""

    messages = [{"role": "system", "content": system_prompt}]

    for h in history:
        messages.append({
            "role": h["role"],
            "content": h["message"]
        })

    messages.append({"role": "user", "content": query})

    # ── API Call ───────────────────────────
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 120
                }
            },
            timeout=120
        )

        if res.status_code != 200:
            print("API ERROR:", res.text)
            yield "⚠️ AI server error."
            return

        data = res.json()
        reply = data.get("message", {}).get("content", "")

        if not reply:
            reply = "Please contact Genkit."

        reply = clean(reply)

        # 🔥 Smart shortening
        sentences = reply.split(". ")
        reply = ". ".join(sentences[:2]).strip()

        if not reply.endswith("."):
            reply += "."

        # 🔥 Personal touch
        if prefix:
            reply = prefix + reply

        # 🔥 Safety check
        if "genkit" not in reply.lower():
            reply = "I can help only with Genkit related queries."

        # 🔥 Lead detection
        if detect_lead(query):
            reply += "\n\n👉 Share your name & email to get started."

        yield reply

    except requests.exceptions.Timeout:
        yield "⚠️ Server timeout."

    except requests.exceptions.ConnectionError:
        yield "⚠️ AI server not running."

    except Exception as e:
        print("ERR:", e)
        yield "⚠️ Server busy."