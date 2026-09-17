import asyncio
import httpx
import logging
import re
import urllib.parse
import xml.etree.ElementTree as ET
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
        Urutan:
        1. Google News RSS Cek Fakta Indonesia (paling cepat & kredibel, tanpa blokir IP)
        2. Tavily API (jika ada key)
        3. DuckDuckGo Search (fallback)
        """
        # Bersihkan operator boolean kaku (site:, OR, AND) agar mesin pencari lebih fleksibel
        clean_q = re.sub(r'site:\S+', '', query)
        clean_q = re.sub(r'\b(OR|AND)\b', ' ', clean_q)
        clean_q = re.sub(r'\s+', ' ', clean_q).strip()

        logger.info(f"Pencarian web dinamis untuk: '{clean_q}'")

        # 1. Google News RSS Fact-Check
        try:
            gnews = await self._search_google_news(clean_q, max_results)
            if gnews and len(gnews) > 0:
                logger.info(f"Berhasil menemukan {len(gnews)} berita dari Google News RSS")
                return self._rank_evidence(gnews, clean_q)
        except Exception as e:
            logger.warning(f"Google News RSS error: {e}")

        # 2. Tavily jika ada key
        if self.provider == "tavily" and self.tavily_api_key:
            try:
                results = await self._search_tavily(clean_q, max_results)
                if results:
                    return self._rank_evidence(results, clean_q)
            except Exception as e:
                logger.warning(f"Tavily search gagal: {e}. Beralih ke fallback...")

        # 3. DuckDuckGo fallback
        try:
            results = await self._search_duckduckgo(clean_q, max_results)
            if results:
                return self._rank_evidence(results, clean_q)
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")

        return []

    async def _search_google_news(self, query: str, max_results: int) -> List[Evidence]:
        """Ambil berita dan artikel klarifikasi cek fakta via Google News RSS Indonesia."""
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=id&gl=ID&ceid=ID:id"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            
            root = ET.fromstring(resp.text)
            evidence_list = []
            for i, item in enumerate(root.findall(".//item")[:max_results]):
                title = item.findtext("title", "Klarifikasi Berita")
                link = item.findtext("link", "")
                raw_desc = item.findtext("description", "")
                snippet = re.sub(r'<[^>]+>', ' ', raw_desc).strip()
                
                # Ekstrak nama media jika ada
                source_tag = item.find("source")
                source_name = source_tag.text if source_tag is not None else "Media Cek Fakta"

                evidence_list.append(
                    Evidence(
                        id=f"gnews_{i}",
                        title=f"{title} ({source_name})",
                        url=link,
                        snippet=snippet or title,
                        source_type="web",
                        relevance_score=0.9
                    )
                )
            return evidence_list

    async def _search_tavily(self, query: str, max_results: int) -> List[Evidence]:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_domains": [],
            "max_results": max_results,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
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
            
        def _fetch():
            ddgs = DDGS()
            return list(ddgs.text(
                query,
                region="id-id",
                safesearch="moderate",
                max_results=max_results
            ))

        try:
            raw_results = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=6.0)
        except Exception as e:
            logger.warning(f"DuckDuckGo search timed out or failed: {e}")
            return []

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
            title_lower = ev.title.lower()
            
            # Bonus untuk domain tepercaya
            for domain in trusted_domains:
                if domain in url_lower or domain in title_lower:
                    score += 0.2
                    break
                    
            # Bonus untuk kata kunci fact-checking
            if any(k in snippet_lower or k in title_lower for k in ["cek fakta", "hoaks", "klarifikasi", "keliru", "disinformasi", "faktanya"]):
                score += 0.15
                
            ev.relevance_score = min(score, 1.0)

        # Urutkan berdasarkan relevance_score tertinggi
        evidence_list.sort(key=lambda x: x.relevance_score or 0.0, reverse=True)
        return evidence_list

search_service = SearchService()
