import sys
import os
sys.path.append(os.path.dirname(__file__))

import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import Optional

from utils import add_message, save_chat_to_db, save_lead_to_db, save_user_from_lead, init_db
from brain import get_answer
from store import load_and_split, add_documents


# ─────────────────────────────────────────────────────────────────────────────
# App Lifespan  (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────
# ✅ STARTUP (FIXED FOR RENDER)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
<<<<<<< HEAD
    print("--- Genkit AI Backend Starting ---")
    init_db()
    print("--- Database Initialized ---")
    docs = load_and_split()
    add_documents(docs)
    print("--- Vector DB Ready ---")
=======
    print("🚀 Starting...")

    try:
        docs = load_and_split()

        if docs:
            add_documents(docs)

        print("✅ Vector DB Ready")

    except Exception as e:
        print("❌ Startup Error:", e)

>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174
    yield
    print("--- Genkit AI Backend Shutting Down ---")


app = FastAPI(
    title="Genkit AI Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# ✅ CORS (FRONTEND FIX)
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change later for production
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)


<<<<<<< HEAD
# ─────────────────────────────────────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────────────────────────────────────

=======
# ─────────────────────────────────────────────
# ✅ MODELS
# ─────────────────────────────────────────────
>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174
class ChatRequest(BaseModel):
    q: str
    session_id: Optional[str] = None

    @field_validator("q")
    @classmethod
    def q_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty.")
        if len(v) > 1000:
            raise ValueError("Query too long (max 1000 characters).")
        return v.strip()


class LeadRequest(BaseModel):
    name: str
    email: str
    session_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name is required.")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        v = v.strip()
        if not v or "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("A valid email address is required.")
        return v.lower()


<<<<<<< HEAD
# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health-check endpoint for uptime monitors."""
    return {"status": "ok", "service": "Genkit AI Chatbot"}
=======
# ─────────────────────────────────────────────
# ✅ LEAD API
# ─────────────────────────────────────────────
@app.post("/lead")
def capture_lead(data: Lead):
    try:
        save_chat(data.name, data.email)
        return {"status": "ok"}
    except Exception as e:
        print("Lead Error:", e)
        return {"status": "error"}
>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174


# ─────────────────────────────────────────────
# ✅ CHAT API (STREAM SAFE)
# ─────────────────────────────────────────────
@app.post("/chat")
<<<<<<< HEAD
async def chat(req: ChatRequest):
=======
def chat(req: ChatRequest):

>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174
    session_id = req.session_id or str(uuid.uuid4())
    add_message(session_id, "user", req.q)

    def generator():
<<<<<<< HEAD
        full_reply = ""
        for chunk in get_answer(req.q, session_id):
            full_reply += chunk
            yield chunk

        # Persist to DB only on successful, non-error replies
        if full_reply and "⚠️" not in full_reply:
            add_message(session_id, "assistant", full_reply)
            save_chat_to_db(req.q, full_reply)
=======
        full = ""

        try:
            for chunk in stream_answer(req.q, session_id):
                full += chunk
                yield chunk

        except Exception as e:
            print("STREAM ERROR:", e)
            yield "⚠️ Server error. Please try again."

        finally:
            if full:
                add_message(session_id, "assistant", full)

                try:
                    save_chat(req.q, full)
                except:
                    pass
>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174

    return StreamingResponse(
        generator(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Session-Id": session_id},
    )


<<<<<<< HEAD
@app.post("/lead")
async def submit_lead(req: LeadRequest):
    save_lead_to_db(req.name, req.email)
    # Update in-memory profile so subsequent AI replies are personalised
    if req.session_id:
        save_user_from_lead(req.session_id, req.name, req.email)
    return {"status": "ok", "message": "Lead saved successfully."}


# ─────────────────────────────────────────────────────────────────────────────
# Static Files  (serves frontend at /)
# ─────────────────────────────────────────────────────────────────────────────

frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {frontend_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
=======
# ─────────────────────────────────────────────
# ✅ HEALTH CHECK (IMPORTANT FOR RENDER)
# ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────
# ✅ SERVE FRONTEND (SAFE VERSION)
# ─────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print("⚠️ Frontend folder not found")
>>>>>>> 569545dffd34f71451109b0ee05c53b997d18174
