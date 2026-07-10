import { NextRequest, NextResponse } from "next/server"

/**
 * Server-side proxy for the public profile chat agent.
 *
 * - Keeps the FastAPI URL server-side (never exposed to the browser).
 * - Rejects requests whose Origin/Referer isn't this site (Layer 5 / CSRF-style
 *   guard) — the chat box only ever calls same-origin.
 * - Forwards the caller IP so the backend's per-IP rate limit is meaningful.
 * - Streams the SSE response straight through to the browser.
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

function allowedOrigin(request: NextRequest): boolean {
  const self = request.nextUrl.origin
  const origin = request.headers.get("origin")
  const referer = request.headers.get("referer")

  // If neither header is present (e.g. some same-origin GETs), be permissive;
  // browsers always send Origin on cross-origin POSTs, which is what we block.
  if (!origin && !referer) return true
  if (origin) return origin === self
  try {
    return new URL(referer as string).origin === self
  } catch {
    return false
  }
}

export async function POST(request: NextRequest) {
  if (!allowedOrigin(request)) {
    return NextResponse.json({ detail: "Forbidden" }, { status: 403 })
  }

  const body = await request.text()

  // Cheap upstream guard against absurd payloads before hitting the backend.
  if (body.length > 64_000) {
    return NextResponse.json({ detail: "Request too large" }, { status: 413 })
  }

  const clientIp =
    request.headers.get("x-forwarded-for") ||
    request.headers.get("x-real-ip") ||
    ""

  let backendRes: Response
  try {
    backendRes = await fetch(`${BACKEND_URL}/api/v1/profile-chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(clientIp ? { "x-forwarded-for": clientIp } : {}),
      },
      body,
    })
  } catch {
    return NextResponse.json(
      { detail: "The assistant is unavailable right now." },
      { status: 502 },
    )
  }

  if (!backendRes.ok || !backendRes.body) {
    const err = await backendRes
      .json()
      .catch(() => ({ detail: "Chat failed" }))
    return NextResponse.json(err, { status: backendRes.status })
  }

  // Stream the SSE body straight through.
  return new Response(backendRes.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  })
}
