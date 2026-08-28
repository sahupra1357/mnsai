import type {
  ContractFieldResult,
  ContractFieldsPage,
  ExtractionStatus,
  FieldCatalogueResponse,
  VerificationAction,
} from "./types"

/** Browser calls go through the Next.js proxy, which attaches the HttpOnly cookie
 *  as a bearer token server-side. No token ever reaches client storage. */
const API_ROOT = "/api/proxy/api/v1/contract-extractions"

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>
  message?: string
}

export class ContractExtractionApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = "ContractExtractionApiError"
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
    // Upload and source failures are intentionally not always JSON.
  }
  return `Request failed with status ${response.status}.`
}

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new ContractExtractionApiError(
      await errorMessage(response),
      response.status,
    )
  }
  return (await response.json()) as T
}

/** The ten-field schema. The UI renders whatever this returns, in this order. */
export async function loadFieldCatalogue(): Promise<FieldCatalogueResponse> {
  return expectJson<FieldCatalogueResponse>(
    await fetch(`${API_ROOT}/fields`, {
      credentials: "same-origin",
      cache: "no-store",
    }),
  )
}

/** Upload a contract with the operator's optional-field selection.
 *
 *  `selectedOptionalFields` may be empty: the five fixed fields are always
 *  extracted, so an empty selection is a valid request, not an error. */
export async function createContractExtraction(
  file: File,
  selectedOptionalFields: string[],
): Promise<ContractFieldResult> {
  const formData = new FormData()
  formData.append("file", file)
  for (const key of selectedOptionalFields) {
    formData.append("selected_fields", key)
  }
  return expectJson<ContractFieldResult>(
    await fetch(API_ROOT, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    }),
  )
}

export async function loadContractExtraction(
  extractionId: string,
): Promise<ContractFieldResult> {
  return expectJson<ContractFieldResult>(
    await fetch(`${API_ROOT}/${encodeURIComponent(extractionId)}`, {
      credentials: "same-origin",
      cache: "no-store",
    }),
  )
}

/** Save, approve, or reject a human verification.
 *
 *  `values` carries requested keys only; the backend answers 422 for anything else
 *  and for an `approve` that would leave an unresolved field blank. Both messages
 *  are surfaced inline by the caller. */
export async function verifyContractExtraction(
  extractionId: string,
  action: VerificationAction,
  values: Record<string, string>,
  note?: string | null,
): Promise<ContractFieldResult> {
  return expectJson<ContractFieldResult>(
    await fetch(`${API_ROOT}/${encodeURIComponent(extractionId)}/verify`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, values, note: note ?? null }),
    }),
  )
}

export async function listContractExtractions(options: {
  extractionStatus?: ExtractionStatus | null
  skip?: number
  limit?: number
}): Promise<ContractFieldsPage> {
  const params = new URLSearchParams()
  if (options.extractionStatus) {
    params.set("extraction_status", options.extractionStatus)
  }
  params.set("skip", String(options.skip ?? 0))
  params.set("limit", String(options.limit ?? 25))
  return expectJson<ContractFieldsPage>(
    await fetch(`${API_ROOT}/records?${params.toString()}`, {
      credentials: "same-origin",
      cache: "no-store",
    }),
  )
}

/** The stored source document, for download when the page preview is unavailable. */
export function contractSourceUrl(extractionId: string): string {
  return `${API_ROOT}/${encodeURIComponent(extractionId)}/source`
}
