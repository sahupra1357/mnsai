export type DocumentStatus =
  | "queued"
  | "classifying"
  | "extracting"
  | "fallback"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed"
  | "cancelled"

export type PageStatus =
  | "pending"
  | "extracting"
  | "needs_review"
  | "approved"
  | "rejected"
  | "manual_review_required"
  | "failed"

export interface CoordinateSpace {
  width: number
  height: number
  origin: "top-left"
}

export interface BoundingBox {
  left: number
  top: number
  right: number
  bottom: number
}

export interface ExtractedElement {
  element_id: string
  type: string
  text: string
  reviewed_text: string | null
  bounding_box: BoundingBox | null
  coordinate_space: CoordinateSpace | null
  reading_order: number
  confidence: number | null
  confidence_source: string | null
  model_derived: boolean
  source_block_number?: number | null
  source_paragraph_number?: number | null
  source_line_number?: number | null
  source_word_number?: number | null
}

export interface ParserSelection {
  name: string
  version: string
  run_id: string
  rationale: string
}

export interface ExtractionCandidate {
  candidate_id: string
  parser: ParserSelection
  confidence: number | null
  confidence_source: string | null
  quality_passed: boolean
  elements: ExtractedElement[]
  warnings: string[]
  created_at: string
}

export interface QualitySignal {
  name: string
  passed: boolean | null
  value: number | string | boolean | null
  threshold: number | string | boolean | null
  detail: string | null
}

export interface ExtractionAttempt {
  parser: string
  version: string
  run_id: string
  status: string
  confidence: number | null
  quality_signals: QualitySignal[]
  error_code: string | null
  error_message: string | null
  retryable: boolean
  provider: string | null
  model: string | null
  prompt_version: string | null
  started_at: string
  completed_at: string
}

export interface AuditEvent {
  event_id: string
  event_type: string
  actor_id: string | null
  occurred_at: string
  details: Record<string, unknown>
}

export interface AdapterCapability {
  name: string
  version: string | null
  available: boolean
  reason: string | null
  classifications: string[]
}

export interface CapabilityResponse {
  adapters: AdapterCapability[]
  supported_extensions: string[]
  max_upload_bytes: number
  max_pages: number
  retry_limits: Record<string, number>
  storage_provider: string
  execution_backend: string
  modal_enabled: boolean
}

export interface PageResult {
  page_number: number
  page_status: PageStatus
  confidence: number | null
  confidence_source: string | null
  classification: string
  routing_reasons: string[]
  selected_parser: ParserSelection | null
  candidates: ExtractionCandidate[]
  selected_candidate_id: string | null
  attempts: ExtractionAttempt[]
  elements: ExtractedElement[]
  semantic_result?: {
    final_content?: Record<string, unknown>
  } | null
  warnings: string[]
  review: {
    status: "pending" | "in_progress" | "approved" | "rejected"
    reviewer_id: string | null
    reviewed_at: string | null
  }
  audit_events: AuditEvent[]
}

export interface DocumentResult {
  document_id: string
  owner_id: string
  source: {
    source_name: string
    source_sha256: string
    media_type: string
    size_bytes: number
    page_count: number
  }
  status: DocumentStatus
  extraction_fingerprint: string | null
  reused_extraction: boolean
  pages: PageResult[]
  created_at: string
  updated_at: string
}

export interface PagePreview {
  media_type: "image/png"
  width: number
  height: number
  page_number: number
  content_sha256: string
}

export type ReviewAction = "save" | "approve" | "reject"

export interface ReviewElementUpdate {
  element_id: string
  reviewed_text: string
}
