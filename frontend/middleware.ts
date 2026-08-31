import { type NextRequest, NextResponse } from "next/server"

/** Signed-in-only prefixes. Never add "/" here — every path starts with it, so
 *  a prefix match would lock the whole site. */
const PROTECTED_PATHS = [
  // "/dashboard" is not here: it only redirects to the public dashboard at "/".
  "/items",
  "/admin",
  "/settings",
  "/extractor",
  "/document-extractions",
  "/contract-extraction",
  "/solutions",
]

/** True when the cookie is a structurally intact JWT whose `exp` is in the
 *  future. The signature is NOT checked — only the backend holds the key — so
 *  this can still be wrong about a token the backend will reject (a rotated
 *  SECRET_KEY invalidates every outstanding token while leaving it looking
 *  perfectly well-formed here). Presence alone is therefore never treated as
 *  proof of a session: this decides only whether to bother rendering a
 *  protected page, and the API is what actually authenticates. */
function looksLikeLiveSession(token: string | undefined): boolean {
  if (!token) return false

  const payload = token.split(".")[1]
  if (!payload) return false

  try {
    // Base64url → base64; atob is the only decoder available on the edge.
    const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"))
    const exp = (JSON.parse(json) as { exp?: number }).exp
    // A token with no exp never expires as far as we can tell; let the API rule.
    return typeof exp !== "number" || exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get("access_token")?.value

  // "/" is the dashboard and stays public — it renders for signed-out visitors
  // too; the individual tools it links to are what require a session.
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p))

  if (isProtected && !looksLikeLiveSession(token)) {
    const response = NextResponse.redirect(new URL("/login", request.url))
    // A cookie we just judged dead would otherwise keep failing every request
    // until it expires on its own. Clearing it here is what turns a stale
    // session back into a plain signed-out one.
    if (token) response.cookies.delete("access_token")
    return response
  }

  // There is deliberately no branch for /login, /signup or the password-reset
  // pages: they are reachable by anyone, cookie or not.
  // Cookie presence is not proof of a usable session, and bouncing on it strands
  // anyone holding a token the backend no longer accepts: the app shows them
  // "Sign In" (because /api/auth/me correctly 401s) while /login redirects them
  // straight back, so the button appears dead and there is no way to
  // re-authenticate short of clearing site data. The login page sends genuinely
  // signed-in users home itself, where the session has actually been verified.

  return NextResponse.next()
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico|assets|api/).*)",
}
