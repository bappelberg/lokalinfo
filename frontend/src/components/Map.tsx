"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const API_URL = "/api";
const HISTORY_DAYS = 30;

// ─── Kategorier ────────────────────────────────────────────────────────────────

const CATEGORIES: Record<string, { label: string; color: string }> = {
  brott:      { label: "Brott",      color: "#ef4444" },
  trafik:     { label: "Trafik",     color: "#f97316" },
  brand:      { label: "Brand",      color: "#dc2626" },
  event:      { label: "Event",      color: "#22c55e" },
  storning:   { label: "Störning",   color: "#a855f7" },
  rekreation: { label: "Rekreation", color: "#14b8a6" },
  natur:      { label: "Natur",      color: "#16a34a" },
  hjalp:      { label: "Hjälp",      color: "#0ea5e9" },
  kultur:     { label: "Kultur",     color: "#f59e0b" },
  mat:        { label: "Mat",        color: "#ec4899" },
  ovrigt:     { label: "Övrigt",     color: "#6b7280" },
};

function makeIcon(category: string, pulse = false) {
  const color = CATEGORIES[category]?.color ?? "#6b7280";
  const size = pulse ? 18 : 14;
  return L.divIcon({
    html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.5)"></div>`,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// ─── Hjälpfunktioner ───────────────────────────────────────────────────────────

function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(d: Date, n: number): Date {
  const result = new Date(d);
  result.setDate(result.getDate() + n);
  return result;
}

function formatSwedish(d: Date): string {
  return d.toLocaleDateString("sv-SE", { weekday: "long", day: "numeric", month: "long" });
}

function buildTree(flat: Comment[]) {
  const top = flat.filter((c) => c.parent_id === null);
  const replies = flat.filter((c) => c.parent_id !== null);
  return top.map((c) => ({
    ...c, replies: replies.filter((r) => r.parent_id === c.id)
  }));
}


// ─── Typer ─────────────────────────────────────────────────────────────────────

type BBox = [number, number, number, number];

type Post = {
  id: string;
  title: string;
  content: string;
  category: string;
  lat: number;
  lng: number;
  created_at: string;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  report_count: number;
  is_hidden: boolean;
};

type Comment = {
  id: string;
  post_id: string;
  parent_id: string | null;
  content: string;
  upvote_count: number;
  downvote_count: number;
  created_at: string;
};

// ─── Kartkomponenter ───────────────────────────────────────────────────────────

function LocateUser({ onLocate }: { onLocate: (lat: number, lng: number) => void }) {
  const map = useMap();
  const onLocateRef = useRef(onLocate);
  onLocateRef.current = onLocate;

  useEffect(() => {
    const FALLBACK_LAT = 59.3293;
    const FALLBACK_LNG = 18.0686;
    map.locate({ setView: true, maxZoom: 14 });
    map.once("locationfound", (e) => onLocateRef.current(e.latlng.lat, e.latlng.lng));
    // Geolocation kräver HTTPS eller localhost — nekas på http + IP (t.ex. vid LAN-test).
    // Utan fallback förblir centerRef null och fetchPosts anropas aldrig.
    map.once("locationerror", () => {
      map.setView([FALLBACK_LAT, FALLBACK_LNG], 13);
      onLocateRef.current(FALLBACK_LAT, FALLBACK_LNG);
    });
  }, [map]); // kör bara en gång — utan ref i deps körs map.locate() varje render och skriver över sökning
  return null;
}

function FlyTo({
  target,
  onArrived,
}: {
  target: { lat: number; lon: number; bbox?: BBox } | null;
  onArrived: (lat: number, lng: number) => void;
}) {
  const map = useMap();
  useEffect(() => {
    if (!target) return;
    if (target.bbox) {
      map.fitBounds([
        [target.bbox[0], target.bbox[2]],
        [target.bbox[1], target.bbox[3]],
      ]);
    } else {
      map.setView([target.lat, target.lon], 16);
    }
    onArrived(target.lat, target.lon);
  }, [target, map, onArrived]);
  return null;
}

function MapClickHandler({ onClick }: { onClick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onClick(e.latlng.lat, e.latlng.lng) });
  return null;
}

// ─── Huvudkomponent ────────────────────────────────────────────────────────────

export default function Map() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Sök
  const [query, setQuery] = useState("");
  const [searchError, setSearchError] = useState("");
  const [target, setTarget] = useState<{ lat: number; lon: number; bbox?: BBox } | null>(null);

  // Inlägg
  const [posts, setPosts] = useState<Post[]>([]);

  // Historik — null = idag (live), annars ett datum
  const [historyDate, setHistoryDate] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const isLive = historyDate === null;

  // Skapa inlägg
  const [addMode, setAddMode] = useState(false);
  const [newPin, setNewPin] = useState<{ lat: number; lng: number } | null>(null);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("ovrigt");
  const [submitting, setSubmitting] = useState(false);
  const [createError, setCreateError] = useState("");

  // Rapport
  const [reported, setReported] = useState<Set<string>>(new Set());

  const centerRef = useRef<{ lat: number; lng: number } | null>(null);

  const [dateInput, setDateInput] = useState("");

  const fetchPosts = useCallback(async (lat: number, lng: number, date: Date | null) => {
    try {
      let url = `${API_URL}/posts/?lat=${lat}&lng=${lng}&radius=20`;
      if (date !== null) url += `&date=${toDateString(date)}`;
      const res = await fetch(url);
      if (res.ok) setPosts(await res.json());
    } catch {
      // tyst fel
    }
  }, []);

  // Polling var 30s — bara i live-läge
  useEffect(() => {
    if (!isLive) return;
    const id = setInterval(() => {
      if (centerRef.current)
        fetchPosts(centerRef.current.lat, centerRef.current.lng, null);
    }, 30_000);
    return () => clearInterval(id);
  }, [isLive, fetchPosts]);

  // Hämta om när historikdatum ändras
  useEffect(() => {
    if (centerRef.current)
      fetchPosts(centerRef.current.lat, centerRef.current.lng, historyDate);
  }, [historyDate, fetchPosts]);

  useEffect(() => {
    if (historyDate) {
      setDateInput(toDateString(historyDate));
    } else {
      setDateInput("");
    }
  }, [historyDate]);

  async function handleSearch(e: React.SubmitEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`,
      { headers: { "Accept-Language": "sv" } }
    );
    const results = await res.json();
    if (results.length === 0) { setSearchError("Hittade ingen adress"); return; }
    setSearchError("");
    const { lat, lon, boundingbox } = results[0];
    setTarget({
      lat: parseFloat(lat),
      lon: parseFloat(lon),
      bbox: boundingbox
        ? [parseFloat(boundingbox[0]), parseFloat(boundingbox[1]), parseFloat(boundingbox[2]), parseFloat(boundingbox[3])]
        : undefined,
    });
  }

  async function handleCreate(e: React.SubmitEvent) {
    e.preventDefault();
    if (!newPin || !content.trim()) return;
    setSubmitting(true);
    setCreateError("");
    try {
      const res = await fetch(`${API_URL}/posts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, content, category, lat: newPin.lat, lng: newPin.lng }),
      });
      if (res.status === 429) {
        const err = await res.json();
        setCreateError(err.detail);
        return;
      }
      if (!res.ok) { setCreateError("Något gick fel. Försök igen."); return; }
      if (centerRef.current) {
        await fetchPosts(centerRef.current.lat, centerRef.current.lng, historyDate);
      }
      setNewPin(null);
      setTitle("");
      setContent("");
      setCategory("ovrigt");
      setAddMode(false);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReport(postId: string) {
    if (reported.has(postId)) return;
    const res = await fetch(`${API_URL}/posts/${postId}/report`, { method: "POST" });
    if (res.ok) {
      setReported((prev) => new Set(prev).add(postId));
      setPosts((prev) =>
        prev.map((p) => p.id === postId ? { ...p, report_count: p.report_count + 1 } : p)
      );
    }
  }

  function formatTime(iso: string) {
    const utc = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
    const diff = (Date.now() - new Date(utc).getTime()) / 60000;
    if (diff < 60) return `${Math.round(diff)} min sedan`;
    return `${Math.round(diff / 60)} tim sedan`;
  }

  const minDate = toDateString(addDays(today, -HISTORY_DAYS));
  const maxDate = toDateString(today);

    // Votes on posts (localStorage)
  const [votes, setVotes] = useState<Record<string, "up" | "down">>(() => {
    try { return JSON.parse(localStorage.getItem("lokalinfo_votes") ?? "{}");}
    catch { return {}; }
  });

  // Thread panel
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentSort, setCommentSort] = useState<"popular" | "newest">("popular");
  const [commentVotes, setCommentVotes] = useState<Record<string, "up" | "down">>(() => {
    try { return JSON.parse(localStorage.getItem("lokalinfo_comment_votes") ?? "{}");}
    catch { return {}; }
  })
  const [newComment, setNewComment] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyText, setReplyText] = useState("");
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [commentError, setCommentError] = useState(false);

  // Fetch comments
  const fetchComments = useCallback(async (postId: string, sort: "popular" | "newest") => {
    setCommentError(false);
    try {
      const res = await fetch(`${API_URL}/posts/${postId}/comments/?sort=${sort}`);
      if (res.ok) {
        setComments(await res.json());
      } else {
        setCommentError(true);
      }
    } catch {
      setCommentError(true);
    }
  }, []);

  useEffect(() => {
    if (selectedPost) {
      fetchComments(selectedPost.id, commentSort);
    }
  }, [commentSort, selectedPost, fetchComments]);

  // handleVote for posts

  async function handleVote(postId: string, direction: "up" | "down") {
    const res = await fetch(`${API_URL}/posts/${postId}/${direction}vote`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      const newVotes = { ...votes };
      if (data.direction === null) delete newVotes[postId];
      else newVotes[postId] = data.direction;
      setVotes(newVotes);
      localStorage.setItem("lokalinfo_votes", JSON.stringify(newVotes));
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, upvote_count: data.upvote_count, downvote_count: data.downvote_count } : p
        )
      );
      if (selectedPost?.id === postId) {
        setSelectedPost((prev) =>
          prev ? { ...prev, upvote_count: data.upvote_count, downvote_count: data.downvote_count } : prev
        );
      }
    }
  }

  async function handleCommentVote(commentId: string, direction: "up" | "down") {
    const postId = comments.find((c) => c.id === commentId)?.post_id;
    if (!postId) return;
    const res = await fetch(
      `${API_URL}/posts/${postId}/comments/${commentId}/${direction}vote/`,
      { method: "POST" }
    );
    if (res.ok) {
      const data = await res.json();
      const newVotes = { ...commentVotes };
      if (data.direction === null) delete newVotes[commentId];
      else newVotes[commentId] = data.direction;
      setCommentVotes(newVotes);
      localStorage.setItem("lokalinfo_comment_votes", JSON.stringify(newVotes));
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId
            ? { ...c, upvote_count: data.upvote_count, downvote_count: data.downvote_count }
            : c
        )
      );
    }
  }

  async function handleAddComment(content: string, parentId: string | null) {
    if (!selectedPost || !content.trim()) {
      return;
    }
    setCommentSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/posts/${selectedPost.id}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, parent_id: parentId })
      });
      if (res.ok) {
        await fetchComments(selectedPost.id, commentSort);
        setPosts((prev) =>
          prev.map((p) =>
            p.id === selectedPost.id ? { ...p, comment_count: p.comment_count + 1 } : p
          )
        );
        setSelectedPost((prev) => prev ? { ...prev, comment_count: prev.comment_count + 1 } : prev);
        if (parentId) {
          setReplyTo(null);
          setReplyText("");
        } else {
          setNewComment("");
        }
      }
    } finally {
      setCommentSubmitting(false);
    }
  }

  function makeIcon(category: string, upvotes = 0, pulse = false) {
    const color = CATEGORIES[category]?.color ?? "#6b7280";
    const base = 14;
    const extra = Math.min(Math.log1p(upvotes) * 4, 14)
    const size = pulse ? 18 : Math.round(base + extra);
    return L.divIcon({
      html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.5)"></div>`,
      className: "",
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }

  
  return (
    <div className="relative h-full w-full">

      {/* ── Tråd-panel ── */}
      {selectedPost && (
        <div className="absolute inset-y-0 right-0 z-[1002] w-full max-w-sm bg-white shadow-2xl flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span
              className="rounded-full px-2 py-0.5 text-white text-xs font-medium"
              style={{ background: CATEGORIES[selectedPost.category]?.color ?? "#6b7280" }}
            >
              {CATEGORIES[selectedPost.category]?.label ?? selectedPost.category}
            </span>
            <span className="text-xs text-gray-400">{formatTime(selectedPost.created_at)}</span>
            <button
              onClick={() => { setSelectedPost(null); setComments([]); setCommentError(false); }}
              className="ml-2 text-gray-400 hover:text-gray-700 text-xl leading-none"
            >
              ×
            </button>
          </div>
          <div className="px-4 py-3 border-b border-gray-100">
            {selectedPost.title && (
              <p className="font-semibold text-gray-900 mb-1">{selectedPost.title}</p>
            )}
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{selectedPost.content}</p>
            <div className="flex items-center gap-3 mt-3">
              <button
                onClick={() => handleVote(selectedPost.id, "up")}
                disabled={false}
                className={`flex items-center gap-1 text-xs font-medium transition-colors ${
                  votes[selectedPost.id] === "up" ? "text-green-600" : "text-gray-400 hover:text-green-500 disabled:text-gray-300"
                }`}
              >
                ▲ {selectedPost.upvote_count}
              </button>
              <button
                onClick={() => handleVote(selectedPost.id, "down")}
                disabled={false}
                className={`flex items-center gap-1 text-xs font-medium transition-colors ${
                  votes[selectedPost.id] === "down" ? "text-red-600" : "text-gray-400 hover:text-red-500 disabled:text-gray-300"
                }`}
              >
                ▼ {selectedPost.downvote_count}
              </button>
              {isLive && (
                <button
                  onClick={() => handleReport(selectedPost.id)}
                  disabled={reported.has(selectedPost.id)}
                  className="ml-auto text-xs text-gray-400 hover:text-red-500 disabled:text-gray-300 transition-colors"
                >
                  {reported.has(selectedPost.id) ? "Rapporterat" : "Rapportera"}
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Kommentarer ({comments.length})
            </span>
            <div className="flex gap-1">
              <button
                onClick={() => setCommentSort("popular")}
                className={`text-xs px-2 py-1 rounded-lg transition-colors ${
                  commentSort === "popular" ? "bg-blue-100 text-blue-700 font-medium" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                Populära
              </button>
              <button
                onClick={() => setCommentSort("newest")}
                className={`text-xs px-2 py-1 rounded-lg transition-colors ${
                  commentSort === "newest" ? "bg-blue-100 text-blue-700 font-medium" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                Senaste
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
            {commentError && (
              <p className="text-sm text-red-400 text-center py-6">Kunde inte ladda kommentarer. <button onClick={() => fetchComments(selectedPost!.id, commentSort)} className="underline">Försök igen</button></p>
            )}
            {!commentError && buildTree(comments).length === 0 && (
              <p className="text-sm text-gray-400 text-center py-6">Inga kommentarer ännu — var först!</p>
            )}
            {buildTree(comments).map((comment) => (
              <div key={comment.id}>
                <div className="text-sm">
                  <p className="text-gray-800 whitespace-pre-wrap">{comment.content}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <span className="text-xs text-gray-400">{formatTime(comment.created_at)}</span>
                    <button
                      onClick={() => handleCommentVote(comment.id, "up")}
                      disabled={false}
                      className={`text-xs transition-colors ${
                        commentVotes[comment.id] === "up" ? "text-green-600 font-medium" : "text-gray-400 hover:text-green-500 disabled:text-gray-300"
                      }`}
                    >
                      ▲ {comment.upvote_count}
                    </button>
                    <button
                      onClick={() => handleCommentVote(comment.id, "down")}
                      disabled={false}
                      className={`text-xs transition-colors ${
                        commentVotes[comment.id] === "down" ? "text-red-600 font-medium" : "text-gray-400 hover:text-red-500 disabled:text-gray-300"
                      }`}
                    >
                      ▼ {comment.downvote_count}
                    </button>
                    {isLive && (
                      <button
                        onClick={() => setReplyTo(replyTo === comment.id ? null : comment.id)}
                        className="text-xs text-gray-400 hover:text-blue-500 transition-colors"
                      >
                        {replyTo === comment.id ? "Avbryt" : "Svara"}
                      </button>
                    )}
                  </div>
                  {replyTo === comment.id && (
                    <div className="mt-2 ml-3 flex gap-2">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        placeholder="Skriv ett svar…"
                        maxLength={500}
                        rows={2}
                        className="flex-1 rounded-lg border border-gray-200 px-2 py-1.5 text-xs resize-none outline-none focus:ring-2 focus:ring-blue-500"
                      />
                      <button
                        onClick={() => handleAddComment(replyText, comment.id)}
                        disabled={commentSubmitting || !replyText.trim()}
                        className="self-end rounded-lg bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        Skicka
                      </button>
                    </div>
                  )}
                </div>
                {comment.replies.length > 0 && (
                  <div className="ml-4 mt-2 space-y-3 border-l-2 border-gray-100 pl-3">
                    {comment.replies.map((reply) => (
                      <div key={reply.id} className="text-sm">
                        <p className="text-gray-700 whitespace-pre-wrap">{reply.content}</p>
                        <div className="flex items-center gap-3 mt-1.5">
                          <span className="text-xs text-gray-400">{formatTime(reply.created_at)}</span>
                          <button
                            onClick={() => handleCommentVote(reply.id, "up")}
                            disabled={false}
                            className={`text-xs transition-colors ${
                              commentVotes[reply.id] === "up" ? "text-green-600 font-medium" : "text-gray-400 hover:text-green-500 disabled:text-gray-300"
                            }`}
                          >
                            ▲ {reply.upvote_count}
                          </button>
                          <button
                            onClick={() => handleCommentVote(reply.id, "down")}
                            disabled={false}
                            className={`text-xs transition-colors ${
                              commentVotes[reply.id] === "down" ? "text-red-600 font-medium" : "text-gray-400 hover:text-red-500 disabled:text-gray-300"
                            }`}
                          >
                            ▼ {reply.downvote_count}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          {isLive && (
            <div className="px-4 py-3 border-t border-gray-100">
              <div className="flex gap-2">
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Skriv en kommentar… (max 500 tecken)"
                  maxLength={500}
                  rows={2}
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={() => handleAddComment(newComment, null)}
                  disabled={commentSubmitting || !newComment.trim()}
                  className="self-end rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  Skicka
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Historikrad (toppen) ── */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-2">
        {!isLive && (
          <button
            onClick={() => {
              setHistoryDate(null);
              setShowDatePicker(false);
              setAddMode(false);
            }}
            className="rounded-xl bg-white px-3 py-1.5 text-xs font-medium text-blue-600 shadow-md hover:bg-blue-50 border border-blue-200"
          >
            ← Gå till idag
          </button>
        )}
        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          {isLive ? (
            <button
              onClick={() => setShowDatePicker((s) => !s)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse inline-block" />
              Live — idag
              <span className="text-gray-400 text-xs ml-1">Historik ▾</span>
            </button>
          ) : (
            <button
              onClick={() => setShowDatePicker((s) => !s)}
              className="flex items-center gap-2 px-4 py-2 text-sm text-amber-700 bg-amber-50 hover:bg-amber-100"
            >
              <span className="text-amber-500">⏪</span>
              {formatSwedish(historyDate!)}
              <span className="text-amber-400 text-xs ml-1">ändra ▾</span>
            </button>
          )}
          {showDatePicker && (
            <div className="border-t border-gray-100 px-3 py-2">
              <p className="text-xs text-gray-400 mb-1">Välj dag (max 30 dagar tillbaka)</p>
              <input
                type="date"
                min={minDate}
                max={maxDate}
                value={dateInput}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!val) return;

                  setDateInput(val);

                  const [y, m, d] = val.split("-").map(Number);
                  const picked = new Date(y, m - 1, d);

                  if (toDateString(picked) === toDateString(today)) {
                    setHistoryDate(null);
                  } else {
                    setHistoryDate(picked);
                  }

                  // ⚠️ Delay för iOS så picker inte stängs direkt
                  setTimeout(() => {
                    setShowDatePicker(false);
                    setAddMode(false);
                  }, 100);
                }}
                className="w-full rounded border border-gray-200 px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Lägg till inlägg-knapp (bara i live-läge) ── */}
      {isLive && (
        <div className="absolute top-4 right-4 z-[1000]">
          <button
            onClick={() => { setAddMode((m) => !m); setNewPin(null); }}
            className={`rounded-xl px-4 py-2 text-sm font-medium shadow-md transition-colors ${
              addMode
                ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {addMode ? "Avbryt" : "+"}
          </button>
        </div>
      )}

      {/* ── Guide-text i add-mode ── */}
      {addMode && !newPin && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-[1000] bg-white/90 backdrop-blur-sm rounded-xl px-4 py-2 shadow-md text-sm text-gray-700">
          Klicka på kartan för att placera ditt inlägg
        </div>
      )}

      {/* ── Formulär: skapa inlägg ── */}
      {addMode && newPin && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-[1001] w-80 bg-white rounded-2xl- shadow-2xl p-5">
          <h2 className="font-semibold text-gray-800 mb-3">Nytt inlägg</h2>
          <form onSubmit={handleCreate} className="flex flex-col gap-3">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Titel (max 80 tecken)"
              maxLength={80}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            >
              {Object.entries(CATEGORIES).map(([value, { label }]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Beskriv vad som händer… (max 280 tecken)"
              maxLength={280}
              rows={4}
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm resize-none outline-none focus:ring-2 focus:ring-blue-500"
            />
            <span className="text-xs text-gray-400 text-right">{content.length}/280</span>
            {createError && <p className="text-sm text-red-600">{createError}</p>}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setNewPin(null)}
                className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Tillbaka
              </button>
              <button
                type="submit"
                disabled={submitting || !title.trim() || !content.trim()}
                className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "Publicerar…" : "Publicera"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Sökfält (botten) ── */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[1000] w-80 bg-white rounded-xl p-3 shadow-lg">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Sök adress eller ort…"
            className="flex-1 rounded-lg px-3 py-2 text-sm border border-gray-200 outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Sök
          </button>
        </form>
        {searchError && <p className="mt-1 text-sm text-red-600 text-center">{searchError}</p>}
      </div>

      {/* ── Karta ── */}
      <MapContainer center={[62.0, 15.0]} zoom={5} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <LocateUser
          onLocate={(lat, lng) => {
            centerRef.current = { lat, lng };
            fetchPosts(lat, lng, historyDate);
          }}
        />
        <FlyTo
          target={target}
          onArrived={(lat, lng) => {
            centerRef.current = { lat, lng };
            fetchPosts(lat, lng, historyDate);
          }}
        />
        {addMode && isLive && (
          <MapClickHandler onClick={(lat, lng) => setNewPin({ lat, lng })} />
        )}

        {/* Förhandsnål */}
        {addMode && newPin && (
          <Marker position={[newPin.lat, newPin.lng]} icon={makeIcon(category, 0, true)} />
        )}

        {/* Inlägg */}
        {posts.map((post) => (
          <Marker key={post.id} position={[post.lat, post.lng]} icon={makeIcon(post.category, post.upvote_count)}>
            <Popup>
              <div className="text-sm min-w-[180px]">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="rounded-full px-2 py-0.5 text-white text-xs font-medium"
                    style={{ background: CATEGORIES[post.category]?.color ?? "#6b7280" }}
                  >
                    {CATEGORIES[post.category]?.label ?? post.category}
                  </span>
                  <span className="text-gray-400 text-xs">{formatTime(post.created_at)}</span>
                </div>
                <p className="font-semibold text-gray-900 mb-1">{post.title}</p>
                <p className="text-gray-700 my-2 whitespace-pre-wrap">{post.content}</p>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleVote(post.id, "up")}
                      disabled={false}
                      className={`flex items-center gap-1 text-xs font-medium transition-colors ${
                        votes[post.id] === "up"
                          ? "text-green-600"
                          : "text-gray-400 hover:text-green-500 disabled:text-gray-300"
                      }`}
                    >
                      ▲ {post.upvote_count}
                    </button>
                    <button
                      onClick={() => handleVote(post.id, "down")}
                      disabled={false}
                      className={`flex items-center gap-1 text-xs font-medium transition-colors ${
                        votes[post.id] === "down"
                          ? "text-red-600"
                          : "text-gray-400 hover:text-red-500 disabled:text-gray-300"
                      }`}
                    >
                      ▼ {post.downvote_count}
                    </button>
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      &#128172; {post.comment_count}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedPost(post);
                      setCommentSort("popular");
                      fetchComments(post.id, "popular");
                    }}
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium transition-colors"
                  >
                    Visa kommentarer →
                  </button>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}