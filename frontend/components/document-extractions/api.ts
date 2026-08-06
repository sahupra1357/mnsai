import type {
  CapabilityResponse,
  DocumentResult,
  PageResult,
  ReviewAction,
  ReviewElementUpdate,
} from "./types"

const API_ROOT = "/api/proxy/api/v1/document-extractions"

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>
  message?: string
}

export class DocumentExtractionApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = "DocumentExtractionApiError"
  }
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) {
      const details = body.detail
        .map((item) => item.msg)
        .filter((item): item is string => Boolean(item))
      if (details.length > 0) return details.join(". ")
    }
    if (body.message) return body.message
  } catch {
    // Some source and proxy failures are intentionally not JSON.
  }
  return `Request failed with status ${response.status}.`
}

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new DocumentExtractionApiError(
      await errorMessage(response),
      response.status,
    )
  }
  return (await response.json()) as T
}

export async function uploadDocument(file: File): Promise<DocumentResult> {
  const formData = new FormData()
  formData.append("file", file)
  return expectJson<DocumentResult>(
    await fetch(API_ROOT, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    }),
  )
}

export async function loadCapabilities(): Promise<CapabilityResponse> {
  return expectJson<CapabilityResponse>(
    await fetch(`${API_ROOT}/capabilities`, {
      credentials: "same-origin",
      cache: "no-store",
    }),
  )
}

export async function loadDocument(documentId: string): Promise<DocumentResult> {
  return expectJson<DocumentResult>(
    await fetch(`${API_ROOT}/${encodeURIComponent(documentId)}`, {
      credentials: "same-origin",
      cache: "no-store",
    }),
  )
}

export async function reviewPage(
  documentId: string,
  pageNumber: number,
  action: ReviewAction,
  elements: ReviewElementUpdate[],
): Promise<PageResult> {
  return expectJson<PageResult>(
    await fetch(
      `${API_ROOT}/${encodeURIComponent(
        documentId,
      )}/pages/${pageNumber}/review`,
      {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, elements }),
      },
    ),
  )
}

export async function reprocessPage(
  documentId: string,
  pageNumber: number,
  parser: string | null,
): Promise<PageResult> {
  return expectJson<PageResult>(
    await fetch(
      `${API_ROOT}/${encodeURIComponent(
        documentId,
      )}/pages/${pageNumber}/reprocess`,
      {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parser,
          reason: parser
            ? `Reviewer requested reprocessing with ${parser} from the validation UI`
            : "Reviewer requested reprocessing with the automatic chain from the validation UI",
        }),
      },
    ),
  )
}

export async function loadPagePreview(
  documentId: string,
  pageNumber: number,
  signal: AbortSignal,
): Promise<Blob> {
  const response = await fetch(
    `${API_ROOT}/${encodeURIComponent(documentId)}/pages/${pageNumber}/preview`,
    { credentials: "same-origin", signal },
  )
  if (!response.ok) {
    throw new DocumentExtractionApiError(
      await errorMessage(response),
      response.status,
    )
  }
  return response.blob()
}

export function sourceDownloadUrl(documentId: string): string {
  return `${API_ROOT}/${encodeURIComponent(documentId)}/source`
}

export function jsonExportUrl(documentId: string): string {
  return `${API_ROOT}/${encodeURIComponent(documentId)}/export`
}
