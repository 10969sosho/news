"""
Desktop GUI untuk Sistem Deteksi Hoaks Berbasis Agentic AI Otonom
Sesuai Bagian 3.1 Paper: Dibangun menggunakan CustomTkinter.
Menyajikan dashboard verifikasi bagi pengguna untuk memasukkan klaim,
melihat jejak penalaran (reasoning chain) secara real-time, serta
menampilkan bukti pendukung yang relevan beserta tautan sumbernya.
"""

import sys
import os
import threading
import asyncio
import json

# Tambahkan backend ke path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

try:
    import customtkinter as ctk
except ImportError:
    print("Library customtkinter belum terinstall. Install dengan: pip install customtkinter")
    sys.exit(1)

from app.agent.react_agent import react_agent

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AntiHoaxApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistem Verifikasi Fakta Otonom (ReAct + RAG) - ITSNUKA")
        self.geometry("1100x780")
        self.minsize(900, 650)

        # Layout Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar Kiri (Kontrol & Info Parameter)
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="ANTI-HOAX AI\nAGENTIC SYSTEM",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.desc_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Kerangka ReAct + RAG\n(Jurnal Khatulistiwa 2026)",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.desc_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # Parameter tau
        self.tau_label = ctk.CTkLabel(self.sidebar_frame, text="Confidence Threshold (𝜏): 0.85", font=ctk.CTkFont(size=12))
        self.tau_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.tau_slider = ctk.CTkSlider(self.sidebar_frame, from_=0.5, to=0.99, number_of_steps=50, command=self._update_tau)
        self.tau_slider.set(0.85)
        self.tau_slider.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="ew")

        # Parameter N
        self.iter_label = ctk.CTkLabel(self.sidebar_frame, text="Batas Iterasi (N): 5", font=ctk.CTkFont(size=12))
        self.iter_label.grid(row=4, column=0, padx=20, pady=(5, 0), sticky="w")
        self.iter_slider = ctk.CTkSlider(self.sidebar_frame, from_=1, to=10, number_of_steps=9, command=self._update_iter)
        self.iter_slider.set(5)
        self.iter_slider.grid(row=5, column=0, padx=20, pady=(5, 20), sticky="ew")

        # Status Server/Model
        self.info_box = ctk.CTkTextbox(self.sidebar_frame, height=120, font=ctk.CTkFont(size=11))
        self.info_box.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        self.info_box.insert("0.0", "Mode: Agentic ReAct\nModel: GPT-4o\nRAG: ChromaDB + Web\nStatus: Siap Memeriksa")
        self.info_box.configure(state="disabled")

        # Area Utama (Kanan)
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Input Klaim
        self.input_label = ctk.CTkLabel(
            self.main_frame,
            text="Masukkan Teks Klaim / Isu Berita Medsos:",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.input_label.grid(row=0, column=0, sticky="w", pady=(0, 5))

        self.claim_input = ctk.CTkTextbox(self.main_frame, height=70, font=ctk.CTkFont(size=13))
        self.claim_input.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.claim_input.insert("0.0", "Pemerintah bagikan bantuan uang tunai 5 juta rupiah lewat tautan WhatsApp dengan mengisi nomor rekening.")

        # Tombol Verifikasi
        self.verify_btn = ctk.CTkButton(
            self.main_frame,
            text="🚀 Verifikasi Klaim Secara Otonom",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.start_verification
        )
        self.verify_btn.grid(row=2, column=0, sticky="ew", pady=(0, 15))

        # Progress Bar & Status Text
        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Menunggu instruksi...", text_color="gray")
        self.status_label.grid(row=3, column=0, sticky="w", pady=(0, 5))

        self.progressbar = ctk.CTkProgressBar(self.main_frame)
        self.progressbar.grid(row=4, column=0, sticky="ew", pady=(0, 15))
        self.progressbar.set(0)

        # Bagian Putusan Akhir (Verdict Box)
        self.verdict_frame = ctk.CTkFrame(self.main_frame, corner_radius=8, fg_color="#1e293b")
        self.verdict_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15), padx=2)
        self.verdict_frame.grid_columnconfigure(0, weight=1)

        self.verdict_badge = ctk.CTkLabel(
            self.verdict_frame,
            text="STATUS: BELUM ADA PUTUSAN",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#94a3b8"
        )
        self.verdict_badge.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.verdict_rationale = ctk.CTkLabel(
            self.verdict_frame,
            text="Hasil analisis dan ringkasan fakta akan ditampilkan di sini...",
            wraplength=750,
            justify="left",
            font=ctk.CTkFont(size=12)
        )
        self.verdict_rationale.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="w")

        # Jejak Penalaran (Reasoning Chain Box)
        self.chain_label = ctk.CTkLabel(
            self.main_frame,
            text="Jejak Penalaran Sistem (Reasoning Chain / ReAct Trace):",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.chain_label.grid(row=6, column=0, sticky="w", pady=(5, 5))

        self.chain_textbox = ctk.CTkTextbox(self.main_frame, height=180, font=ctk.CTkFont(family="Courier", size=12))
        self.chain_textbox.grid(row=7, column=0, sticky="ew", pady=(0, 15))

        # Bukti Pendukung (Evidence Cards)
        self.evidence_label = ctk.CTkLabel(
            self.main_frame,
            text="Bukti & Sumber Rujukan Terverifikasi:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.evidence_label.grid(row=8, column=0, sticky="w", pady=(5, 5))

        self.evidence_textbox = ctk.CTkTextbox(self.main_frame, height=140, font=ctk.CTkFont(size=12))
        self.evidence_textbox.grid(row=9, column=0, sticky="ew", pady=(0, 10))

    def _update_tau(self, value):
        self.tau_label.configure(text=f"Confidence Threshold (𝜏): {value:.2f}")

    def _update_iter(self, value):
        self.iter_label.configure(text=f"Batas Iterasi (N): {int(value)}")

    def start_verification(self):
        claim = self.claim_input.get("0.0", "end").strip()
        if not claim:
            return

        self.verify_btn.configure(state="disabled")
        self.status_label.configure(text="Status: Menginisialisasi ReAct Agent...")
        self.progressbar.set(0.1)
        self.chain_textbox.delete("0.0", "end")
        self.evidence_textbox.delete("0.0", "end")
        self.verdict_badge.configure(text="STATUS: SEDANG MEMERIKSA...", text_color="#38bdf8")

        # Jalankan loop async di thread terpisah agar UI responsif
        threading.Thread(target=self._run_async_worker, args=(claim,), daemon=True).start()

    def _run_async_worker(self, claim):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._verify_task(claim))

    async def _verify_task(self, claim):
        tau = self.tau_slider.get()
        n = int(self.iter_slider.get())

        async for event in react_agent.verify_stream(claim, max_iterations=n, tau=tau):
            ev_type = event["event"]
            data = event["data"]

            if ev_type == "status":
                self.after(0, lambda m=data.get("message", ""): self.status_label.configure(text=f"Status: {m}"))
            elif ev_type == "decomposition":
                sub_qs = "\n".join(f"  • {q}" for q in data.get("sub_questions", []))
                msg = f"[DEKOMPOSISI KLAIM]:\n{sub_qs}\n\n"
                self.after(0, lambda m=msg: self._append_chain(m))
            elif ev_type == "thought":
                it = data.get("iteration")
                th = data.get("thought")
                act = data.get("action")
                act_in = data.get("action_input")
                msg = f"[ITERASI {it}] - THOUGHT:\n{th}\nACTION: {act} -> {act_in}\n"
                self.after(0, lambda m=msg: self._append_chain(m))
            elif ev_type == "observation":
                obs = data.get("observation")
                msg = f"OBSERVATION: {obs}\n\n"
                self.after(0, lambda m=msg: self._append_chain(m))
            elif ev_type == "assessment":
                conf = data.get("confidence", 0)
                reason = data.get("assessment_reason", "")
                self.after(0, lambda c=conf: self.progressbar.set(min(1.0, c)))
                msg = f"CONFIDENCE ASSESSMENT: {conf:.2f} (Alasan: {reason})\n" + "-"*50 + "\n"
                self.after(0, lambda m=msg: self._append_chain(m))
            elif ev_type == "final":
                self.after(0, lambda res=data: self._display_final(res))

    def _append_chain(self, text):
        self.chain_textbox.insert("end", text)
        self.chain_textbox.see("end")

    def _display_final(self, res):
        status = res.get("status", "Not Enough Information")
        conf = res.get("confidence", 0.0)
        rationale = res.get("rationale", "")
        evidence_list = res.get("evidence", [])

        # Color coding status
        if status == "Didukung":
            color = "#22c55e" # Hijau
            badge_text = f"✅ DIDUKUNG (FAKTA TERKONFIRMASI) | Keyakinan: {conf:.0%}"
        elif status == "Ditolak":
            color = "#ef4444" # Merah
            badge_text = f"❌ DITOLAK (HOAKS / KELIRU) | Keyakinan: {conf:.0%}"
        else:
            color = "#eab308" # Kuning
            badge_text = f"⚠️ NOT ENOUGH INFORMATION | Keyakinan: {conf:.0%}"

        self.verdict_badge.configure(text=badge_text, text_color=color)
        self.verdict_rationale.configure(text=rationale)

        # Tampilkan list bukti
        for i, ev in enumerate(evidence_list):
            snippet = f"[{i+1}] {ev.get('title', 'Sumber')}\n" \
                      f"    URL: {ev.get('url', '-')}\n" \
                      f"    Relevansi: {ev.get('relevance_score', 0):.2f}\n" \
                      f"    Kutipan: {ev.get('snippet', '')[:200]}...\n\n"
            self.evidence_textbox.insert("end", snippet)

        self.status_label.configure(text="Status: Selesai memverifikasi.")
        self.verify_btn.configure(state="normal")
        self.progressbar.set(1.0)

if __name__ == "__main__":
    app = AntiHoaxApp()
    app.mainloop()
