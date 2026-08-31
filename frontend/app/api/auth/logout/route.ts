import { NextResponse } from "next/server"

export async function POST() {
  const response = NextResponse.json(
    { success: true },
    { headers: { "Cache-Control": "private, no-store, max-age=0, must-revalidate" } },
  )
  response.cookies.set("access_token", "", {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  })
  return response
}
