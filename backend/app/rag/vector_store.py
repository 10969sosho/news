import os
import logging
from typing import List, Optional
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
except ImportError:
    chromadb = None
    ChromaSettings = None
from app.config import settings
from app.agent.models import Evidence

logger = logging.getLogger("antihoax.vector_store")

class VectorStoreManager:
    def __init__(self):
        self.client = None
        self.collection = None
        
        if chromadb is None:
            logger.warning("Pustaka 'chromadb' belum terinstall. Basis data vektor lokal nonaktif.")
            return

        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        # Inisialisasi koleksi pengetahuan hoaks lokal
        self.collection = self.client.get_or_create_collection(
            name="fact_checks_kb",
            metadata={"description": "Basis pengetahuan verifikasi fakta lokal"}
        )
        logger.info(f"ChromaDB diinisialisasi di {persist_dir}, total data: {self.collection.count()}")

    def add_fact_check(self, doc_id: str, title: str, text: str, url: str, label: str):
        """Menyimpan hasil klarifikasi / artikel fakta ke ChromaDB."""
        try:
            self.collection.upsert(
                ids=[doc_id],
                documents=[f"Judul: {title}\nIsi: {text}\nStatus: {label}"],
                metadatas=[{"title": title, "url": url, "label": label}]
            )
            logger.info(f"Tersimpan ke Vector DB: {title}")
        except Exception as e:
            logger.error(f"Gagal menyimpan ke ChromaDB: {e}")

    def query_similar(self, query: str, n_results: int = 3) -> List[Evidence]:
        """Mencari dokumen fakta mirip dari basis data vektor lokal."""
        try:
            if not self.collection or self.collection.count() == 0:
                return []
                
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            
            evidences = []
            if results and "documents" in results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    dist = results["distances"][0][i] if "distances" in results and results["distances"] else 0.5
                    # Konversi jarak cosine/l2 ke confidence score (0 - 1)
                    score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                    
                    evidences.append(
                        Evidence(
                            id=results["ids"][0][i],
                            title=metadata.get("title", "Klarifikasi Basis Data"),
                            url=metadata.get("url", "#basis-data-lokal"),
                            snippet=doc,
                            source_type="local_kb",
                            relevance_score=score
                        )
                    )
            return evidences
        except Exception as e:
            logger.warning(f"Error saat query ChromaDB: {e}")
            return []

vector_store = VectorStoreManager()
