import { type NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

type Params = Promise<{ path: string[] }>

async function proxy(request: NextRequest, params: { path: string[] }) {
  const token = request.cookies.get("access_token")?.value
  const subpath = params.path.join("/")
  const search = request.nextUrl.search
  const url = `${BACKEND_URL}/${subpath}${search}`

  const headers: Record<string, string> = {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const contentType = request.headers.get("content-type")
  const isFormData = contentType?.includes("multipart/form-data")

  let body: BodyInit | null = null
  if (request.method !== "GET" && request.method !== "HEAD") {
    if (isFormData) {
      body = await request.formData()
    } else {
      body = await request.text()
      if (contentType) headers["Content-Type"] = contentType
    }
  }

  const backendRes = await fetch(url, {
    method: request.method,
    headers,
    body,
  })

  const resHeaders = new Headers()
  for (const header of [
    "content-type",
    "content-disposition",
    "cache-control",
    "etag",
    "x-content-type-options",
  ]) {
    const value = backendRes.headers.get(header)
    if (value) resHeaders.set(header, value)
  }

  return new NextResponse(backendRes.body, {
    status: backendRes.status,
    headers: resHeaders,
  })
}

export async function GET(
  request: NextRequest,
  { params }: { params: Params },
) {
  return proxy(request, await params)
}
export async function POST(
  request: NextRequest,
  { params }: { params: Params },
) {
  return proxy(request, await params)
}
export async function PUT(
  request: NextRequest,
  { params }: { params: Params },
) {
  return proxy(request, await params)
}
export async function DELETE(
  request: NextRequest,
  { params }: { params: Params },
) {
  return proxy(request, await params)
}
export async function PATCH(
  request: NextRequest,
  { params }: { params: Params },
) {
  return proxy(request, await params)
}
