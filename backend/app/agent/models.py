from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ClaimStatus(str, Enum):
    DIDUKUNG = "Didukung"      # Supported (True / Fakta)
    DITOLAK = "Ditolak"        # Refuted (Hoaks / Salah)
    NEI = "Not Enough Information"  # Belum cukup bukti

class ClaimRequest(BaseModel):
    claim: str = Field(..., description="Teks klaim atau berita yang akan diverifikasi")
    max_iterations: Optional[int] = Field(5, description="Batas maksimum iterasi ReAct")
    confidence_threshold: Optional[float] = Field(0.85, description="Ambang batas keyakinan tau")

class Evidence(BaseModel):
    id: Optional[str] = None
    title: str
    url: str
    snippet: str
    source_type: str = "web"  # "web" | "local_kb"
    relevance_score: Optional[float] = None

class ThoughtStep(BaseModel):
    iteration: int
    thought: str = Field(..., description="Penalaran agen pada tahap ini")
    action: str = Field(..., description="Tindakan yang diambil (SEARCH, ANALYZE, FINISH)")
    action_input: Optional[str] = Field(None, description="Input untuk tindakan, misal query pencarian")
    observation: Optional[str] = Field(None, description="Hasil observasi dari tindakan yang dilakukan")
    confidence: float = Field(0.0, description="Tingkat keyakinan bukti saat ini")

class VerificationResult(BaseModel):
    claim: str
    status: ClaimStatus
    confidence: float
    sub_questions: List[str]
    reasoning_chain: List[ThoughtStep]
    evidence: List[Evidence]
    rationale: str
    iterations_used: int

class StreamEvent(BaseModel):
    event_type: str  # "start" | "decomposition" | "thought" | "action" | "observation" | "assessment" | "final" | "error"
    data: Dict[str, Any]
