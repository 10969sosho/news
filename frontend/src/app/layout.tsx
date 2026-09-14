import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anti-Hoax AI | Sistem Deteksi Hoaks Berbasis Agentic AI Otonom",
  description: "Implementasi ReAct (Reason and Act) + RAG Fact-Checking Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className="antialiased selection:bg-emerald-500 selection:text-white bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}
