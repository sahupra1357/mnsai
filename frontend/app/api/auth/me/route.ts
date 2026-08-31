import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

/** Per-user and cookie-dependent, so it must never be stored by any cache.
 *  Next's default for this route was `public, max-age=0, must-revalidate` with
 *  no `Vary: Cookie`, which invites a shared cache to hand one visitor's
 *  identity to the next. */
const NO_STORE = {
  "Cache-Control": "private, no-store, max-age=0, must-revalidate",
} as const

export async function GET(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value

  if (!token) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401, headers: NO_STORE },
    )
  }

  const backendRes = await fetch(`${BACKEND_URL}/api/v1/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  })

  if (!backendRes.ok) {
    const error = await backendRes.json().catch(() => ({ detail: "Unauthorized" }))
    const response = NextResponse.json(error, {
      status: backendRes.status,
      headers: NO_STORE,
    })
    // The backend refused this token, so it is dead whatever the reason —
    // expired, or signed with a key the API no longer uses. Dropping it here is
    // what stops a stale cookie from following the user around: this is the
    // first call the app makes on every page, so one load returns the browser
    // to a clean signed-out state instead of a half-authenticated one.
    // Only 401/403 count — a 5xx means the API is unwell, not the session.
    if (backendRes.status === 401 || backendRes.status === 403) {
      response.cookies.delete("access_token")
    }
    return response
  }

  const user = await backendRes.json()
  return NextResponse.json(user, { headers: NO_STORE })
}
