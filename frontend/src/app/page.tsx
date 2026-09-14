"use client";

import React, { useState, useRef } from "react";
import { 
  ShieldCheck, AlertTriangle, XCircle, Search, Cpu, RefreshCw, 
  ExternalLink, ChevronRight, CheckCircle2, Sparkles, Sliders, Database,
  ArrowRight, BookOpen, Layers
} from "lucide-react";

interface Evidence {
  id?: string;
  title: string;
  url: string;
  snippet: string;
  source_type: string;
  relevance_score?: number;
}

interface ThoughtStep {
  iteration: number;
  thought: string;
  action: string;
  action_input?: string;
  observation?: string;
  confidence: number;
}

interface VerificationResult {
  claim: string;
  status: "Didukung" | "Ditolak" | "Not Enough Information";
  confidence: number;
  sub_questions: string[];
  reasoning_chain: ThoughtStep[];
  evidence: Evidence[];
  rationale: string;
  iterations_used: number;
}

const SAMPLE_CLAIMS = [
  {
    label: "Hoaks Bantuan Medsos",
    text: "Pemerintah bagikan bantuan uang tunai 5 juta rupiah lewat tautan WhatsApp dengan mengisi nomor rekening."
  },
  {
    label: "Fakta Kominfo 2024",
    text: "Kementerian Komunikasi dan Digital mengidentifikasi ribuan konten hoaks sepanjang tahun 2024."
  },
  {
    label: "Hoaks Kesehatan Serai",
    text: "Minum air rebusan daun serai dapat menyembuhkan diabetes stadium empat secara instan dalam 3 hari."
  },
  {
    label: "Klaim Ambigu / Minim Bukti",
    text: "Seseorang di desa terpencil mengaku melihat penampakan cahaya aneh tanpa ada rekaman dan saksi."
  }
];

