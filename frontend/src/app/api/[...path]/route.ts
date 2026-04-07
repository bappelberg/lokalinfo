import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

function clientIP(req: NextRequest): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "";
}

function forwardHeaders(req: NextRequest): Record<string, string> {
  const headers: Record<string, string> = { "x-real-ip": clientIP(req) };
  const auth = req.headers.get("authorization");
  if (auth) headers["authorization"] = auth;
  return headers;
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const url = `${BACKEND}/${path.join("/")}${req.nextUrl.search}`;
  const res = await fetch(url, { headers: forwardHeaders(req) });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.filter(Boolean).join("/");
  const url = `${BACKEND}/${pathStr}`;
  const body = await req.text();
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": req.headers.get("content-type") ?? "application/json",
      ...forwardHeaders(req),
    },
    body: body || undefined,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const pathStr = path.filter(Boolean).join("/");
  const url = `${BACKEND}/${pathStr}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: forwardHeaders(req),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
