"use client";

import React, { useState, useRef } from "react";
import { 
  ShieldCheck, AlertTriangle, XCircle, Search, Cpu, RefreshCw, 
  ExternalLink, ChevronRight, CheckCircle2, Sparkles, Database,
  BookOpen, Languages, ShieldAlert, CheckCircle, Info, Activity
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
  thought_en?: string;
  action: string;
  action_input?: string;
  observation?: string;
  confidence: number;
}

interface VerificationResult {
  claim: string;
  truth_score: number;
  tier: "Hoax" | "Rendah" | "Sedang" | "Tinggi";
  tier_label: string;
  tier_label_en: string;
  sub_questions: string[];
  sub_questions_en: string[];
  reasoning_chain: ThoughtStep[];
  evidence: Evidence[];
  rationale: string;
  rationale_en: string;
  iterations_used: number;
  detected_language: string;
}

const SAMPLES = {
  id: [
    { label: "Hoaks Bantuan WhatsApp", text: "Pemerintah bagikan bantuan uang tunai lewat tautan WhatsApp mengatasnamakan Presiden dengan mengisi nomor rekening." },
    { label: "Hoaks Uang 1 Juta", text: "Bank Indonesia menerbitkan uang pecahan 1.000.000 rupiah bergambar Presiden Jokowi yang sah untuk belanja." },
    { label: "Fakta Program Resmi", text: "Kementerian Komunikasi dan Digital mengidentifikasi ribuan konten hoaks sepanjang tahun 2024." },
    { label: "Klaim Minim Fakta", text: "Seseorang di desa terpencil mengaku melihat penampakan cahaya aneh tanpa bukti dan saksi mata." },
  ],
  en: [
    { label: "WhatsApp Cash Scam", text: "Government gives away $5,000 cash aid through WhatsApp link asking for bank account details." },
    { label: "NASA UFO Claim", text: "NASA officially confirmed an alien spacecraft landed in the middle of New York City yesterday." },
    { label: "Official Tech Program", text: "Indonesia Ministry of Communication launches Digital Talent Scholarship for technological skills training." },
  ]
};

