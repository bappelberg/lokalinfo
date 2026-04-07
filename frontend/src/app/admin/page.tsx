"use client";

import { useEffect, useState } from "react";

const API_URL = "/api";

type Post = {
  id: string;
  title: string;
  content: string;
  category: string;
  report_count: number;
  is_hidden: boolean;
  is_deleted: boolean;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  created_at: string;
};

type Comment = {
  id: string;
  content: string;
  upvote_count: number;
  downvote_count: number;
  created_at: string;
  parent_id: string | null;
};

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [posts, setPosts] = useState<Post[]>([]);
  const [expandedPost, setExpandedPost] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, Comment[]>>({});

  useEffect(() => {
    const saved = sessionStorage.getItem("admin_token");
    if (!saved) return;
    setToken(saved);
    fetch(`${API_URL}/admin/posts`, { headers: { Authorization: `Bearer ${saved}` } })
      .then((res) => res.ok ? res.json() : null)
      .then((data) => { if (data) setPosts(data); });
  }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    const res = await fetch(`${API_URL}/admin/posts`, {
      headers: { Authorization: `Bearer ${input}` },
    });
    if (res.status === 403) {
      setError("Fel token.");
      return;
    }
    sessionStorage.setItem("admin_token", input);
    setToken(input);
    setPosts(await res.json());
    setError("");
  }

  async function fetchPosts(t: string) {
    const res = await fetch(`${API_URL}/admin/posts`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (res.ok) setPosts(await res.json());
  }

  async function fetchComments(postId: string) {
    if (comments[postId]) {
      setExpandedPost(expandedPost === postId ? null : postId);
      return;
    }
    const res = await fetch(`${API_URL}/admin/posts/${postId}/comments`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const data = await res.json();
      setComments((prev) => ({ ...prev, [postId]: data }));
      setExpandedPost(postId);
    }
  }

  async function deletePost(postId: string) {
    if (!confirm("Ta bort inlägg?")) return;
    const res = await fetch(`${API_URL}/admin/posts/${postId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) setPosts((prev) => prev.filter((p) => p.id !== postId));
  }

  async function restorePost(postId: string) {
    const res = await fetch(`${API_URL}/admin/posts/${postId}/restore`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      const updated = await res.json();
      setPosts((prev) => prev.map((p) => (p.id === postId ? updated : p)));
    }
  }

  async function deleteComment(postId: string, commentId: string) {
    if (!confirm("Ta bort kommentar?")) return;
    const res = await fetch(`${API_URL}/admin/comments/${commentId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.ok) {
      setComments((prev) => ({
        ...prev,
        [postId]: prev[postId].filter((c) => c.id !== commentId),
      }));
    }
  }

  function formatTime(iso: string) {
    const utc = iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z";
    return new Date(utc).toLocaleString("sv-SE");
  }

  // ── Login ──────────────────────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-lg p-8 w-80">
          <h1 className="text-xl font-semibold text-gray-800 mb-6">Admin</h1>
          <form onSubmit={handleLogin} className="flex flex-col gap-3">
            <input
              type="password"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Admin-token"
              className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              className="rounded-lg bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700"
            >
              Logga in
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── Dashboard ──────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-gray-800">
            Admin — Rapporterade inlägg ({posts.length})
          </h1>
          <button
            onClick={() => {
              sessionStorage.removeItem("admin_token");
              setToken("");
              setPosts([]);
            }}
            className="text-sm text-gray-400 hover:text-gray-700"
          >
            Logga ut
          </button>
        </div>

        {posts.length === 0 && (
          <p className="text-gray-400 text-center py-12">Inga rapporterade inlägg.</p>
        )}

        <div className="space-y-4">
          {posts.map((post) => (
            <div key={post.id} className="bg-white rounded-xl shadow-sm p-4">
              {/* Post header */}
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-500 uppercase">{post.category}</span>
                    <span className="text-xs text-red-600 font-medium">
                      {post.report_count} rapporter
                    </span>
                    {post.is_hidden && (
                      <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                        Dold
                      </span>
                    )}
                  </div>
                  <p className="font-medium text-gray-900 truncate">{post.title}</p>
                  <p className="text-sm text-gray-600 mt-1 line-clamp-2">{post.content}</p>
                  <p className="text-xs text-gray-400 mt-1">{formatTime(post.created_at)}</p>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={() => deletePost(post.id)}
                    className="rounded-lg bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-700"
                  >
                    Ta bort
                  </button>
                  <button
                    onClick={() => restorePost(post.id)}
                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                  >
                    Återställ
                  </button>
                  <button
                    onClick={() => fetchComments(post.id)}
                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50"
                  >
                    {expandedPost === post.id ? "Dölj" : `Kommentarer (${post.comment_count})`}
                  </button>
                </div>
              </div>

              {/* Comments */}
              {expandedPost === post.id && comments[post.id] && (
                <div className="mt-4 border-t border-gray-100 pt-4 space-y-3">
                  {comments[post.id].length === 0 && (
                    <p className="text-sm text-gray-400">Inga kommentarer.</p>
                  )}
                  {comments[post.id].map((comment) => (
                    <div key={comment.id} className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        {comment.parent_id && (
                          <span className="text-xs text-gray-400 mr-1">↳ svar</span>
                        )}
                        <span className="text-sm text-gray-700">{comment.content}</span>
                        <div className="flex gap-3 mt-0.5">
                          <span className="text-xs text-gray-400">{formatTime(comment.created_at)}</span>
                          <span className="text-xs text-gray-400">▲ {comment.upvote_count} ▼ {comment.downvote_count}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => deleteComment(post.id, comment.id)}
                        className="shrink-0 text-xs text-red-500 hover:text-red-700"
                      >
                        Ta bort
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
