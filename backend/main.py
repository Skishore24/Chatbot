import os
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting...")

    docs = load_and_split()
    add_documents(docs)

    print("✅ Vector DB Ready")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    q: str
    session_id: Optional[str] = None


class Lead(BaseModel):
    name: str
    email: str


@app.post("/lead")
def capture_lead(data: Lead):
    save_chat(data.name, data.email)
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    add_message(session_id, "user", req.q)

    def generator():
        full = ""

        for chunk in stream_answer(req.q, session_id):
            full += chunk
            yield chunk

        if full:
            add_message(session_id, "assistant", full)
            save_chat(req.q, full)

    return StreamingResponse(
        generator(),
        media_type="text/plain",
        headers={"X-Session-Id": session_id}
    )


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")