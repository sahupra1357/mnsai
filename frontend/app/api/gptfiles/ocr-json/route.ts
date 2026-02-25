import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

export async function POST(request: NextRequest) {
  const token = request.cookies.get("access_token")?.value

  if (!token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 })
  }

  const formData = await request.formData()

  const backendRes = await fetch(`${BACKEND_URL}/api/v1/gptfiles/ocr-json`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  })

  const data = await backendRes.json().catch(() => ({ detail: "Unknown error from backend" }))
  return NextResponse.json(data, { status: backendRes.status })
}
