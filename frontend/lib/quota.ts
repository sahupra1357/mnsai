/**
 * Client-side handling of the lifetime request quota.
 *
 * The backend refuses a metered call with **402 Payment Required** and a
 * structured body (see `quota_exceeded_detail` in `backend/app/api/deps.py`):
 *
 *   { code: "quota_exceeded", message, limit, used, redirect }
 *
 * Nothing here parses prose — the `code` is what we match on, and `redirect` is
 * where the backend wants the user sent. Two call paths need covering: the
 * generated OpenAPI client (axios) and the hand-written `fetch` API modules for
 * document/contract extraction. Both funnel into `goToSubscription`.
 */

export const QUOTA_EXCEEDED_CODE = "quota_exceeded"
export const SUBSCRIPTION_PATH = "/pricing?reason=quota"

export interface QuotaExceededDetail {
  code: string
  message?: string
  limit?: number
  used?: number
  redirect?: string
}

/** One redirect per page load. Several parallel calls can all come back 402
 *  (a page that fires two requests at once), and each one navigating would
 *  stack history entries the user has to click back through. */
let redirecting = false

function isQuotaDetail(value: unknown): value is QuotaExceededDetail {
  return (
    typeof value === "object" &&
    value !== null &&
    (value as QuotaExceededDetail).code === QUOTA_EXCEEDED_CODE
  )
}

/** Pulls the quota detail out of a FastAPI error body, whatever shape it took. */
export function quotaDetailFrom(body: unknown): QuotaExceededDetail | null {
  if (isQuotaDetail(body)) return body
  if (typeof body === "object" && body !== null) {
    const detail = (body as { detail?: unknown }).detail
    if (isQuotaDetail(detail)) return detail
  }
  return null
}

/** Hard navigation, so it works from plain modules as well as React trees. */
export function goToSubscription(detail?: QuotaExceededDetail | null): void {
  if (typeof window === "undefined" || redirecting) return
  redirecting = true
  window.location.href = detail?.redirect || SUBSCRIPTION_PATH
}

/**
 * For `fetch`-based callers. Redirects and resolves `true` when the response is
 * a quota refusal, leaving the caller free to throw its own error for any other
 * failure. The response is cloned, so the caller can still read the body.
 */
export async function handleQuotaResponse(response: Response): Promise<boolean> {
  if (response.status !== 402) return false
  let detail: QuotaExceededDetail | null = null
  try {
    detail = quotaDetailFrom(await response.clone().json())
  } catch {
    // A 402 without a JSON body still means the quota is spent.
  }
  goToSubscription(detail)
  return true
}
