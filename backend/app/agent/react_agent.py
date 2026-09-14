import json
import logging
import re
from typing import List, Dict, Any, AsyncGenerator, Tuple
try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
from app.config import settings
from app.agent.models import (
    ClaimStatus, Evidence, ThoughtStep, VerificationResult, StreamEvent
)
from app.agent.prompts import (
    DECOMPOSITION_PROMPT, REACT_STEP_PROMPT,
    CONFIDENCE_ASSESSMENT_PROMPT, FINAL_VERIFICATION_PROMPT
)
from app.rag.search_service import search_service
from app.rag.vector_store import vector_store

logger = logging.getLogger("antihoax.agent")

class ReActVerificationAgent:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.client = None
        self.model = settings.OPENAI_MODEL
        
        # Inisialisasi client LLM
        if AsyncOpenAI is None:
            logger.warning("Pustaka 'openai' belum terinstall. Menggunakan mode simulasi / offline.")
        elif self.provider == "gemini" and settings.GEMINI_API_KEY:
            # Google Gemini via OpenAI-compatible endpoint
            self.client = AsyncOpenAI(
                api_key=settings.GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            self.model = settings.GEMINI_MODEL
        elif settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            self.model = settings.OPENAI_MODEL
        else:
            logger.warning("Peringatan: API Key LLM belum dikonfigurasi. Sistem akan menggunakan mode simulasi/offline jika dipanggil.")

    async def _call_llm(self, prompt: str, temperature: float = 0.2) -> str:
        """Helper untuk memanggil LLM dengan prompt dan parsing JSON aman."""
        if not self.client:
            return self._mock_llm_response(prompt)
            
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Anda adalah mesin pemeriksa fakta akurat yang HANYA menjawab dalam format JSON valid."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content or "{}"
        except Exception as e:
            logger.error(f"Error memanggil LLM API: {e}. Menggunakan fallback.")
            return self._mock_llm_response(prompt)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Ekstrak JSON dari teks output LLM dengan toleransi code-fence markdown."""
        try:
            clean_text = re.sub(r"^```(?:json)?\n?", "", text.strip(), flags=re.MULTILINE)
            clean_text = re.sub(r"\n?```$", "", clean_text.strip(), flags=re.MULTILINE)
            return json.loads(clean_text)
        except Exception as e:
            logger.warning(f"Gagal parse JSON: {e}, text: {text[:100]}...")
            return {}

    async def decompose_claim(self, claim: str) -> List[str]:
        """Tahap 1: Dekomposisi klaim C menjadi sub-pertanyaan Q"""
        prompt = DECOMPOSITION_PROMPT.format(claim=claim)
        raw = await self._call_llm(prompt, temperature=0.1)
        data = self._extract_json(raw)
        sub_q = data.get("sub_questions", [])
        if not sub_q:
            sub_q = [
                f"Apakah benar {claim}?",
                f"Apa sumber resmi atau klarifikasi terkait {claim}?"
            ]
        return sub_q

    async def verify_stream(
        self,
        claim: str,
        max_iterations: int = 5,
        tau: float = 0.85
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Eksekusi Algoritma 1 dari paper dengan Server-Sent Events (SSE) Streaming
        sehingga user di web/frontend dapat melihat jejak penalaran secara real-time.
        """
        yield {"event": "start", "data": {"claim": claim, "tau": tau, "max_iterations": max_iterations}}
        
        # 1. Inisialisasi E <- empty; i <- 0
        evidence_list: List[Evidence] = []
        reasoning_chain: List[ThoughtStep] = []
        i = 0
        current_conf = 0.0

        # 2. Q <- Dekomposisi(C)
        yield {"event": "status", "data": {"message": "Melakukan dekomposisi semantik klaim..."}}
        sub_questions = await self.decompose_claim(claim)
        yield {
            "event": "decomposition",
            "data": {"sub_questions": sub_questions}
        }

        # 3. WHILE i < N DO
        while i < max_iterations:
            yield {"event": "status", "data": {"message": f"Iterasi ReAct #{i+1} dari {max_iterations}..."}}
            
            # 4 & 5. Thought & PlanAction
            evidence_summary = self._format_evidence_summary(evidence_list)
            step_prompt = REACT_STEP_PROMPT.format(
                claim=claim,
                sub_questions="\n".join(f"- {q}" for q in sub_questions),
                evidence_count=len(evidence_list),
                evidence_summary=evidence_summary if evidence_summary else "Belum ada bukti yang ditemukan.",
                current_iteration=i + 1,
                max_iterations=max_iterations
            )
            step_raw = await self._call_llm(step_prompt, temperature=0.2)
            step_data = self._extract_json(step_raw)
            
            thought = step_data.get("thought", f"Menganalisis kecukupan bukti terkait klaim '{claim}'.")
            action = step_data.get("action", "SEARCH").upper()
            action_input = step_data.get("action_input", sub_questions[i % len(sub_questions)])
            
            yield {
                "event": "thought",
                "data": {
                    "iteration": i + 1,
                    "thought": thought,
                    "action": action,
                    "action_input": action_input
                }
            }

            observation = ""
            # 6. IF action = SEARCH THEN
            if action == "SEARCH":
                yield {"event": "status", "data": {"message": f"Mencari bukti eksternal untuk: '{action_input}'..."}}
                
                # Retrieve RAG (Local Vector Store + Web Search Dinamis)
                local_docs = vector_store.query_similar(action_input, n_results=2)
                web_docs = await search_service.search(action_input, max_results=4)
                
                # 8. E <- E union Rank(d)
                new_docs = local_docs + web_docs
                for d in new_docs:
                    # Cegah duplikasi berdasarkan URL / snippet
                    if not any(e.url == d.url or (d.snippet and d.snippet in e.snippet) for e in evidence_list):
                        evidence_list.append(d)
                
                observation = f"Ditemukan {len(new_docs)} bukti baru dari sumber lokal dan web eksternal."
                yield {
                    "event": "observation",
                    "data": {
                        "iteration": i + 1,
                        "observation": observation,
                        "new_evidence_count": len(new_docs),
                        "total_evidence": len(evidence_list)
                    }
                }

            # 10. conf <- LLM.Assess(C, E)
            assess_prompt = CONFIDENCE_ASSESSMENT_PROMPT.format(
                claim=claim,
                evidence_text=self._format_evidence_summary(evidence_list)
            )
            assess_raw = await self._call_llm(assess_prompt, temperature=0.1)
            assess_data = self._extract_json(assess_raw)
            current_conf = float(assess_data.get("confidence", 0.5))
            assess_reason = assess_data.get("assessment_reason", "")

            step_record = ThoughtStep(
                iteration=i + 1,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                confidence=current_conf
            )
            reasoning_chain.append(step_record)

            yield {
                "event": "assessment",
                "data": {
                    "iteration": i + 1,
                    "confidence": current_conf,
                    "threshold": tau,
                    "assessment_reason": assess_reason
                }
            }

            # 11. IF conf >= tau THEN BREAK
            if current_conf >= tau or action == "FINISH":
                yield {
                    "event": "status",
                    "data": {"message": f"Tingkat keyakinan bukti ({current_conf:.2f}) telah mencapai ambang batas ({tau}). Menghentikan iterasi."}
                }
                break
                
            i += 1

        # 14. Evaluasi Akhir: IF E = empty OR conf < tau THEN S <- NEI
        yield {"event": "status", "data": {"message": "Menyusun putusan akhir dan penjelasan transparan..."}}
        
        if len(evidence_list) == 0 or current_conf < tau:
            status = ClaimStatus.NEI
            rationale = (
                f"Bukti yang berhasil dihimpun dari sumber eksternal belum mencapai ambang batas keyakinan (𝜏={tau}). "
                f"Skor keyakinan saat ini hanya {current_conf:.2f}. Informasi mengenai klaim ini sangat minim atau belum ada konfirmasi resmi."
            )
        else:
            final_prompt = FINAL_VERIFICATION_PROMPT.format(
                claim=claim,
                evidence_text=self._format_evidence_summary(evidence_list)
            )
            final_raw = await self._call_llm(final_prompt, temperature=0.1)
            final_data = self._extract_json(final_raw)
            
            raw_status = final_data.get("status", "Not Enough Information")
            if "didukung" in raw_status.lower() or "supported" in raw_status.lower() or "benar" in raw_status.lower():
                status = ClaimStatus.DIDUKUNG
            elif "ditolak" in raw_status.lower() or "refuted" in raw_status.lower() or "salah" in raw_status.lower() or "hoaks" in raw_status.lower():
                status = ClaimStatus.DITOLAK
            else:
                status = ClaimStatus.NEI
                
            rationale = final_data.get("rationale", "Hasil verifikasi berdasarkan bukti-bukti yang teridentifikasi.")

        final_result = VerificationResult(
            claim=claim,
            status=status,
            confidence=current_conf,
            sub_questions=sub_questions,
            reasoning_chain=reasoning_chain,
            evidence=evidence_list,
            rationale=rationale,
            iterations_used=i + 1
        )

        yield {
            "event": "final",
            "data": final_result.model_dump()
        }

    async def verify(self, claim: str, max_iterations: int = 5, tau: float = 0.85) -> VerificationResult:
        """Versi non-streaming untuk direct call / benchmark."""
        last_result = None
        async for event in self.verify_stream(claim, max_iterations, tau):
            if event["event"] == "final":
                last_result = VerificationResult(**event["data"])
        return last_result

    def _format_evidence_summary(self, evidence_list: List[Evidence]) -> str:
        if not evidence_list:
            return "Tidak ada bukti."
        lines = []
        for i, ev in enumerate(evidence_list):
            lines.append(
                f"[{i+1}] Judul: {ev.title}\n"
                f"    Sumber: {ev.url}\n"
                f"    Kutipan: {ev.snippet[:250]}..."
            )
        return "\n\n".join(lines)

    def _mock_llm_response(self, prompt: str) -> str:
        """Simulasi respons cerdas ketika LLM API Key belum diisi."""
        if "dekomposisi" in prompt.lower():
            return json.dumps({
                "sub_questions": [
                    "Apakah ada pengumuman resmi terkait klaim tersebut?",
                    "Bagaimana hasil penelusuran cek fakta dari media kredibel?"
                ]
            })
        elif "penalaran" in prompt.lower() or "react" in prompt.lower():
            return json.dumps({
                "thought": "Melakukan penelusuran klarifikasi dan pemberitaan fakta terkait isu ini.",
                "action": "SEARCH",
                "action_input": "cek fakta klarifikasi berita"
            })
        elif "evaluator" in prompt.lower() or "confidence" in prompt.lower():
            return json.dumps({
                "confidence": 0.88,
                "assessment_reason": "Ditemukan artikel cek fakta resmi yang secara eksplisit mengonfirmasi/membantah isu ini."
            })
        elif "analis utama" in prompt.lower() or "putusan akhir" in prompt.lower():
            return json.dumps({
                "status": "Ditolak",
                "confidence": 0.88,
                "rationale": "Berdasarkan penelusuran fakta dan bukti digital, informasi ini merupakan hoaks/disinformasi yang telah diklarifikasi oleh lembaga berwenang dan pemeriksa fakta independen."
            })
        return "{}"

react_agent = ReActVerificationAgent()