export default function Home() {
  const [claim, setClaim] = useState("");
  const [tau, setTau] = useState(0.85);
  const [maxIterations, setMaxIterations] = useState(5);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  
  // Real-time states
  const [subQuestions, setSubQuestions] = useState<string[]>([]);
  const [steps, setSteps] = useState<ThoughtStep[]>([]);
  const [currentThought, setCurrentThought] = useState<any>(null);
  const [finalResult, setFinalResult] = useState<VerificationResult | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleStartVerification = async () => {
    if (!claim.trim()) return;

    setLoading(true);
    setStatusMsg("Menginisialisasi ReAct Agent...");
    setSubQuestions([]);
    setSteps([]);
    setCurrentThought(null);
    setFinalResult(null);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const apiUrl = `/api/verify/stream?claim=${encodeURIComponent(claim)}&tau=${tau}&max_iterations=${maxIterations}`;
    const es = new EventSource(apiUrl);
    eventSourceRef.current = es;

    es.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      setStatusMsg(data.message || "");
    });

    es.addEventListener("decomposition", (e) => {
      const data = JSON.parse(e.data);
      setSubQuestions(data.sub_questions || []);
    });

    es.addEventListener("thought", (e) => {
      const data = JSON.parse(e.data);
      setCurrentThought(data);
    });

    es.addEventListener("observation", (e) => {
      const data = JSON.parse(e.data);
      setCurrentThought((prev: any) => prev ? { ...prev, observation: data.observation } : null);
    });

    es.addEventListener("assessment", (e) => {
      const data = JSON.parse(e.data);
      const newStep: ThoughtStep = {
        iteration: data.iteration,
        thought: currentThought?.thought || "",
        action: currentThought?.action || "SEARCH",
        action_input: currentThought?.action_input || "",
        observation: currentThought?.observation || "",
        confidence: data.confidence || 0,
      };
      setSteps((prev) => [...prev, newStep]);
      setCurrentThought(null);
    });

    es.addEventListener("final", (e) => {
      const data = JSON.parse(e.data);
      setFinalResult(data);
      setLoading(false);
      setStatusMsg("Selesai memverifikasi.");
      es.close();
    });

    es.onerror = (err) => {
      console.error("SSE Connection error:", err);
      // Fallback: jika SSE error, coba POST langsung
      handleFallbackPost();
      es.close();
    };
  };

  const handleFallbackPost = async () => {
    setStatusMsg("Beralih ke verifikasi sinkronus...");
    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim,
          confidence_threshold: tau,
          max_iterations: maxIterations,
        })
      });
      if (res.ok) {
        const data = await res.json();
        setFinalResult(data);
        setSubQuestions(data.sub_questions || []);
        setSteps(data.reasoning_chain || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setStatusMsg("Selesai.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight text-white">Anti-Hoax AI</span>
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Agentic ReAct + RAG
                </span>
              </div>
              <p className="text-xs text-slate-400">Verifikasi Fakta Otonom Multi-Langkah Berbahasa Indonesia</p>
            </div>
          </div>
          <div className="hidden sm:flex items-center space-x-4 text-xs text-slate-400">
            <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-emerald-400" /> GPT-4o / Gemini</span>
            <span className="flex items-center gap-1.5"><Database className="w-3.5 h-3.5 text-blue-400" /> ChromaDB + Live Web</span>
            <span className="flex items-center gap-1.5"><BookOpen className="w-3.5 h-3.5 text-purple-400" /> Jurnal Khatulistiwa 2026</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left / Input Column (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
              
              <h2 className="text-base font-semibold text-white flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-emerald-400" /> Masukkan Klaim Informasi
              </h2>
              
              <textarea
                value={claim}
                onChange={(e) => setClaim(e.target.value)}
                placeholder="Tulis atau tempel klaim berita, pesan WhatsApp viral, atau postingan media sosial yang ingin diverifikasi kebenarannya..."
                rows={4}
                className="w-full bg-slate-950/70 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition resize-none"
              />

              {/* Sample Claims Pills */}
              <div className="mt-3">
                <p className="text-xs text-slate-400 mb-2">Contoh Klaim Pengujian:</p>
                <div className="flex flex-wrap gap-1.5">
                  {SAMPLE_CLAIMS.map((sample, idx) => (
                    <button
                      key={idx}
                      onClick={() => setClaim(sample.text)}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 transition border border-slate-700/50 flex items-center gap-1"
                    >
                      <span>{sample.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Parameters Controls */}
              <div className="mt-6 pt-5 border-t border-slate-800/80 space-y-4">
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="flex items-center gap-1 font-medium">
                    <Sliders className="w-3.5 h-3.5 text-emerald-400" /> Ambang Keyakinan (𝜏):
                  </span>
                  <span className="font-mono bg-slate-800 px-2 py-0.5 rounded text-emerald-400 font-bold">
                    {tau.toFixed(2)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="0.95"
                  step="0.05"
                  value={tau}
                  onChange={(e) => setTau(parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />

                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span className="flex items-center gap-1 font-medium">
                    <Layers className="w-3.5 h-3.5 text-blue-400" /> Batas Maksimum Siklus ReAct (N):
                  </span>
                  <span className="font-mono bg-slate-800 px-2 py-0.5 rounded text-blue-400 font-bold">
                    {maxIterations} siklus
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="10"
                  step="1"
                  value={maxIterations}
                  onChange={(e) => setMaxIterations(parseInt(e.target.value))}
                  className="w-full accent-blue-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
              </div>

              {/* Start Button */}
              <button
                onClick={handleStartVerification}
                disabled={loading || !claim.trim()}
                className="mt-6 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/30 transition transform active:scale-[0.99]"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Agen Sedang Menelusuri Bukti...</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    <span>Verifikasi Klaim Sekarang</span>
                  </>
                )}
              </button>

              {statusMsg && (
                <div className="mt-3 text-center text-xs text-emerald-400/90 animate-pulse font-mono">
                  {statusMsg}
                </div>
              )}
            </div>

            {/* Paper Reference Card */}
            <div className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 text-xs text-slate-400 space-y-2">
              <div className="font-medium text-slate-300 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4 text-slate-400" /> Landasan Teori Algoritma
              </div>
              <p className="leading-relaxed">
                Sistem ini merealisasikan arsitektur agen otonom ReAct (Reasoning and Acting) yang dipadukan dengan Retrieval-Augmented Generation (RAG), ChromaDB, dan web retrieval dinamis sesuai publikasi Adwiya et al. (2026).
              </p>
            </div>
          </div>

          {/* Right / Results Column (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Final Verdict Box */}
            {finalResult && (
              <div className={`border rounded-2xl p-6 shadow-2xl relative overflow-hidden backdrop-blur-xl ${
                finalResult.status === "Didukung" 
                  ? "bg-emerald-950/40 border-emerald-500/40 shadow-emerald-950/20" 
                  : finalResult.status === "Ditolak"
                  ? "bg-red-950/40 border-red-500/40 shadow-red-950/20"
                  : "bg-amber-950/40 border-amber-500/40 shadow-amber-950/20"
              }`}>
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Putusan Verifikasi AI:</span>
                    <div className="flex items-center gap-3 mt-1">
                      {finalResult.status === "Didukung" && (
                        <div className="flex items-center gap-2 text-emerald-400 text-2xl font-black">
                          <CheckCircle2 className="w-7 h-7" /> DIDUKUNG (FAKTA)
                        </div>
                      )}
                      {finalResult.status === "Ditolak" && (
                        <div className="flex items-center gap-2 text-red-400 text-2xl font-black">
                          <XCircle className="w-7 h-7" /> DITOLAK (HOAKS)
                        </div>
                      )}
                      {finalResult.status === "Not Enough Information" && (
                        <div className="flex items-center gap-2 text-amber-400 text-2xl font-black">
                          <AlertTriangle className="w-7 h-7" /> BUKTI BELUM CUKUP (NEI)
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[11px] text-slate-400 block">Confidence Score</span>
                    <span className="text-2xl font-bold font-mono text-white">
                      {(finalResult.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-800/80">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">Penjelasan & Alasan Putusan:</h4>
                  <p className="text-sm text-slate-200 leading-relaxed">
                    {finalResult.rationale}
                  </p>
                </div>

                <div className="mt-3 flex items-center gap-4 text-xs text-slate-400">
                  <span>Iterasi ReAct: <strong>{finalResult.iterations_used}</strong> siklus</span>
                  <span>•</span>
                  <span>Bukti Ditemukan: <strong>{finalResult.evidence.length}</strong> sumber</span>
                </div>
              </div>
            )}

            {/* Claim Decomposition */}
            {subQuestions.length > 0 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5 mb-3">
                  <ChevronRight className="w-4 h-4" /> Dekomposisi Semantik Klaim ({subQuestions.length} Sub-Pertanyaan):
                </h3>
                <div className="space-y-2">
                  {subQuestions.map((q, i) => (
                    <div key={i} className="flex items-start gap-2.5 text-xs text-slate-300 bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/60">
                      <span className="w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-400 font-bold flex items-center justify-center flex-shrink-0 text-[10px]">
                        {i + 1}
                      </span>
                      <span className="leading-snug">{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Live Reasoning Chain (ReAct Trace) */}
            {(steps.length > 0 || currentThought) && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-blue-400" /> Jejak Penalaran ReAct (Reasoning Chain)
                  </h3>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {steps.length} langkah terselesaikan
                  </span>
                </div>

                <div className="space-y-3">
                  {steps.map((step, idx) => (
                    <div key={idx} className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 text-xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-blue-400 uppercase text-[11px]">
                          Siklus #{step.iteration}
                        </span>
                        <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-[10px] font-mono">
                          Keyakinan: {(step.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div>
                        <span className="font-semibold text-slate-400 block mb-0.5">🧠 Penalaran (Thought):</span>
                        <p className="text-slate-200 leading-relaxed">{step.thought}</p>
                      </div>

                      <div className="bg-slate-900/90 p-2.5 rounded-lg border border-slate-800/60 flex items-center justify-between">
                        <span className="text-slate-400">Tindakan (Action): <strong className="text-emerald-400">{step.action}</strong></span>
                        {step.action_input && (
                          <span className="text-slate-300 font-mono text-[11px]">"{step.action_input}"</span>
                        )}
                      </div>

                      {step.observation && (
                        <div className="text-slate-400 bg-slate-900/40 p-2.5 rounded-lg">
                          <span className="font-semibold text-slate-300 block mb-0.5">🔍 Observasi Bukti (Observation):</span>
                          <p>{step.observation}</p>
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Ongoing live thought */}
                  {currentThought && (
                    <div className="bg-blue-950/20 border border-blue-500/30 rounded-xl p-4 text-xs space-y-2 animate-pulse">
                      <div className="flex items-center gap-2 text-blue-400 font-semibold">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Sedang Menalar Siklus #{currentThought.iteration}...
                      </div>
                      <p className="text-slate-300">{currentThought.thought}</p>
                      {currentThought.action && (
                        <p className="text-xs text-slate-400">Action: <span className="text-emerald-400 font-mono">{currentThought.action}</span> ({currentThought.action_input})</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Evidence & References */}
            {finalResult && finalResult.evidence.length > 0 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-lg">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-white flex items-center gap-1.5 mb-4">
                  <Database className="w-4 h-4 text-emerald-400" /> Sumber Bukti Rujukan Terverifikasi ({finalResult.evidence.length})
                </h3>
                
                <div className="space-y-3">
                  {finalResult.evidence.map((ev, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-bold text-slate-200 line-clamp-1">{ev.title}</h4>
                        {ev.url && ev.url !== "-" && (
                          <a
                            href={ev.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1 text-[11px] flex-shrink-0"
                          >
                            <span>Buka Sumber</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                        {ev.snippet}
                      </p>
                      <div className="flex items-center gap-3 text-[10px] text-slate-500 font-mono pt-1">
                        <span>Tipe: {ev.source_type}</span>
                        {ev.relevance_score !== undefined && (
                          <span>Relevansi: {(ev.relevance_score * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!loading && !finalResult && (
              <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center text-slate-500">
                <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <h3 className="text-sm font-medium text-slate-400 mb-1">Menunggu Klaim untuk Diverifikasi</h3>
                <p className="text-xs max-w-sm mx-auto">
                  Tulis klaim atau pilih salah satu contoh di sebelah kiri, lalu tekan tombol "Verifikasi Klaim Sekarang" untuk memulai siklus ReAct.
                </p>
              </div>
            )}

          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-600">
        Anti-Hoax Autonomous Agent System • Mengadaptasi Kerangka Kerja ReAct & RAG • Jurnal Khatulistiwa Informatika 2026
      </footer>
    </div>
  );
}
