import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from database import db, create_document, get_documents
from schemas import Lkpd, Reflection, QuizAttempt, StatusResponse

app = FastAPI(title="Networking Learning API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"ok": True, "service": "Networking Learning API"}

@app.get("/test")
def test_database():
    info = {
        "backend": "running",
        "database_url": bool(os.getenv("DATABASE_URL")),
        "database_name": os.getenv("DATABASE_NAME"),
        "connected": db is not None,
    }
    try:
        if db is not None:
            info["collections"] = db.list_collection_names()
        else:
            info["collections"] = []
    except Exception as e:
        info["error"] = str(e)
    return info

# ------------------- Progress & gating -------------------

def _get_latest(collection: str, user_id: str):
    docs = get_documents(collection, {"user_id": user_id}, limit=1)
    return docs[0] if docs else None

@app.get("/api/status", response_model=StatusResponse)
def status(user_id: str):
    has_lkpd = _get_latest("lkpd", user_id) is not None
    has_reflection = _get_latest("reflection", user_id) is not None

    last_score = None
    qa = _get_latest("quizattempt", user_id)
    if qa and "score" in qa:
        last_score = int(qa["score"]) if qa["score"] is not None else None

    return StatusResponse(user_id=user_id, has_lkpd=has_lkpd, has_reflection=has_reflection, last_score=last_score)

# ------------------- LKPD -------------------

@app.post("/api/lkpd")
def submit_lkpd(payload: Lkpd):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc_id = create_document("lkpd", payload)
    return {"ok": True, "id": doc_id}

# ------------------- Reflection -------------------

@app.post("/api/reflection")
def submit_reflection(payload: Reflection):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Require LKPD first
    if _get_latest("lkpd", payload.user_id) is None:
        raise HTTPException(status_code=400, detail="Complete LKPD before reflection")
    doc_id = create_document("reflection", payload)
    return {"ok": True, "id": doc_id}

# ------------------- Quiz with auto-grading -------------------

# Simple built-in quiz bank for Network Topology
QUIZ_QUESTIONS = [
    {
        "id": "q1",
        "type": "single",
        "question": "Which topology connects all devices to a central hub/switch?",
        "options": ["Bus", "Ring", "Star", "Mesh"],
        "answer": 2
    },
    {
        "id": "q2",
        "type": "single",
        "question": "In which topology does a single break bring the entire network down?",
        "options": ["Bus", "Star", "Hybrid", "Mesh"],
        "answer": 0
    },
    {
        "id": "q3",
        "type": "single",
        "question": "Which topology offers the highest redundancy?",
        "options": ["Bus", "Ring", "Star", "Full Mesh"],
        "answer": 3
    },
]

@app.get("/api/quiz")
def get_quiz():
    # Do not expose answers
    sanitized = [
        {k: v for k, v in q.items() if k != "answer"}
        for q in QUIZ_QUESTIONS
    ]
    return {"questions": sanitized}

@app.post("/api/quiz/submit")
def submit_quiz(payload: QuizAttempt):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Require Reflection first
    if _get_latest("reflection", payload.user_id) is None:
        raise HTTPException(status_code=400, detail="Complete reflection before quiz")

    # Auto-grade
    score = 0
    for q in QUIZ_QUESTIONS:
        qid = q["id"]
        correct_idx = q["answer"]
        user_idx = payload.answers.get(qid)
        if isinstance(user_idx, int) and user_idx == correct_idx:
            score += 1

    attempt = QuizAttempt(user_id=payload.user_id, answers=payload.answers, score=score)
    create_document("quizattempt", attempt)
    return {"ok": True, "score": score, "total": len(QUIZ_QUESTIONS)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
