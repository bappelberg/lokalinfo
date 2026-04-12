import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import Providers from "@/components/Providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LokalInfo – Vad händer nära dig just nu",
  description:
    "Upptäck och dela vad som händer i ditt område i realtid. Se trafik, händelser, tips och mer direkt på kartan.",
  keywords: [
    "lokala nyheter",
    "realtid karta",
    "trafik",
    "händelser",
    "community",
    "Sverige",
    "lokal info",
  ],
  authors: [{ name: "LokalInfo" }],
  creator: "LokalInfo",
  openGraph: {
    title: "LokalInfo – Livekarta över lokala händelser",
    description:
      "Se vad som händer nära dig – live. Dela egna händelser och följ vad andra rapporterar i ditt område.",
    url: "https://lokalinfo.vercel.app/",
    siteName: "LokalInfo",
    locale: "sv_SE",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LokalInfo – Vad händer nära dig?",
    description:
      "Följ lokala händelser i realtid på en interaktiv karta.",
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    other: [
      {
        rel: "android-chrome-192x192",
        url: "/android-chrome-192x192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        rel: "android-chrome-512x512",
        url: "/android-chrome-512x512.png",
        sizes: "512x512",
        type: "image/png",
      },
    ],
  },
  // manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="sv"  // Ändrade från "en" till "sv" eftersom sidan är på svenska
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased flex flex-col`}
    >
      <body className="flex-1 flex flex-col">
        <Providers>
          <Navbar />
          {children}
        </Providers>
      </body>
    </html>
  );
}