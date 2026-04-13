"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
    const router = useRouter();
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
        e.preventDefault();
        setError("");
        setLoading(true);

        const form = e.currentTarget;
        const username = (form.elements.namedItem("username") as HTMLInputElement).value;
        const email = (form.elements.namedItem("email") as HTMLInputElement).value;
        const password = (form.elements.namedItem("password") as HTMLInputElement).value;
        const confirm = (form.elements.namedItem("confirm") as HTMLInputElement).value;

        if (password !== confirm) {
            setError("Lösenorden matchar inte.");
            setLoading(false);
            return;
        }
        
        const res = await fetch("/api/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, email, password }),
        });

        if (!res.ok) {
            const data = await res.json().catch(() => null)
            setError(data?.detail ?? "Registreringen misslyckades.");
            setLoading(false);
            return;
        }

        const result = await signIn("credentials", {
            identifier: email, password, redirect: false
        })
        setLoading(false);

        if (result?.error) {
            setError("Kontot skapades men inloggningen misslyckades. Försök logga in manuellt.");
        } else {
            router.push("/");
        }
    }
    
    return (
        <main className="flex-1 flex item-center justify-center px-4 py-12 bg-gray-50">
            <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8">
                <h1 className="text-2xl font-semibold text-blue-900">Skapa konto</h1>
                <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
                        Användarnamn
                        </label>
                        <input
                        id="username"
                        name="username"
                        type="text"
                        required
                        minLength={3}
                        maxLength={50}
                        autoComplete="username"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                        E-post
                        </label>
                        <input
                        id="email"
                        name="email"
                        type="email"
                        required
                        autoComplete="email"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                        Lösenord <span className="text-gray-400 font-normal">(minst 8 tecken)</span>
                        </label>
                        <input
                        id="password"
                        name="password"
                        type="password"
                        required
                        minLength={8}
                        autoComplete="new-password"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    <div>
                        <label htmlFor="confirm" className="block text-sm font-medium text-gray-700 mb-1">
                        Bekräfta lösenord
                        </label>
                        <input
                        id="confirm"
                        name="confirm"
                        type="password"
                        required
                        minLength={8}
                        autoComplete="new-password"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    {error && <p className="text-red-600 text-sm">{error}</p>}
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 mt-1"
                    >
                        {loading ? "Skapar konto..." : "Skapa konto"}
                    </button>
                </form>
            </div>
        </main>
    )
}