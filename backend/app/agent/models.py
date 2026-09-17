from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TruthTier(str, Enum):
    HOAX = "Hoax"                      # < 60% (Palsu / Disinformasi)
    RENDAH = "Rendah"                  # 61% - 75% (Tingkat Kebenaran Rendah)
    SEDANG = "Sedang"                  # 76% - 85% (Tingkat Kebenaran Sedang)
    TINGGI = "Tinggi"                  # 86% - 100% (Tingkat Kebenaran Tinggi / Fakta)

class ClaimRequest(BaseModel):
    claim: str = Field(..., description="Teks klaim atau berita yang akan diverifikasi (Bahasa Indonesia / English)")
    max_iterations: Optional[int] = Field(3, description="Batas maksimum iterasi ReAct")
    target_language: Optional[str] = Field("id", description="Bahasa utama tampilan: 'id' atau 'en'")

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
    thought_en: Optional[str] = Field(None, description="Reasoning in English")
    action: str = Field(..., description="Tindakan yang diambil (SEARCH, ANALYZE, FINISH)")
    action_input: Optional[str] = Field(None, description="Input untuk tindakan, misal query pencarian")
    observation: Optional[str] = Field(None, description="Hasil observasi dari tindakan yang dilakukan")
    confidence: float = Field(0.0, description="Persentase keyakinan saat ini (0-100)")

class VerificationResult(BaseModel):
    claim: str
    truth_score: float = Field(..., description="Skor kebenaran (0 - 100%)")
    tier: TruthTier = Field(..., description="Kategori tingkat kebenaran (<60 Hoax, 61-75 Rendah, 76-85 Sedang, 86-100 Tinggi)")
    tier_label: str
    tier_label_en: str
    sub_questions: List[str]
    sub_questions_en: List[str] = []
    reasoning_chain: List[ThoughtStep]
    evidence: List[Evidence]
    rationale: str
    rationale_en: str
    iterations_used: int
    detected_language: str = "id"

class StreamEvent(BaseModel):
    event_type: str
    data: Dict[str, Any]
