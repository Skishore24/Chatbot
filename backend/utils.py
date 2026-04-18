import sqlite3
import os
from collections import OrderedDict

# ─────────────────────────────────────────────────────────────────────────────
# Lead Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_lead(text: str) -> bool:
    triggers = ["price", "cost", "project", "build", "hire", "quote", "services", "how much", "budget"]
    return any(t in text.lower() for t in triggers)


# ─────────────────────────────────────────────────────────────────────────────
# SQLite Database (Zero-Config)
# ─────────────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "genkit.db")

def get_db_connection():
    """Retrieve a connection to the local SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Ensure database and tables exist on startup."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_query   TEXT,
                bot_response TEXT,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       VARCHAR(255),
                email      VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ SQLite Database Initialized.")
    except Exception as e:
        print("❌ DB INIT ERROR:", e)


def save_chat_to_db(query: str, response: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chats (user_query, bot_response) VALUES (?, ?)",
            (query, response),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB ERROR (chat):", e)


def save_lead_to_db(name: str, email: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO leads (name, email) VALUES (?, ?)",
            (name, email),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("DB ERROR (lead):", e)


# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Session Store
# ─────────────────────────────────────────────────────────────────────────────

chat_history: OrderedDict = OrderedDict()
user_profiles: dict = {}
MAX_SESSIONS = 100
MAX_MESSAGES = 20   # store more for better memory


def add_message(session_id: str, role: str, message: str):
    if session_id not in chat_history:
        if len(chat_history) >= MAX_SESSIONS:
            chat_history.popitem(last=False)
        chat_history[session_id] = []

    chat_history[session_id].append({"role": role, "message": message})
    if len(chat_history[session_id]) > MAX_MESSAGES:
        chat_history[session_id] = chat_history[session_id][-MAX_MESSAGES:]


def get_history(session_id: str) -> list:
    """Return last 6 messages for richer conversational context."""
    return chat_history.get(session_id, [])[-6:]


def _ensure_profile(session_id: str):
    if session_id not in user_profiles:
        user_profiles[session_id] = {}


def save_user_from_lead(session_id: str, name: str, email: str):
    """Called when user submits the lead form — immediately stores name + email."""
    _ensure_profile(session_id)
    if name:
        user_profiles[session_id]["name"] = name.strip().title()
    if email:
        user_profiles[session_id]["email"] = email.strip().lower()


def update_user_info(session_id: str, message: str):
    """
    Detect user name and email from natural conversation.
    Patterns: 'my name is X', 'i am X', "i'm X", 'call me X'
    Also detects email addresses in the message.
    """
    _ensure_profile(session_id)
    msg_lower = message.lower().strip()

    # ── Name detection ────────────────────────────────────────────────────────
    name_patterns = [
        "my name is ",
        "i am ",
        "i'm ",
        "im ",
        "call me ",
        "this is ",
    ]
    for pattern in name_patterns:
        if pattern in msg_lower:
            try:
                after = msg_lower.split(pattern)[-1].strip()
                # Take first word only, capitalize
                name_candidate = after.split()[0].strip(".,!?")
                # Only store if it looks like a real name (alpha, 2+ chars)
                if name_candidate.isalpha() and len(name_candidate) >= 2:
                    # Don't overwrite a lead-form name (which is more reliable)
                    if not user_profiles[session_id].get("name"):
                        user_profiles[session_id]["name"] = name_candidate.capitalize()
            except IndexError:
                pass
            break

    # ── Email detection ───────────────────────────────────────────────────────
    words = message.split()
    for word in words:
        word = word.strip(".,!?<>")
        if "@" in word and "." in word.split("@")[-1]:
            if not user_profiles[session_id].get("email"):
                user_profiles[session_id]["email"] = word.lower()
            break


def get_user_info(session_id: str) -> dict:
    return user_profiles.get(session_id, {})
