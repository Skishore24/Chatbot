import os
import uuid
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from contextlib import asynccontextmanager

from brain import get_answer
from utils import init_db, add_message, save_chat_to_db, save_lead_to_db, save_user_from_lead
from store import load_and_split, add_documents

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Genkit AI Backend Starting ---")
    # Initialize DB & Vector Store
    init_db()
    docs = load_and_split()
    add_documents(docs)
    yield
    print("--- Genkit AI Backend Shutting Down ---")

app = FastAPI(
    title="Genkit AI Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Session-Id"],
)

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health-check endpoint for uptime monitors."""
    return {"status": "ok", "service": "Genkit AI Chatbot"}

@app.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    add_message(session_id, "user", req.q)

    def generator():
        full_reply = ""
        for chunk in get_answer(req.q, session_id):
            full_reply += chunk
            yield chunk

        # Persist to DB only on successful, non-error replies
        if full_reply and "⚠️" not in full_reply:
            add_message(session_id, "assistant", full_reply)
            save_chat_to_db(req.q, full_reply)

    return StreamingResponse(
        generator(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Session-Id": session_id},
    )

@app.post("/lead")
def submit_lead(req: LeadRequest):
    save_lead_to_db(req.name, req.email)
    # Update in-memory profile so subsequent AI replies are personalised
    if req.session_id:
        save_user_from_lead(req.session_id, req.name, req.email)
    return {"status": "ok", "message": "Lead saved successfully."}

# ─────────────────────────────────────────────
# Static Files  (serves frontend at /)
# ─────────────────────────────────────────────

frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {frontend_path}")

# ─────────────────────────────────────────────
# Dev entry-point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
