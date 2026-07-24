/**
 * Server-side lookup for the profile headshot uploaded via User Settings →
 * Profile photo.
 *
 * The hero calls this to decide between the real photo and the initials-ring
 * placeholder, so a missing image never renders as a broken <img>. The bytes
 * themselves are served to the browser through the same-origin proxy at
 * `/api/proxy/...`, stamped with the upload timestamp so replacing the photo
 * busts any cached copy.
 */

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000"

/** Browser-reachable URL for the headshot bytes (same-origin, via the proxy). */
export const PROFILE_IMAGE_URL = "/api/proxy/api/v1/profile/image"

export interface ProfileImageMeta {
  has_image: boolean
  content_type?: string | null
  updated_at?: string | null
}

/**
 * Returns the versioned headshot URL, or null when no photo has been uploaded.
 * Never throws — if the backend is unreachable the hero falls back to initials.
 */
export async function getProfileHeadshotUrl(): Promise<string | null> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/profile/image/meta`, {
      // Request-time, never build-time. A cached/revalidated fetch gets baked
      // into the prerendered homepage during `next build` — where the backend
      // is unreachable — so an uploaded photo would not appear until a
      // revalidation fired, and a stale bake could point at a deleted image.
      cache: "no-store",
    })
    if (!res.ok) return null

    const meta = (await res.json()) as ProfileImageMeta
    if (!meta.has_image) return null

    const version = encodeURIComponent(meta.updated_at ?? "")
    return version ? `${PROFILE_IMAGE_URL}?v=${version}` : PROFILE_IMAGE_URL
  } catch {
    return null
  }
}