export default function Home() {
  const [uiLang, setUiLang] = useState<"id" | "en">("id");
  const [displayLang, setDisplayLang] = useState<"id" | "en">("id");
  const [claim, setClaim] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  
  // Real-time states
  const [subQuestions, setSubQuestions] = useState<string[]>([]);
  const [subQuestionsEn, setSubQuestionsEn] = useState<string[]>([]);
  const [steps, setSteps] = useState<ThoughtStep[]>([]);
  const [currentThought, setCurrentThought] = useState<any>(null);
  const [finalResult, setFinalResult] = useState<VerificationResult | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

  const handleStartVerification = async () => {
    if (!claim.trim()) return;

    setLoading(true);
    setStatusMsg(uiLang === "id" ? "Menginisialisasi Agen Verifikasi..." : "Initializing Fact-Checking Agent...");
    setSubQuestions([]);
    setSubQuestionsEn([]);
    setSteps([]);
    setCurrentThought(null);
    setFinalResult(null);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const apiUrl = `/api/verify/stream?claim=${encodeURIComponent(claim)}&max_iterations=3&lang=${uiLang}`;
    const es = new EventSource(apiUrl);
    eventSourceRef.current = es;

    es.addEventListener("status", (e) => {
      const data = JSON.parse(e.data);
      setStatusMsg(data.message || "");
    });

    es.addEventListener("decomposition", (e) => {
      const data = JSON.parse(e.data);
      setSubQuestions(data.sub_questions || []);
      setSubQuestionsEn(data.sub_questions_en || []);
    });

    es.addEventListener("thought", (e) => {
      const data = JSON.parse(e.data);
      setCurrentThought(data);
    });

    es.addEventListener("observation", (e) => {
      const data = JSON.parse(e.data);
      setCurrentThought((prev: any) => prev ? { ...prev, observation: data.observation } : null);
    });

    es.addEventListener("final", (e) => {
      const data = JSON.parse(e.data);
      setFinalResult(data);
      setLoading(false);
      setStatusMsg(uiLang === "id" ? "Analisis selesai." : "Analysis completed.");
      es.close();
    });

    es.onerror = () => {
      handleFallbackPost();
      es.close();
    };
  };

  const handleFallbackPost = async () => {
    setStatusMsg(uiLang === "id" ? "Memproses analisis..." : "Processing analysis...");
    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          claim,
          max_iterations: 3,
          target_language: uiLang
        })
      });
      if (res.ok) {
        const data = await res.json();
        setFinalResult(data);
        setSubQuestions(data.sub_questions || []);
        setSubQuestionsEn(data.sub_questions_en || []);
        setSteps(data.reasoning_chain || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setStatusMsg("");
    }
  };

  const getTierInfo = (score: number) => {
    if (score < 60) {
      return {
        name: "Hoax",
        labelId: "HOAX (Palsu / Disinformasi)",
        labelEn: "HOAX (Fabricated / False)",
        color: "text-red-400",
        bgColor: "bg-red-500/10 border-red-500/30",
        badgeBg: "bg-red-600 text-white",
        barColor: "bg-red-500",
        icon: <XCircle className="w-8 h-8 text-red-400" />
      };
    } else if (score <= 75) {
      return {
        name: "Rendah",
        labelId: "Tingkat Kebenaran Rendah",
        labelEn: "Low Truth / Questionable",
        color: "text-orange-400",
        bgColor: "bg-orange-500/10 border-orange-500/30",
        badgeBg: "bg-orange-600 text-white",
        barColor: "bg-orange-500",
        icon: <AlertTriangle className="w-8 h-8 text-orange-400" />
      };
    } else if (score <= 85) {
      return {
        name: "Sedang",
        labelId: "Tingkat Kebenaran Sedang",
        labelEn: "Moderate Truth / Partially True",
        color: "text-amber-400",
        bgColor: "bg-amber-500/10 border-amber-500/30",
        badgeBg: "bg-amber-600 text-white",
        barColor: "bg-amber-500",
        icon: <Info className="w-8 h-8 text-amber-400" />
      };
    } else {
      return {
        name: "Tinggi",
        labelId: "Tingkat Kebenaran Tinggi (Fakta)",
        labelEn: "High Truth (Verified Fact)",
        color: "text-emerald-400",
        bgColor: "bg-emerald-500/10 border-emerald-500/30",
        badgeBg: "bg-emerald-600 text-white",
        barColor: "bg-emerald-500",
        icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />
      };
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 border border-cyan-400/20">
              <ShieldAlert className="w-7 h-7 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-extrabold text-xl tracking-tight text-white">DIGITAL WATCH</h1>
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 tracking-wider">
                  AI FACT-CHECK HUB
                </span>
              </div>
              <p className="text-xs font-medium text-cyan-400/90 tracking-wide">
                WEB ANALYZE TRUTH AND CHECKING HUB
              </p>
            </div>
          </div>

          {/* Language Selector */}
          <div className="flex items-center gap-2 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800">
            <Languages className="w-4 h-4 text-slate-400 ml-1.5" />
            <button
              onClick={() => setUiLang("id")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                uiLang === "id" ? "bg-cyan-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              🇮🇩 ID
            </button>
            <button
              onClick={() => setUiLang("en")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                uiLang === "en" ? "bg-cyan-600 text-white shadow" : "text-slate-400 hover:text-white"
              }`}
            >
              🇬🇧 EN
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Input Form */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-2xl relative overflow-hidden backdrop-blur-xl">
              <div className="absolute top-0 right-0 w-40 h-40 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

              <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2 mb-3 uppercase tracking-wider">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                {uiLang === "id" ? "Masukkan Informasi / Isu Berita" : "Enter Information / News Claim"}
              </h2>

              <textarea
                value={claim}
                onChange={(e) => setClaim(e.target.value)}
                placeholder={
                  uiLang === "id"
                    ? "Tempel atau ketik klaim berita, postingan media sosial, atau pesan viral yang ingin Anda periksa kebenarannya..."
                    : "Paste or write the news claim, viral post, or statement you want to fact-check..."
                }
                rows={5}
                className="w-full bg-slate-950/80 border border-slate-800 rounded-2xl p-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition resize-none leading-relaxed"
              />

              {/* Sample Claims */}
              <div className="mt-4">
                <p className="text-[11px] font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                  {uiLang === "id" ? "Contoh Klaim Populer:" : "Sample Claims:"}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(uiLang === "id" ? SAMPLES.id : SAMPLES.en).map((item, idx) => (
                    <button
                      key={idx}
                      onClick={() => setClaim(item.text)}
                      className="text-[11px] px-3 py-1.5 rounded-xl bg-slate-800/60 hover:bg-slate-700/80 text-slate-300 transition border border-slate-700/40 text-left"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={handleStartVerification}
                disabled={loading || !claim.trim()}
                className="mt-6 w-full py-3.5 px-5 rounded-2xl bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed font-bold text-sm flex items-center justify-center gap-2 shadow-xl shadow-cyan-950/40 transition transform active:scale-[0.99] text-white"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>{uiLang === "id" ? "Agen Sedang Memeriksa Fakta..." : "Agent Is Fact-Checking..."}</span>
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    <span>{uiLang === "id" ? "Uji Kebenaran Klaim" : "Verify Claim Truth"}</span>
                  </>
                )}
              </button>

              {statusMsg && (
                <div className="mt-3 text-center text-xs text-cyan-400 font-mono animate-pulse">
                  {statusMsg}
                </div>
              )}
            </div>

            {/* Criteria Info Card */}
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-3xl p-5 text-xs text-slate-400 space-y-3">
              <div className="font-bold text-slate-300 flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                {uiLang === "id" ? "Skala Rating Kebenaran (Truth Score):" : "Truth Score Rating Scale:"}
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">
                  <span className="font-bold block">&lt; 60%</span>
                  <span>Hoax / Palsu</span>
                </div>
                <div className="p-2.5 rounded-xl bg-orange-500/10 border border-orange-500/20 text-orange-300">
                  <span className="font-bold block">61% - 75%</span>
                  <span>{uiLang === "id" ? "Kebenaran Rendah" : "Low Truth"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300">
                  <span className="font-bold block">76% - 85%</span>
                  <span>{uiLang === "id" ? "Kebenaran Sedang" : "Moderate Truth"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                  <span className="font-bold block">86% - 100%</span>
                  <span>{uiLang === "id" ? "Kebenaran Tinggi" : "High Truth (Fact)"}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Analysis Results */}
          <div className="lg:col-span-7 space-y-6">
            
            {/* Final Verdict Card */}
            {finalResult && (() => {
              const tierInfo = getTierInfo(finalResult.truth_score);
              return (
                <div className={`border rounded-3xl p-6 shadow-2xl relative overflow-hidden backdrop-blur-xl ${tierInfo.bgColor}`}>
                  
                  {/* Header Tier */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3.5">
                      {tierInfo.icon}
                      <div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                          {uiLang === "id" ? "Hasil Analisis Kebenaran:" : "Truth Assessment Result:"}
                        </span>
                        <h3 className={`text-2xl font-black tracking-tight ${tierInfo.color}`}>
                          {uiLang === "id" ? tierInfo.labelId : tierInfo.labelEn}
                        </h3>
                      </div>
                    </div>

                    {/* Percentage Score Meter */}
                    <div className="bg-slate-950/80 border border-slate-800/80 px-4 py-2.5 rounded-2xl text-center sm:text-right flex-shrink-0">
                      <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                        TRUTH SCORE
                      </span>
                      <span className="text-3xl font-black font-mono text-white">
                        {finalResult.truth_score.toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Visual Progress Bar Scale */}
                  <div className="mt-5 space-y-1.5">
                    <div className="h-3 w-full bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
                      <div 
                        className={`h-full rounded-full transition-all duration-1000 ${tierInfo.barColor}`}
                        style={{ width: `${Math.max(5, Math.min(100, finalResult.truth_score))}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-500 font-mono px-1">
                      <span>0% (Hoax)</span>
                      <span>60%</span>
                      <span>75%</span>
                      <span>85%</span>
                      <span>100% (Fakta)</span>
                    </div>
                  </div>

                  {/* Dual Language Explanation Toggle */}
                  <div className="mt-6 pt-5 border-t border-slate-800/80">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                        {uiLang === "id" ? "Uraian & Rujukan Fakta:" : "Fact-Checking Explanation:"}
                      </h4>
                      <div className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-lg border border-slate-800">
                        <button
                          onClick={() => setDisplayLang("id")}
                          className={`text-[10px] px-2 py-0.5 rounded font-bold transition ${
                            displayLang === "id" ? "bg-slate-800 text-cyan-300" : "text-slate-400"
                          }`}
                        >
                          🇮🇩 ID
                        </button>
                        <button
                          onClick={() => setDisplayLang("en")}
                          className={`text-[10px] px-2 py-0.5 rounded font-bold transition ${
                            displayLang === "en" ? "bg-slate-800 text-cyan-300" : "text-slate-400"
                          }`}
                        >
                          🇬🇧 EN
                        </button>
                      </div>
                    </div>

                    <p className="text-sm text-slate-200 leading-relaxed font-normal bg-slate-950/40 p-4 rounded-2xl border border-slate-800/60">
                      {displayLang === "id" ? finalResult.rationale : finalResult.rationale_en}
                    </p>
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span>Iterasi ReAct: <strong>{finalResult.iterations_used}</strong></span>
                    <span>•</span>
                    <span>Bukti Rujukan: <strong>{finalResult.evidence.length}</strong></span>
                  </div>
                </div>
              );
            })()}

            {/* Semantic Claim Decomposition */}
            {(subQuestions.length > 0 || subQuestionsEn.length > 0) && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-lg">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-2 mb-3">
                  <ChevronRight className="w-4 h-4" /> 
                  {uiLang === "id" ? "Dekomposisi Semantik Sub-Pertanyaan:" : "Semantic Sub-Questions Breakdown:"}
                </h3>
                <div className="space-y-2">
                  {(displayLang === "id" ? subQuestions : subQuestionsEn).map((q, i) => (
                    <div key={i} className="flex items-start gap-3 text-xs text-slate-300 bg-slate-950/60 p-3 rounded-2xl border border-slate-800/60">
                      <span className="w-5 h-5 rounded-full bg-cyan-500/10 text-cyan-400 font-bold flex items-center justify-center flex-shrink-0 text-[10px]">
                        {i + 1}
                      </span>
                      <span className="leading-relaxed">{q}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Live ReAct Reasoning Steps */}
            {(steps.length > 0 || currentThought) && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-lg space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-cyan-400" />
                    {uiLang === "id" ? "Jejak Penalaran ReAct (Reasoning Chain)" : "ReAct Reasoning Chain Trace"}
                  </h3>
                </div>

                <div className="space-y-3">
                  {steps.map((step, idx) => (
                    <div key={idx} className="bg-slate-950/80 border border-slate-800/80 rounded-2xl p-4 text-xs space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-cyan-400 uppercase text-[11px]">
                          {uiLang === "id" ? `Siklus #${step.iteration}` : `Cycle #${step.iteration}`}
                        </span>
                      </div>

                      <div>
                        <span className="font-semibold text-slate-400 block mb-0.5">🧠 {uiLang === "id" ? "Penalaran:" : "Reasoning:"}</span>
                        <p className="text-slate-200 leading-relaxed">
                          {displayLang === "id" ? step.thought : (step.thought_en || step.thought)}
                        </p>
                      </div>

                      <div className="bg-slate-900/90 p-2.5 rounded-xl border border-slate-800/60 flex items-center justify-between">
                        <span className="text-slate-400">{uiLang === "id" ? "Tindakan:" : "Action:"} <strong className="text-cyan-400">{step.action}</strong></span>
                        {step.action_input && (
                          <span className="text-slate-300 font-mono text-[11px]">"{step.action_input}"</span>
                        )}
                      </div>

                      {step.observation && (
                        <div className="text-slate-400 bg-slate-900/40 p-2.5 rounded-xl">
                          <span className="font-semibold text-slate-300 block mb-0.5">🔍 {uiLang === "id" ? "Observasi Bukti:" : "Evidence Observation:"}</span>
                          <p>{step.observation}</p>
                        </div>
                      )}
                    </div>
                  ))}

                  {currentThought && (
                    <div className="bg-cyan-950/20 border border-cyan-500/30 rounded-2xl p-4 text-xs space-y-2 animate-pulse">
                      <div className="flex items-center gap-2 text-cyan-400 font-semibold">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> 
                        {uiLang === "id" ? `Sedang Menalar Siklus #${currentThought.iteration}...` : `Reasoning Cycle #${currentThought.iteration}...`}
                      </div>
                      <p className="text-slate-300">
                        {displayLang === "id" ? currentThought.thought : (currentThought.thought_en || currentThought.thought)}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Evidence References */}
            {finalResult && finalResult.evidence.length > 0 && (
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 shadow-lg">
                <h3 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2 mb-4">
                  <Database className="w-4 h-4 text-cyan-400" />
                  {uiLang === "id" ? `Sumber & Bukti Klarifikasi (${finalResult.evidence.length})` : `Verified Evidence Sources (${finalResult.evidence.length})`}
                </h3>
                
                <div className="space-y-3">
                  {finalResult.evidence.map((ev, i) => (
                    <div key={i} className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 hover:border-cyan-500/40 transition space-y-1.5">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-xs font-bold text-slate-200 line-clamp-1">{ev.title}</h4>
                        {ev.url && ev.url !== "-" && (
                          <a
                            href={ev.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[11px] flex-shrink-0"
                          >
                            <span>{uiLang === "id" ? "Buka Sumber" : "View Source"}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                        {ev.snippet}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Initial Empty State */}
            {!loading && !finalResult && (
              <div className="border border-dashed border-slate-800/80 rounded-3xl p-12 text-center text-slate-500">
                <Search className="w-12 h-12 mx-auto mb-3 opacity-30 text-cyan-400" />
                <h3 className="text-sm font-semibold text-slate-300 mb-1">
                  {uiLang === "id" ? "Siap Memeriksa Fakta" : "Ready to Fact-Check"}
                </h3>
                <p className="text-xs max-w-md mx-auto text-slate-500 leading-relaxed">
                  {uiLang === "id" 
                    ? "Ketik klaim Anda atau pilih salah satu contoh di panel kiri, lalu tekan tombol 'Uji Kebenaran Klaim' untuk memulai penalaran otonom."
                    : "Type your claim or select one of the samples on the left, then click 'Verify Claim Truth' to initiate autonomous reasoning."}
                </p>
              </div>
            )}

          </div>

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-5 text-center text-xs text-slate-500">
        <p className="font-semibold text-slate-400">DIGITAL WATCH (WEB ANALYZE TRUTH AND CHECKING HUB)</p>
        <p className="text-[11px] text-slate-600 mt-0.5">Autonomous ReAct Fact-Checking & Knowledge Retrieval Engine</p>
      </footer>
    </div>
  );
}
