import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  const formData = await request.formData()

  const backendRes = await fetch(
    `${BACKEND_URL}/api/v1/login/access-token`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        username: formData.get("username") as string,
        password: formData.get("password") as string,
      }),
    },
  )

  if (!backendRes.ok) {
    const error = await backendRes.json().catch(() => ({ detail: "Login failed" }))
    return NextResponse.json(error, { status: backendRes.status })
  }

  const data = await backendRes.json()

  // Set Secure only when the request arrived over HTTPS (Traefik/production).
  // Plain HTTP (local Docker dev) keeps secure:false so browsers accept the cookie.
  const isHttps =
    request.headers.get("x-forwarded-proto") === "https" ||
    request.nextUrl.protocol === "https:"

  const response = NextResponse.json({ success: true })
  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 8, // 8 days
    secure: isHttps,
  })

  return response
}
