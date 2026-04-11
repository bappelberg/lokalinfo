"use client";

import { useState } from "react";
import Link from "next/link";

export default function Navbar() {
  const [open, setOpen] = useState(false);

  // Centraliserad lista för att enkelt lägga till/ta bort sidor
  const links = [
    { href: "/", label: "Karta" },
    { href: "/about", label: "Om oss" },
    { href: "/loggain", label: "Logga in" },
    { href: "/registrera", label: "Registrera", isButton: true },
  ];

  return (
    <nav className="bg-blue-50 border-b border-blue-200 shadow-sm z-50">
      <div className="flex items-center justify-between px-4 py-2">
        {/* Logotyp */}
        <Link href="/" className="text-lg font-semibold text-blue-900 tracking-tight">
          LokalInfo
        </Link>

        {/* Desktop Menu */}
        <div className="hidden sm:flex items-center gap-4 text-sm text-blue-700">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={
                l.isButton
                  ? "bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700 transition-colors font-medium"
                  : "hover:text-blue-900 hover:bg-blue-100 px-2 py-1 rounded-md transition-colors"
              }
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* Hamburger Button */}
        <button
          className="sm:hidden p-2 rounded-md text-blue-700 hover:bg-blue-100 transition-colors"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Stäng meny" : "Öppna meny"}
        >
          {open ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile Menu */}
      {open && (
        <div className="sm:hidden border-t border-blue-200 px-4 py-3 flex flex-col gap-2 text-sm text-blue-700 bg-blue-50">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={
                l.isButton
                  ? "bg-blue-600 text-white px-3 py-2.5 rounded-md text-center font-medium mt-1"
                  : "hover:text-blue-900 hover:bg-blue-100 px-2 py-2 rounded-md transition-colors"
              }
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