import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function GET(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }

  const backendRes = await fetch(`${BACKEND_URL}/api/v1/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!backendRes.ok) {
    const error = await backendRes.json().catch(() => ({ detail: "Unauthorized" }))
    return NextResponse.json(error, { status: backendRes.status })
  }

  const user = await backendRes.json()
  return NextResponse.json(user)
}
