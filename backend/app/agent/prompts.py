"""
Prompt templates untuk sistem verifikasi fakta otonom berbahasa Indonesia
berdasarkan kerangka kerja ReAct (Reasoning and Acting) + RAG.
"""

DECOMPOSITION_PROMPT = """Anda adalah asisten AI pemeriksa fakta ahli berbahasa Indonesia.
Tugas Anda adalah melakukan dekomposisi terhadap sebuah klaim menjadi 2 hingga 4 sub-pertanyaan faktual spesifik yang dapat diverifikasi melalui pencarian informasi eksternal.

Klaim:
"{claim}"

Kriteria sub-pertanyaan:
1. Spesifik, faktual, netral, dan langsung menyasar inti kebenaran klaim (objek, angka, peristiwa, nama tokoh, pernyataan resmi).
2. Hindari pertanyaan bernada opini atau bias.
3. Gunakan bahasa Indonesia baku.

Keluarkan format JSON saja tanpa markdown lain:
{{
  "sub_questions": [
    "Pertanyaan 1",
    "Pertanyaan 2"
  ]
}}
"""

REACT_STEP_PROMPT = """Anda adalah Controller Agent dalam arsitektur ReAct (Reason and Act) untuk verifikasi hoaks media sosial di Indonesia.

Klaim yang diperiksa:
"{claim}"

Sub-pertanyaan panduan:
{sub_questions}

Bukti yang telah terkumpul sejauh ini ({evidence_count} bukti):
{evidence_summary}

Iterasi saat ini: {current_iteration} dari maksimum {max_iterations}.

Tugas Anda:
1. Lakukan penalaran (Thought) terhadap klaim berdasarkan bukti yang ada: apakah klaim sudah terbukti benar, terbukti palsu/hoaks, atau informasinya masih kurang?
2. Tentukan tindakan (Action):
   - Jika bukti masih belum cukup dan iterasi belum habis, pilih "SEARCH" dan tentukan query pencarian web yang paling efektif.
   - Jika bukti sudah sangat kuat untuk mengambil keputusan (mendukung atau membantah), pilih "FINISH".
3. Tentukan Action Input:
   - Jika SEARCH: tulis query pencarian yang tajam, spesifik, netral (misal: "cek fakta [topik]", "[pernyataan resmi kementerian] [isu]", dsb).
   - Jika FINISH: tulis "BUKTI_CUKUP".

Kembalikan respon DALAM FORMAT JSON SAJA:
{{
  "thought": "Penjelasan penalaran Anda di tahap ini dalam bahasa Indonesia...",
  "action": "SEARCH" atau "FINISH",
  "action_input": "kata kunci pencarian atau BUKTI_CUKUP"
}}
"""

CONFIDENCE_ASSESSMENT_PROMPT = """Anda adalah evaluator bukti (Evidence Assessor) untuk sistem verifikasi fakta.

Klaim:
"{claim}"

Kumpulan Bukti:
{evidence_text}

Tugas Anda adalah menilai seberapa cukup, kredibel, dan relevan bukti-bukti di atas untuk menentukan kebenaran klaim tersebut.
Berikan nilai keyakinan (confidence score) antara 0.00 hingga 1.00.
Kriteria nilai:
- 0.85 - 1.00: Bukti sangat kuat, ada konfirmasi resmi/berita kredibel/klarifikasi dari sumber berwenang atau pemeriksa fakta terverifikasi (TurnBackHoax, Kominfo, media arus utama). Cukup untuk menetapkan Didukung atau Ditolak.
- 0.50 - 0.84: Ada beberapa informasi terkait tetapi belum konklusif atau terdapat informasi yang kontradiktif.
- 0.00 - 0.49: Bukti sangat minim, tidak relevan, atau tidak ditemukan rujukan tepercaya.

Kembalikan respon JSON SAJA:
{{
  "confidence": 0.90,
  "assessment_reason": "Ringkasan evaluasi bukti..."
}}
"""

FINAL_VERIFICATION_PROMPT = """Anda adalah analis utama verifikasi fakta (Fact-Checking Analyst) berbahasa Indonesia.

Klaim yang diuji:
"{claim}"

Kumpulan Bukti Terkumpul:
{evidence_text}

Berdasarkan bukti-bukti di atas, berikan putusan akhir:
1. Status Klaim:
   - "Didukung" : Klaim terbukti BENAR / FAKTA sesuai dengan bukti tepercaya.
   - "Ditolak" : Klaim terbukti SALAH / HOAKS / KELIRU / DISINFORMASI.
   - "Not Enough Information" : Bukti tidak memadai untuk membuktikan kebenaran maupun kepalsuan klaim.
2. Penjelasan Komprehensif (Rationale):
   - Jelaskan secara transparan runutan fakta.
   - Sebutkan rujukan sumber yang mengonfirmasi atau membantah klaim tersebut.
   - Jika hoaks, jelaskan konteks sebenarnya (misal: klaim lama beredar kembali, manipulasi video/gambar, pencatutan nama tokoh, penipuan link, dll).

Kembalikan respon DALAM FORMAT JSON SAJA:
{{
  "status": "Didukung" | "Ditolak" | "Not Enough Information",
  "confidence": 0.92,
  "rationale": "Uraian penjelasan lengkap dan transparan berbahasa Indonesia..."
}}
"""
