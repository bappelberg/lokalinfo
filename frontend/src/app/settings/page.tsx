"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

export default function SettingsPage() {
  const { data: session, status, update } = useSession();
  const router = useRouter();

  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (status === "unauthenticated") router.push("/login");
  }, [status, router]);

  useEffect(() => {
    if (session?.user?.image) setAvatarUrl(session.user.image);
  }, [session]);

  if (status === "loading" || status === "unauthenticated") return null;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setPreview(URL.createObjectURL(file));
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("image", file);
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error ?? "Uppladdningen misslyckades.");
        setPreview(null);
        return;
      }
      const data = await res.json();
      setAvatarUrl(data.url);
    } finally {
      setUploading(false);
    }
  }

  async function handleSave() {
    setError("");
    setSaved(false);
    const res = await fetch("/api/users/me/avatar", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ avatar_url: avatarUrl }),
    });
    if (!res.ok) {
      setError("Kunde inte spara. Försök igen.");
      return;
    }
    await update({ image: avatarUrl });
    setSaved(true);
  }

  const displayAvatar = preview ?? avatarUrl;
  const initial = session?.user?.name?.[0]?.toUpperCase() ?? "?";

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-12 bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-2xl font-semibold text-blue-900 mb-6">Inställningar</h1>

        <div className="flex flex-col items-center gap-4 mb-6">
          <button
            onClick={() => fileRef.current?.click()}
            className="relative group"
            disabled={uploading}
          >
            {displayAvatar ? (
              <img
                src={displayAvatar}
                alt="Avatar"
                className="w-24 h-24 rounded-full object-cover border-2 border-gray-200 group-hover:opacity-80 transition-opacity"
              />
            ) : (
              <span className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center text-3xl font-semibold text-blue-600 group-hover:bg-blue-200 transition-colors">
                {initial}
              </span>
            )}
            <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity text-white text-xs font-medium">
              {uploading ? "Laddar…" : "Ändra"}
            </span>
          </button>
          <p className="text-sm text-gray-500">Klicka för att välja bild</p>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Användarnamn</label>
          <p className="text-sm text-gray-900 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50">
            {session?.user?.name}
          </p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">E-post</label>
          <p className="text-sm text-gray-900 px-3 py-2 border border-gray-200 rounded-lg bg-gray-50">
            {session?.user?.email}
          </p>
        </div>

        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        {saved && <p className="text-green-600 text-sm mb-3">Sparat!</p>}

        <button
          onClick={handleSave}
          disabled={uploading || !avatarUrl}
          className="w-full bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          Spara
        </button>
      </div>
    </main>
  );
}
