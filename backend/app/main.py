import json
import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.agent.models import ClaimRequest, VerificationResult
from app.agent.react_agent import react_agent
from app.rag.vector_store import vector_store

app = FastAPI(
    title="DIGITAL WATCH (WEB ANALYZE TRUTH AND CHECKING HUB)",
    description="Sistem Verifikasi Fakta & Deteksi Hoaks Berbasis Agentic AI Otonom",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "system": "DIGITAL WATCH (WEB ANALYZE TRUTH AND CHECKING HUB)",
        "service": "digital-watch-agent",
        "llm_provider": settings.LLM_PROVIDER,
        "model": settings.OPENAI_MODEL,
        "search_engine": "Google News RSS + Multi-Provider"
    }

@app.post("/api/verify", response_model=VerificationResult)
async def verify_claim(req: ClaimRequest):
    """Verifikasi klaim secara langsung (non-streaming)."""
    if not req.claim.strip():
        raise HTTPException(status_code=400, detail="Teks klaim tidak boleh kosong.")
    
    max_iter = req.max_iterations or 3
    target_lang = req.target_language or "id"
    
    result = await react_agent.verify(
        claim=req.claim,
        max_iterations=max_iter,
        target_language=target_lang
    )
    return result

@app.get("/api/verify/stream")
async def verify_claim_stream(
    claim: str = Query(..., description="Klaim yang akan diperiksa"),
    max_iterations: int = Query(3, description="Maksimum iterasi ReAct"),
    lang: str = Query("id", description="Bahasa interface: 'id' atau 'en'")
):
    """
    Verifikasi klaim dengan Server-Sent Events (SSE) streaming real-time.
    """
    if not claim.strip():
        raise HTTPException(status_code=400, detail="Teks klaim tidak boleh kosong.")

    async def event_generator():
        async for item in react_agent.verify_stream(claim, max_iterations, lang):
            yield {
                "event": item["event"],
                "data": json.dumps(item["data"], ensure_ascii=False)
            }

    return EventSourceResponse(event_generator(), ping=5)

@app.post("/api/kb/add")
async def add_knowledge(doc_id: str, title: str, text: str, url: str, label: str):
    vector_store.add_fact_check(doc_id, title, text, url, label)
    return {"status": "success", "message": f"Dokumen '{title}' berhasil disimpan."}
