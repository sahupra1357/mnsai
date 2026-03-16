import { NextRequest, NextResponse } from "next/server"

const PROTECTED_PATHS = [
  "/dashboard",
  "/items",
  "/admin",
  "/settings",
  "/extractor",
  "/solutions",
]

const PUBLIC_AUTH_PATHS = ["/login", "/signup", "/recover-password", "/reset-password"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get("access_token")?.value

  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p))
  const isPublicAuth = PUBLIC_AUTH_PATHS.some((p) => pathname.startsWith(p))

  // Redirect logged-in users away from the public landing page
  if (pathname === "/" && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url))
  }

  if (isProtected && !token) {
    const loginUrl = new URL("/login", request.url)
    return NextResponse.redirect(loginUrl)
  }

  if (isPublicAuth && token) {
    const dashboardUrl = new URL("/dashboard", request.url)
    return NextResponse.redirect(dashboardUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: "/((?!_next/static|_next/image|favicon.ico|assets|api/).*)",
}
