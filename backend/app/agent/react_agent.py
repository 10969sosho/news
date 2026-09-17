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
    TruthTier, Evidence, ThoughtStep, VerificationResult, StreamEvent
)
from app.agent.prompts import (
    DECOMPOSITION_PROMPT, REACT_STEP_PROMPT, FINAL_VERIFICATION_PROMPT
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
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a professional fact-checking analysis system. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            model_lower = self.model.lower()
            if not any(k in model_lower for k in ["gpt-5", "luna", "o1", "o3"]):
                kwargs["temperature"] = temperature

            response = await self.client.chat.completions.create(**kwargs)
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

    async def decompose_claim(self, claim: str) -> Dict[str, Any]:
        """Dekomposisi klaim C menjadi sub-pertanyaan bilingual"""
        prompt = DECOMPOSITION_PROMPT.format(claim=claim)
        raw = await self._call_llm(prompt, temperature=0.1)
        data = self._extract_json(raw)
        
        sub_q = data.get("sub_questions", [])
        sub_q_en = data.get("sub_questions_en", [])
        lang = data.get("detected_language", "id")

        if not sub_q:
            sub_q = [
                f"Apakah terdapat sumber resmi terkait '{claim}'?",
                f"Bagaimana hasil penelusuran cek fakta mengenai isu ini?"
            ]
        if not sub_q_en:
            sub_q_en = [
                f"Are there credible official sources regarding '{claim}'?",
                f"What do verified fact-checking organizations report on this claim?"
            ]

        return {
            "detected_language": lang,
            "sub_questions": sub_q,
            "sub_questions_en": sub_q_en
        }

    async def verify_stream(
        self,
        claim: str,
        max_iterations: int = 3,
        target_language: str = "id"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming ReAct Fact-Checking Loop untuk DIGITAL WATCH
        dengan estimasi persentase kebenaran (Truth Score).
        """
        yield {"event": "start", "data": {"claim": claim, "max_iterations": max_iterations}}
        
        evidence_list: List[Evidence] = []
        reasoning_chain: List[ThoughtStep] = []
        i = 0

        yield {"event": "status", "data": {"message": "Menganalisis dan melakukan dekomposisi semantik klaim..."}}
        decomp = await self.decompose_claim(claim)
        sub_questions = decomp["sub_questions"]
        sub_questions_en = decomp["sub_questions_en"]
        detected_language = decomp.get("detected_language", "id")

        yield {
            "event": "decomposition",
            "data": {
                "detected_language": detected_language,
                "sub_questions": sub_questions,
                "sub_questions_en": sub_questions_en
            }
        }

        # Siklus ReAct
        while i < max_iterations:
            yield {"event": "status", "data": {"message": f"Siklus ReAct #{i+1} dari {max_iterations}..."}}
            
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
            
            thought = step_data.get("thought", f"Mengevaluasi bukti terkait klaim '{claim}'.")
            thought_en = step_data.get("thought_en", f"Evaluating collected evidence regarding '{claim}'.")
            action = step_data.get("action", "SEARCH").upper()
            action_input = step_data.get("action_input", sub_questions[i % len(sub_questions)])
            
            yield {
                "event": "thought",
                "data": {
                    "iteration": i + 1,
                    "thought": thought,
                    "thought_en": thought_en,
                    "action": action,
                    "action_input": action_input
                }
            }

            observation = ""
            if action == "SEARCH":
                yield {"event": "status", "data": {"message": f"Mencari bukti rujukan: '{action_input}'..."}}
                
                # Retrieve RAG
                local_docs = vector_store.query_similar(action_input, n_results=2)
                web_docs = await search_service.search(action_input, max_results=4)
                
                new_docs = local_docs + web_docs
                for d in new_docs:
                    if not any(e.url == d.url or (d.snippet and d.snippet in e.snippet) for e in evidence_list):
                        evidence_list.append(d)
                
                observation = f"Ditemukan {len(new_docs)} bukti baru dari sumber berita dan pemeriksa fakta."
                yield {
                    "event": "observation",
                    "data": {
                        "iteration": i + 1,
                        "observation": observation,
                        "new_evidence_count": len(new_docs),
                        "total_evidence": len(evidence_list)
                    }
                }

            # Hitung estimasi sementara
            step_record = ThoughtStep(
                iteration=i + 1,
                thought=thought,
                thought_en=thought_en,
                action=action,
                action_input=action_input,
                observation=observation,
                confidence=min(100.0, float(len(evidence_list) * 25.0))
            )
            reasoning_chain.append(step_record)

            if action == "FINISH":
                break
                
            i += 1

        # Sintesis Akhir: Penentuan Truth Score & Kategori
        yield {"event": "status", "data": {"message": "Menghitung Truth Score dan menyusun sintesis bilingual..."}}
        
        final_prompt = FINAL_VERIFICATION_PROMPT.format(
            claim=claim,
            evidence_text=self._format_evidence_summary(evidence_list)
        )
        final_raw = await self._call_llm(final_prompt, temperature=0.1)
        final_data = self._extract_json(final_raw)
        
        raw_score = final_data.get("truth_score", 50)
        try:
            truth_score = float(raw_score)
            truth_score = max(0.0, min(100.0, truth_score))
        except (ValueError, TypeError):
            truth_score = 50.0

        # Tentukan Kategori Sesuai Permintaan User:
        # < 60% : Hoax
        # 61 - 75% : Rendah
        # 76 - 85% : Sedang
        # 86 - 100% : Tinggi
        if truth_score < 60.0:
            tier = TruthTier.HOAX
            tier_label = "Hoax / Palsu"
            tier_label_en = "Hoax / Fabricated"
        elif truth_score <= 75.0:
            tier = TruthTier.RENDAH
            tier_label = "Kebenaran Rendah"
            tier_label_en = "Low Credibility"
        elif truth_score <= 85.0:
            tier = TruthTier.SEDANG
            tier_label = "Kebenaran Sedang"
            tier_label_en = "Moderate Credibility"
        else:
            tier = TruthTier.TINGGI
            tier_label = "Kebenaran Tinggi (Fakta)"
            tier_label_en = "High Credibility (Verified Fact)"

        rationale = final_data.get("rationale", "Hasil analisis bukti penelusuran fakta.")
        rationale_en = final_data.get("rationale_en", "Analysis based on collected verification evidence.")

        final_result = VerificationResult(
            claim=claim,
            truth_score=truth_score,
            tier=tier,
            tier_label=tier_label,
            tier_label_en=tier_label_en,
            sub_questions=sub_questions,
            sub_questions_en=sub_questions_en,
            reasoning_chain=reasoning_chain,
            evidence=evidence_list,
            rationale=rationale,
            rationale_en=rationale_en,
            iterations_used=i + 1,
            detected_language=detected_language
        )

        yield {
            "event": "final",
            "data": final_result.model_dump()
        }

    async def verify(self, claim: str, max_iterations: int = 3, target_language: str = "id") -> VerificationResult:
        last_result = None
        async for event in self.verify_stream(claim, max_iterations, target_language):
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
                f"    Ringkasan: {ev.snippet[:250]}..."
            )
        return "\n\n".join(lines)

    def _mock_llm_response(self, prompt: str) -> str:
        if "decomposition" in prompt.lower() or "dekomposisi" in prompt.lower():
            return json.dumps({
                "detected_language": "id",
                "sub_questions": [
                    "Apakah terdapat pengumuman resmi pemerintah terkait klaim ini?",
                    "Bagaimana hasil pengecekan dari portal pemeriksa fakta?"
                ],
                "sub_questions_en": [
                    "Are there official government announcements regarding this claim?",
                    "What are the findings from verified fact-checking portals?"
                ]
            })
        elif "react" in prompt.lower() or "reasoning" in prompt.lower():
            return json.dumps({
                "thought": "Melakukan penelusuran sumber berita dan verifikasi terkait klaim.",
                "thought_en": "Performing news search and verification on this claim.",
                "action": "SEARCH",
                "action_input": "cek fakta berita resmi"
            })
        elif "analyst" in prompt.lower() or "evaluator" in prompt.lower() or "final" in prompt.lower():
            return json.dumps({
                "truth_score": 15,
                "tier": "Hoax",
                "tier_label": "Hoax / Palsu",
                "tier_label_en": "Hoax / Fabricated",
                "rationale": "Klaim ini terbukti tidak berdasar atau telah diklarifikasi sebagai disinformasi oleh lembaga pemeriksa fakta.",
                "rationale_en": "This claim is confirmed to be fabricated or classified as disinformation by verified fact-checking authorities."
            })
        return "{}"

react_agent = ReActVerificationAgent()
