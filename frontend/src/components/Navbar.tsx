"use client";

import Link from "next/link";
import { useState } from "react";

const links = [
  { href: "/", label: "Karta" },
  { href: "/about", label: "Om oss" },
  { href: "/register", label: "Registrera" },
  { href: "/login", label: "Logga in" },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="bg-blue-50 border-b border-blue-200 shadow-sm z-50">
      <div className="flex items-center justify-between px-4 py-2">
        <Link href="/" className="text-lg font-semibold text-blue-900 tracking-tight">
          LokalInfo
        </Link>

        {/* Desktop */}
        <div className="hidden sm:flex items-center gap-4 text-sm text-blue-700">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hover:text-blue-900 hover:bg-blue-100 px-2 py-1 rounded-md transition-colors"
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* Hamburger */}
        <button
          className="sm:hidden p-2 rounded-md text-blue-700 hover:bg-blue-100 transition-colors"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Stäng meny" : "Öppna meny"}
        >
          {open ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="sm:hidden border-t border-blue-200 px-4 py-2 flex flex-col gap-1 text-sm text-blue-700">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hover:text-blue-900 hover:bg-blue-100 px-2 py-2 rounded-md transition-colors"
              onClick={() => setOpen(false)}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
