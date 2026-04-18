from collections import OrderedDict

chat_history = OrderedDict()
user_profiles = {}

MAX_SESSIONS = 100
MAX_MESSAGES = 50


def add_message(session_id, role, message):
    if session_id not in chat_history:
        chat_history[session_id] = []

        if len(chat_history) > MAX_SESSIONS:
            chat_history.popitem(last=False)

    chat_history[session_id].append({
        "role": role,
        "message": message
    })

    if len(chat_history[session_id]) > MAX_MESSAGES:
        chat_history[session_id] = chat_history[session_id][-MAX_MESSAGES:]


def get_history(session_id):
    return chat_history.get(session_id, [])[-4:]


# 🔥 SMART USER MEMORY
def save_user_info(session_id, message):
    msg = message.lower()

    if session_id not in user_profiles:
        user_profiles[session_id] = {}

    # name
    if "my name is" in msg:
        name = msg.split("my name is")[-1].strip().split()[0]
        user_profiles[session_id]["name"] = name.capitalize()

    # interest tracking
    if "website" in msg:
        user_profiles[session_id]["interest"] = "website"
    elif "app" in msg:
        user_profiles[session_id]["interest"] = "app"
    elif "chatbot" in msg:
        user_profiles[session_id]["interest"] = "chatbot"


def get_user_info(session_id):
    return user_profiles.get(session_id, {})