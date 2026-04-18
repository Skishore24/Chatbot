import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import OLLAMA_URL, MODEL_NAME
from utils import get_history, update_user_info, get_user_info, detect_lead
from store import search

if not OLLAMA_URL:
    print("⚠️ WARNING: OLLAMA_URL is not set. AI features will fail.")
if not MODEL_NAME:
    print("⚠️ WARNING: MODEL_NAME is not set. AI features will fail.")


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
    elif len(r.split()) < 20 and any(w in r for w in ["hi", "hello", "hey", "help", "sure", "ok", "yes", "no", "name is"]):
        pass
    # If model went completely off-topic (and it's a long reply)
    elif "genkit" not in r and len(r.split()) > 10:
        return (
            "Genkit is a web and AI development company. "
            "Visit https://genkit.in or email genkit.tech@gmail.com."
        )

    # Append website hint if missing (only for genkit-related answers)
    if "genkit" in r and "genkit.in" not in r:
        reply = reply.rstrip(".") + ". Visit https://genkit.in for more details."

    return reply


# ─────────────────────────────────────────────────────────────────────────────
# Smart Fallback (when Ollama is down)
# ─────────────────────────────────────────────────────────────────────────────

def smart_fallback(query: str, context: str) -> str:
    """
    Simple keyword-based retrieval as a fallback if the AI service is offline.
    """
    q = query.lower()
    
    # 1. Check for specific keywords in the context
    if "price" in q or "cost" in q or "how much" in q:
        return "Genkit offers cost-effective solutions tailored to your budget. Please contact genkit.tech@gmail.com for a custom quote!"
        
    if "service" in q or "offer" in q or "do you do" in q:
        return "Genkit provides Web Development, AI Chatbots, Mobile Apps, UI/UX Design, E-commerce, Video Editing, and Graphic Design. Visit https://genkit.in for more."

    if "contact" in q or "email" in q or "phone" in q:
        return "You can reach Genkit at genkit.tech@gmail.com or visit our website at https://genkit.in."

    if "about" in q or "who is" in q or "what is genkit" in q:
        return "Genkit is a web and AI development company founded in 2024, focused on innovation and client-first solutions. Learn more at https://genkit.in."

    # 2. If no specific keyword, try to find a matching sentence in the context
    for line in context.split("\n"):
        if len(line.strip()) > 30 and any(word in line.lower() for word in q.split() if len(word) > 4):
            return line.strip() + " (Note: This is an automated fallback response as our AI service is currently busy)."

    return "Genkit is a digital solutions provider. For detailed inquiries while our AI is updating, please email genkit.tech@gmail.com."


# ─────────────────────────────────────────────────────────────────────────────
# Robust HTTP Session
# ─────────────────────────────────────────────────────────────────────────────

_session = requests.Session()
_retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
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

    # ── 5. Call Ollama (With Robust Retry) ───────────────────────────────────
    import time
    max_retries = 3
    response = None

    # Fix OLLAMA_URL if it's localhost (127.0.0.1 is more reliable on Windows)
    final_url = OLLAMA_URL
    if "localhost" in final_url:
        final_url = final_url.replace("localhost", "127.0.0.1")

    for attempt in range(max_retries):
        try:
            response = _session.post(
                final_url,
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.2, "num_predict": 200},
                },
                timeout=60, # Increased for first-load latency
            )

            if response.status_code == 200:
                break
                
            print(f"OLLAMA HTTP {response.status_code} (Attempt {attempt+1}): {response.text[:200]}")
            if attempt < max_retries - 1:
                time.sleep(1.5)

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt == max_retries - 1:
                # Last resort fallback if service is literally unreachable
                yield smart_fallback(query, context)
                return
            time.sleep(2)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"BRAIN ERROR: {e}")
                yield "⚠️ AI service encountered an error. Please try again."
                return
            time.sleep(1.5)

    if not response or response.status_code != 200:
        yield "Please contact Genkit — our AI is momentarily busy."
        return

    try:
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

    except Exception as e:
        print(f"BRAIN POST-PROCESS ERROR: {e}")
        yield "⚠️ Something went wrong. Please try again."