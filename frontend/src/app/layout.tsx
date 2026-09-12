import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

// Fonts are loaded via a runtime <link> rather than next/font/google: that
// keeps `next build` fully offline-capable (no build-time fetch to Google's
// font CDN required), which matters for restricted build environments and
// for this project's own CI/sandbox. See CLAUDE.md.
export const metadata: Metadata = {
  title: "MetraCheck — Legal Metrology Compliance",
  description:
    "AI-assisted compliance screening and evidence management for Legal Metrology inspections.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@500;600;700&family=Source+Sans+3:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
