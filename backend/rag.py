import requests
from config import OLLAMA_URL, MODEL_NAME
from memory import get_history, save_user_info, get_user_info
from vector_db import search
from lead import detect_lead


# ── Clean Output ─────────────────────────────
def clean(text):
    return " ".join(str(text).split()) if text else ""


# ── Smart Filter (improved) ──────────────────
def is_genkit_query(query):
    q = query.lower()

    blocked = [
        "elon musk", "celebrity", "weather", "news",
        "movie", "song", "cricket", "football",
        "politics", "science", "math"
    ]

    if any(b in q for b in blocked):
        return False

    return True


# ── Main Function ────────────────────────────
def stream_answer(query, session_id):

    # Memory
    save_user_info(session_id, query)
    user = get_user_info(session_id)
    name = user.get("name", "")

    # Filter
    if not is_genkit_query(query):
        yield "I can help only with Genkit services and company details."
        return

    # ── Vector Search ────────────────────────
    context = search(query)

    if not context or len(context.strip()) < 30:
        context = """
Genkit is a digital solutions company.

We provide:
- Website development
- AI chatbot development
- Mobile app development
- UI/UX design
- E-commerce solutions
- Video editing
- Graphic designing

Technologies:
HTML, CSS, JavaScript, Python, Node.js, MongoDB, MySQL

Contact: genkit.tech@gmail.com
"""

    # limit context (important)
    context = context[:300]

    # History
    history = get_history(session_id)

    # Personalization
    prefix = f"{name}, " if name else ""

    # ── Prompt ───────────────────────────────
    system_prompt = f"""
You are Genkit AI Assistant.

Rules:
- Answer ONLY using given context
- Talk only about Genkit
- Use simple and natural English
- Keep response short (2–3 lines)
- Do NOT say "based on context"
- Do NOT add outside knowledge
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

    # ── API Call ────────────────────────────
    try:
        res = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 100
                }
            },
            timeout=60
        )

        if res.status_code != 200:
            print("API ERROR:", res.text)
            yield "Please contact Genkit for details."
            return

        data = res.json()
        reply = data.get("message", {}).get("content", "")

        if not reply:
            reply = "Please contact Genkit."

        reply = clean(reply)

        # shorten
        sentences = reply.split(". ")
        reply = ". ".join(sentences[:2]).strip()

        if not reply.endswith("."):
            reply += "."

        # personalization
        if prefix:
            reply = prefix + reply

        # ❌ REMOVE THIS BAD LOGIC (IMPORTANT)
        # if "genkit" not in reply.lower():
        #     reply = "I can help only with Genkit related queries."

        # lead
        if detect_lead(query):
            reply += "\n\n👉 Share your name & email to get started."

        yield reply

    except requests.exceptions.Timeout:
        yield "⚠️ Server timeout. Try again."

    except requests.exceptions.ConnectionError:
        yield "⚠️ AI service not available."

    except Exception as e:
        print("ERR:", e)
        yield "⚠️ Server busy."
