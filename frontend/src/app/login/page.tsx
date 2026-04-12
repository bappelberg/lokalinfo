"use client";
import { useState } from "react"
import { signIn } from "next-auth/react"
import { useRouter } from "next/navigation"
import Link from "next/link"

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault()
    setError("")
    setLoading(true)
    const form = e.currentTarget
    const identifier = (form.elements.namedItem("identifier") as HTMLInputElement).value
    const password = (form.elements.namedItem("password") as HTMLInputElement).value

    const result = await signIn("credentials", { identifier, password, redirect: false })
    setLoading(false)

    if (result?.error) {
      setError("Fel inloggningsuppgifter.")
    } else {
      router.push("/")
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-12 bg-gray-50">

      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-semibold text-blue-900 mb-6">Logga in</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              E-post eller användarnamn
            </label>
            <input
              id="identifier"
              name="identifier"
              type="text"
              required
              autoComplete="email"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Lösenord
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              autoComplete="current-password"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 mt-1"
          >
            {loading ? "Loggar in..." : "Logga in"}
          </button>
        </form>
        <p className="mt-5 text-center text-sm text-gray-500">
          Inget konto?{" "}
          <Link href="/registrer" className="text-blue-600 hover:underline">
            Registrera dig
          </Link>
        </p>
      </div>
    </main>
  )
}