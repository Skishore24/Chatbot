import sys
import os
sys.path.append(os.path.dirname(__file__))

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from typing import Optional

from memory import add_message
from rag import stream_answer
from database import save_chat

from embeddings import load_and_split
from vector_db import add_documents


# ─────────────────────────────────────────────
# ✅ STARTUP (FIXED FOR RENDER)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Genkit AI Backend...")

    try:
        docs = load_and_split()

        if docs:
            add_documents(docs)

        print("✅ Vector DB Ready")

    except Exception as e:
        print("❌ Vector DB Error:", e)

    yield


app = FastAPI(lifespan=lifespan)


# ─────────────────────────────────────────────
# ✅ CORS (FRONTEND FIX)
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change later for production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# ✅ MODELS
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    q: str
    session_id: Optional[str] = None


class Lead(BaseModel):
    name: str
    email: str


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


# ─────────────────────────────────────────────
# ✅ CHAT API (STREAM SAFE)
# ─────────────────────────────────────────────
@app.post("/chat")
def chat(req: ChatRequest):

    session_id = req.session_id or str(uuid.uuid4())

    add_message(session_id, "user", req.q)

    def generator():
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

    return StreamingResponse(
        generator(),
        media_type="text/plain",
        headers={"X-Session-Id": session_id}
    )


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
