import { NextRequest, NextResponse } from "next/server"

export async function GET(request: NextRequest) {
  const token = request.nextUrl.searchParams.get("token")

  if (!token || token.split(".").length !== 3) {
    return NextResponse.redirect(
      new URL("/login?error=invalid_token", request.url),
    )
  }

  const isHttps =
    request.headers.get("x-forwarded-proto") === "https" ||
    request.nextUrl.protocol === "https:"

  const response = NextResponse.redirect(new URL("/dashboard", request.url))
  response.cookies.set("access_token", token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 8, // 8 days
    secure: isHttps,
  })

  return response
}
