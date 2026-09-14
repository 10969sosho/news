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
    title="Sistem Deteksi Hoaks Berbasis Agentic AI Otonom",
    description="Implementasi sistem verifikasi fakta otonom ReAct (Reasoning and Acting) + RAG sesuai paper Jurnal Khatulistiwa Informatika 2026",
    version="1.0.0"
)

# Enable CORS for Next.js / Web frontend
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
        "service": "antihoax-react-agent",
        "llm_provider": settings.LLM_PROVIDER,
        "search_provider": settings.SEARCH_PROVIDER,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "max_iterations": settings.MAX_ITERATIONS
    }

@app.post("/api/verify", response_model=VerificationResult)
async def verify_claim(req: ClaimRequest):
    """Verifikasi klaim secara langsung (non-streaming JSON result)."""
    if not req.claim.strip():
        raise HTTPException(status_code=400, detail="Klaim tidak boleh kosong.")
    
    max_iter = req.max_iterations or settings.MAX_ITERATIONS
    tau = req.confidence_threshold or settings.CONFIDENCE_THRESHOLD
    
    result = await react_agent.verify(
        claim=req.claim,
        max_iterations=max_iter,
        tau=tau
    )
    return result

@app.get("/api/verify/stream")
async def verify_claim_stream(
    claim: str = Query(..., description="Klaim yang akan diperiksa"),
    tau: float = Query(0.85, description="Threshold keyakinan"),
    max_iterations: int = Query(5, description="Maksimum iterasi")
):
    """
    Verifikasi klaim dengan streaming SSE (Server-Sent Events) secara live.
    Frontend dapat mendengarkan event: 'start', 'decomposition', 'thought', 'action', 'observation', 'assessment', 'final'.
    """
    if not claim.strip():
        raise HTTPException(status_code=400, detail="Klaim tidak boleh kosong.")

    async def event_generator():
        async for item in react_agent.verify_stream(claim, max_iterations, tau):
            yield {
                "event": item["event"],
                "data": json.dumps(item["data"], ensure_ascii=False)
            }

    return EventSourceResponse(event_generator())

@app.post("/api/kb/add")
async def add_knowledge(doc_id: str, title: str, text: str, url: str, label: str):
    """Menambahkan data klarifikasi fakta ke basis data vektor lokal (ChromaDB)."""
    vector_store.add_fact_check(doc_id, title, text, url, label)
    return {"status": "success", "message": f"Artikel '{title}' berhasil disimpan ke ChromaDB."}

# Mount static frontend jika sudah di-build
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/out"))
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        target = os.path.join(static_dir, full_path)
        if os.path.exists(target) and not os.path.isdir(target):
            return FileResponse(target)
        index_file = os.path.join(static_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend static file not found"}
