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

const PUBLIC_AUTH_PATHS = [
  "/login",
  "/signup",
  "/recover-password",
  "/reset-password",
]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get("access_token")?.value

  // "/" is the dashboard and stays public — it renders for signed-out visitors
  // too; the individual tools it links to are what require a session.
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p))
  const isPublicAuth = PUBLIC_AUTH_PATHS.some((p) => pathname.startsWith(p))

  if (isProtected && !token) {
    const loginUrl = new URL("/login", request.url)
    return NextResponse.redirect(loginUrl)
  }

  if (isPublicAuth && token) {
    const dashboardUrl = new URL("/", request.url)
    return NextResponse.redirect(dashboardUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico|assets|api/).*)",
}
