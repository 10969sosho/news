# Sistem Deteksi Hoaks Berbasis Agentic AI Otonom (ReAct + RAG)

Implementasi lengkap sistem verifikasi fakta otonom berbahasa Indonesia yang memadukan **Agentic AI**, **Large Language Models (LLM)**, dan **Retrieval-Augmented Generation (RAG)** berbasis kerangka kerja **ReAct (Reasoning and Acting)**.

> 📄 **Rujukan Ilmiah**:  
> Rabiatul Adwiya, Achmad Arif Munaji, Airways Parlindungan Siahaan.  
> *"RANCANG BANGUN SISTEM DETEKSI HOAKS BERBASIS AGENTIC AI OTONOM"*,  
> **Jurnal Khatulistiwa Informatika**, Vol. 14 No. 1, Juni 2026, Hal. 6–13.  
> File paper: [`hoax.pdf`](./hoax.pdf)

---

## 🏛️ Arsitektur Sistem Sesuai Paper

Sistem merealisasikan **Algoritma 1** (ReAct Fact-Checking Loop):
1. **Dekomposisi Klaim ($Q \leftarrow \text{Dekomposisi}(C)$)**: Memecah klaim kompleks menjadi 2–4 sub-pertanyaan faktual spesifik berbahasa Indonesia.
2. **Siklus ReAct ($N \le 5$ iterasi, $\tau \ge 0.85$)**:
   - **Reasoning (`thought`)**: Evaluasi kecukupan bukti terhadap klaim.
   - **Action (`action`)**: Pencarian eksternal jika bukti belum konklusif.
   - **Retrieval RAG**: Pencarian web dinamis (Web Search API / DuckDuckGo fallback) + Vector Store (ChromaDB).
   - **Ranking & Assesment**: Perangkingan bukti kredibel (portal cek fakta tepercaya) dan penilaian ambang batas keyakinan ($\tau$).
3. **Putusan & Transparansi**:
   - Status: `Didukung` (Supported), `Ditolak` (Refuted), atau `Not Enough Information` (NEI).
   - Menyajikan **bukti rujukan terverifikasi** dan **jejak penalaran (reasoning chain)** transparan.

---

## 📁 Struktur Direktori

```
HOAX/
├── backend/
│   ├── app/
│   │   ├── agent/             # ReAct loop, model data Pydantic, prompts Bahasa Indonesia
│   │   ├── rag/               # Web search dinamis + ChromaDB vector store
│   │   ├── evaluation/        # Script benchmark & 20+ dataset klaim ground truth
│   │   ├── config.py          # Konfigurasi LLM & Search
│   │   └── main.py            # FastAPI REST & SSE streaming endpoints
│   ├── requirements.txt
│   └── run_server.py
├── frontend/                  # Next.js 14 Dashboard modern dengan Tailwind CSS & SSE
│   ├── src/app/
│   └── package.json
├── desktop_gui/
│   └── app_gui.py             # Desktop GUI CustomTkinter (Sesuai Bab 3.1 Paper)
├── deploy/
│   ├── ecosystem.config.js    # PM2 Process Manager
│   ├── nginx-subdomain.conf   # Template Reverse Proxy Nginx
│   └── setup_alurelab.sh      # Skrip deployment SSH server Alurelab (sesuai SOP)
├── .env.example               # Template environment variables
└── hoax.pdf                   # Dokumentasi / Paper acuan
```

---

## 🚀 Panduan Menjalankan Secara Lokal

### 1. Konfigurasi Environment
Salin file `.env.example` ke `.env`:
```bash
cp .env.example .env
```
Isi API key yang lu miliki di `.env`:
- `LLM_PROVIDER`: `openai` atau `gemini`
- `OPENAI_API_KEY`: API Key OpenAI (untuk GPT-4o) atau `GEMINI_API_KEY`
- `SEARCH_PROVIDER`: `duckduckgo` (bebas biaya, tanpa API key) atau `tavily`

### 2. Menjalankan Backend (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_server.py
```
Backend berjalan di: `http://localhost:8000` (Dokumentasi Swagger di `http://localhost:8000/docs`).

### 3. Menjalankan Frontend (Next.js Dashboard)
Di terminal baru:
```bash
cd frontend
npm install
npm run dev
```
Buka di browser: `http://localhost:3000`.

### 4. Menjalankan Desktop GUI (CustomTkinter)
Sesuai rancangan pada Bab 3.1 paper:
```bash
cd desktop_gui
python app_gui.py
```

### 5. Menjalankan Benchmark Kinerja (Evaluasi Metrik Paper)
Untuk menguji akurasi, presisi, recall, dan F1-score pada dataset klaim:
```bash
cd backend
python app/evaluation/benchmark.py
```

---

## 🌐 Panduan Hosting di Server Alurelab

Server: `emerald.hidden-server.net:31988` (User: `alurelab`)

Sesuai **SOP Server Alurelab**:
1. Push kode lokal ke Git repository (misal: GitHub / GitLab).
2. Login ke SSH Alurelab:
   ```bash
   ssh alurelab
   ```
3. Pull repo di folder bersih `~/repositories/`:
   ```bash
   cd ~/repositories/hoax
   git pull origin main
   ```
4. Salin kode ke folder subdomain tujuan (misal: `/home/alurelab/antihoax.domainanda.com`):
   ```bash
   # Jalankan skrip otomatis yang sudah disiapkan:
   bash ~/repositories/hoax/deploy/setup_alurelab.sh
   ```
5. Konfigurasi subdomain di Nginx/Apache cPanel mengarah ke port 3000 (frontend) dan reverse proxy `/api` ke port 8000 (backend).
