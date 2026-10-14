import { cookies } from "next/headers"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

type ServerUser = { id: string; email: string; is_superuser: boolean }

/** The signed-in user, verified by the backend — for server components that
 *  must decide access before rendering anything. Null when signed out or the
 *  token is rejected. Reading cookies makes the calling route dynamic. */
export async function getServerUser(): Promise<ServerUser | null> {
  const token = (await cookies()).get("access_token")?.value
  if (!token) return null
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
    return res.ok ? ((await res.json()) as ServerUser) : null
  } catch {
    return null
  }
}
