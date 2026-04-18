import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import OLLAMA_URL, MODEL_NAME
from utils import get_history, update_user_info, get_user_info, detect_lead
from store import search


# ─────────────────────────────────────────────────────────────────────────────
# Text Utilities
# ─────────────────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    return " ".join(str(text).split()) if text else ""


def is_valid_query(query: str) -> bool:
    q = query.lower().strip()
    blocked = [
        "elon musk", "celebrity gossip", "weather forecast",
        "cricket score", "football score", "stock price",
        "movie review", "song lyrics",
    ]
    return not any(b in q for b in blocked)


# ─────────────────────────────────────────────────────────────────────────────
# Anti-Hallucination Filter
# ─────────────────────────────────────────────────────────────────────────────

def enforce_genkit_only(reply: str, name: str = "") -> str:
    r = reply.lower()

    # Block fake phone numbers or external company domains
    hallucination_signals = [
        "tel:", "phone:", "+1 ", "+44 ", "+91 ",
        "contact@", "info@", ".org", ".net",
        "barcelona", "spain ", " usa ",
    ]
    if any(sig in r for sig in hallucination_signals):
        return (
            "You can contact Genkit at genkit.tech@gmail.com "
            "or visit https://genkit.in."
        )

    # Allow conversational replies or if it addresses the user by name
    if name and name.lower() in r:
        pass
    elif len(r.split()) < 15 and any(w in r for w in ["hi", "hello", "hey", "name is", "you are"]):
        pass
    # If model went completely off-topic
    elif "genkit" not in r:
        return (
            "Genkit is a web and AI development company. "
            "Visit https://genkit.in or email genkit.tech@gmail.com."
        )

    # Append website hint if missing (only for genkit-related answers)
    if "genkit" in r and "genkit.in" not in r:
        reply = reply.rstrip(".") + ". Visit https://genkit.in for more details."

    return reply


# ─────────────────────────────────────────────────────────────────────────────
# Robust HTTP Session
# ─────────────────────────────────────────────────────────────────────────────

_session = requests.Session()
_retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
_session.mount("http://", HTTPAdapter(max_retries=_retries))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ANSWER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_answer(query: str, session_id: str):
    """
    Generator that yields the AI reply.
    Memory → Filter → RAG → Prompt → Ollama → Post-process → Yield
    """

    # ── 1. Update session memory ─────────────────────────────────────────────
    update_user_info(session_id, query)
    user   = get_user_info(session_id)
    name   = user.get("name", "")
    email  = user.get("email", "")

    # ── 2. Block off-topic queries ───────────────────────────────────────────
    if not is_valid_query(query):
        greeting = f"Hi {name}! " if name else ""
        yield f"{greeting}I can only help with questions about Genkit. How can I assist you?"
        return

    # ── 2.5 Intercept simple identity/greeting questions ─────────────────────
    q_lower = query.lower().strip()
    if q_lower in ["what is my name", "what's my name", "what is my name?", "whats my name", "what my name", "who am i", "who am i?"]:
        if name:
            yield f"Your name is {name}."
        else:
            yield "I don't know your name yet. You can tell me, or fill out the quote form!"
        return
        
    if q_lower in ["hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon"]:
        greeting = f"Hi {name}! " if name else "Hi there! "
        yield f"{greeting}I'm the Genkit AI Assistant. How can I help you today?"
        return

    # ── 3. RAG: retrieve relevant context ────────────────────────────────────
    context = search(query)
    if not context or len(context.strip()) < 50:
        context = (
            "Genkit is a web and AI development company.\n"
            "Services: Website development, AI chatbot development, "
            "Mobile app development, UI/UX design, E-commerce solutions, "
            "Video editing, Graphic designing.\n"
            "Contact: genkit.tech@gmail.com\n"
            "Website: https://genkit.in"
        )
    else:
        context = context[:1200]

    # ── 4. Build personalised system prompt ──────────────────────────────────
    history = get_history(session_id)

    system_prompt = (
        "You are the Genkit AI Assistant. Be helpful and concise.\n"
        "RULES:\n"
        "- Answer questions about Genkit using the context.\n"
        "- Never mention other companies or fake phone numbers.\n"
        "- If answering about Genkit and the info isn't in context, say: 'Please contact genkit.tech@gmail.com'.\n"
    )

    if name:
        system_prompt += f"- The user's name is {name}. Address them by name occasionally.\n"
    if email:
        system_prompt += f"- The user's email is {email}.\n"

    system_prompt += f"\nContext:\n{context}"

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h["role"], "content": h["message"]})
    messages.append({"role": "user", "content": query})

    # ── 5. Call Ollama ───────────────────────────────────────────────────────
    try:
        response = _session.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 160},
            },
            timeout=60,
        )

        if response.status_code != 200:
            print(f"OLLAMA HTTP {response.status_code}: {response.text[:200]}")
            yield "Please contact Genkit — our AI is momentarily busy."
            return

        data  = response.json()
        reply = data.get("message", {}).get("content", "").strip()

        if not reply:
            yield "Please contact Genkit at genkit.tech@gmail.com."
            return

        # ── 6. Post-process ──────────────────────────────────────────────────
        reply = clean_text(reply)
        reply = enforce_genkit_only(reply, name=name)   # runs BEFORE any prefix

        # Lead capture prompt (only if not already addressed)
        if detect_lead(query) and "👉" not in reply:
            reply += "\n\n👉 Share your name & email to get a custom quote!"

        yield reply

    except requests.exceptions.ConnectionError:
        yield "⚠️ Cannot reach the AI service. Please ensure Ollama is running."
    except requests.exceptions.Timeout:
        yield "⚠️ AI is taking too long. Please try again in a moment."
    except Exception as e:
        print(f"BRAIN ERROR: {e}")
        yield "⚠️ Something went wrong. Please try again."