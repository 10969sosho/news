import httpx
import logging
from typing import List
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
from app.config import settings
from app.agent.models import Evidence

logger = logging.getLogger("antihoax.search")

class SearchService:
    def __init__(self):
        self.provider = settings.SEARCH_PROVIDER
        self.tavily_api_key = settings.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 5) -> List[Evidence]:
        """
        Cari bukti dari web secara dinamis.
        Mencoba Tavily jika ada API key, atau fallback otomatis ke DuckDuckGo.
        """
        logger.info(f"Pencarian web untuk query: '{query}' via provider: {self.provider}")
        
        if self.provider == "tavily" and self.tavily_api_key:
            try:
                results = await self._search_tavily(query, max_results)
                if results:
                    return self._rank_evidence(results, query)
            except Exception as e:
                logger.warning(f"Tavily search gagal: {e}. Beralih ke DuckDuckGo...")

        # Fallback DuckDuckGo
        try:
            results = await self._search_duckduckgo(query, max_results)
            return self._rank_evidence(results, query)
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    async def _search_tavily(self, query: str, max_results: int) -> List[Evidence]:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": [],
            "max_results": max_results,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        evidence_list = []
        for i, item in enumerate(data.get("results", [])):
            evidence_list.append(
                Evidence(
                    id=f"tavily_{i}",
                    title=item.get("title", "Tanpa Judul"),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source_type="web",
                    relevance_score=float(item.get("score", 0.8))
                )
            )
        return evidence_list

    async def _search_duckduckgo(self, query: str, max_results: int) -> List[Evidence]:
        if DDGS is None:
            logger.warning("Pustaka 'duckduckgo_search' belum terinstall.")
            return []
            
        # Tambahkan region Indonesia / konteks id-id untuk hasil lokal
        ddgs = DDGS()
        raw_results = ddgs.text(
            query,
            region="id-id",
            safesearch="moderate",
            max_results=max_results
        )

        evidence_list = []
        for i, item in enumerate(raw_results):
            evidence_list.append(
                Evidence(
                    id=f"ddg_{i}",
                    title=item.get("title", "Tanpa Judul"),
                    url=item.get("href", item.get("link", "")),
                    snippet=item.get("body", item.get("snippet", "")),
                    source_type="web",
                    relevance_score=0.8
                )
            )
        return evidence_list

    def _rank_evidence(self, evidence_list: List[Evidence], query: str) -> List[Evidence]:
        """
        Ranking bukti: memberi bobot ekstra untuk portal pemeriksa fakta tepercaya di Indonesia
        (TurnBackHoax, Kominfo, Antara Cek Fakta, Liputan6 Cek Fakta, Kompas Cek Fakta, dll).
        """
        trusted_domains = [
            "turnbackhoax.id", "kominfo.go.id", "kompas.com/cekfakta",
            "liputan6.com/cek-fakta", "tempo.co/cekfakta", "antaranews.com",
            "republika.co.id", "detik.com", "bbc.com/indonesia", "cnbcindonesia.com"
        ]

        for ev in evidence_list:
            score = ev.relevance_score or 0.7
            url_lower = ev.url.lower()
            snippet_lower = ev.snippet.lower()
            
            # Bonus untuk domain tepercaya
            for domain in trusted_domains:
                if domain in url_lower:
                    score += 0.2
                    break
                    
            # Bonus untuk kata kunci fact-checking
            if any(k in snippet_lower for k in ["cek fakta", "hoaks", "klarifikasi", "keliru", "disinformasi", "faktanya"]):
                score += 0.1
                
            ev.relevance_score = min(score, 1.0)

        # Urutkan berdasarkan relevance_score tertinggi
        evidence_list.sort(key=lambda x: x.relevance_score or 0.0, reverse=True)
        return evidence_list

search_service = SearchService()
