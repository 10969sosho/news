import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DIGITAL WATCH (WEB ANALYZE TRUTH AND CHECKING HUB)",
  description: "Autonomous Agentic Fact-Checking and Truth Analysis Platform",
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
