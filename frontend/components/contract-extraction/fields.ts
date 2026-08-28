import type {
  ContractFieldRecordRow,
  ContractFieldResult,
  ContractFields,
  ExtractionStatus,
  FieldDefinition,
  UnresolvedField,
  UnresolvedReason,
} from "./types"

/** Read one of the ten keys. The generated type marks every value optional because
 *  the backend defaults it to `""`; on the wire the key is always present. Missing
 *  and blank both mean the same thing here — blank — and never `null`. */
export function fieldValue(
  fields: ContractFields | undefined,
  key: string,
): string {
  if (!fields) return ""
  return (fields as Record<string, string | undefined>)[key] ?? ""
}

/** Requested = exactly what the operator selected. Nothing is implicit.
 *
 *  This distinction is the whole point of `selected_fields`: a blank in a requested
 *  field is a failure, a blank in an unselected field is the expected outcome and
 *  must never be shown as one. Every one of the ten fields can be unselected — there
 *  is no field that is requested by default at this layer. */
export function isRequested(
  definition: FieldDefinition,
  selectedFields: string[] | undefined,
): boolean {
  return (selectedFields ?? []).includes(definition.key)
}

/** The number shown beside the picker: however many fields are on the selected side. */
export function requestedCount(
  _catalogue: FieldDefinition[],
  selectedFields: string[],
): number {
  return selectedFields.length
}

/** The human's value wins for display; the machine column is never overwritten, so
 *  both halves stay available and the UI can mark which cells a human supplied. */
export function effectiveValue(
  record: ContractFieldResult | ContractFieldRecordRow,
  key: string,
): string {
  const verified = record.verified_values?.[key]?.trim()
  if (verified) return verified
  return fieldValue(record.fields, key)
}

export function hasHumanValue(
  record: ContractFieldResult | ContractFieldRecordRow,
  key: string,
): boolean {
  return Boolean(record.verified_values?.[key]?.trim())
}

export function unresolvedByKey(
  unresolved: UnresolvedField[] | undefined,
): Map<string, UnresolvedField> {
  return new Map((unresolved ?? []).map((entry) => [entry.field_key, entry]))
}

/** Why a requested field came back blank. Never a generic "failed". */
export const UNRESOLVED_REASON_LABEL: Record<UnresolvedReason, string> = {
  not_found: "Not found in the document",
  ungrounded: "Could not be grounded in the source",
  normalization_failed: "Could not be normalized to the required format",
  provider_unavailable: "Extraction provider unavailable",
}

export function reasonLabel(entry: UnresolvedField | undefined): string {
  if (!entry) return ""
  const label = UNRESOLVED_REASON_LABEL[entry.reason] ?? entry.reason
  return entry.detail ? `${label} — “${entry.detail}”` : label
}

export const STATUS_LABEL: Record<ExtractionStatus, string> = {
  complete: "Complete",
  needs_verification: "Needs verification",
  verified: "Verified",
  rejected: "Rejected",
}

export function statusBadgeVariant(
  status: ExtractionStatus,
): "default" | "secondary" | "destructive" | "outline" {
  if (status === "needs_verification") return "destructive"
  if (status === "verified") return "default"
  if (status === "rejected") return "outline"
  return "secondary"
}

/** The ten-key payload, in catalogue order.
 *
 *  Every key is always present and every value is a string — a field that was not
 *  selected, not found, or not groundable is `""`. This is what the copy button puts
 *  on the clipboard.
 *
 *  Values are *effective*: once a human has verified a blank field, this carries the
 *  value they supplied. The machine column it shadows is never overwritten and stays
 *  visible under "View details", so the JSON reads as the operator's answer while the
 *  provenance of every value remains recoverable. */
export function fieldsJson(
  catalogue: FieldDefinition[],
  record: ContractFieldResult | ContractFieldRecordRow,
): string {
  const ordered: Record<string, string> = {}
  for (const definition of catalogue) {
    ordered[definition.key] = effectiveValue(record, definition.key)
  }
  return JSON.stringify(ordered, null, 2)
}

/** Unresolved keys whose effective value is still blank once the human's draft
 *  edits are taken into account. Approve stays blocked while this is non-empty —
 *  the backend enforces the same rule with a 422. */
export function stillBlankKeys(
  record: ContractFieldResult,
  draft: Record<string, string>,
): string[] {
  return (record.unresolved_fields ?? [])
    .filter((entry) => {
      const typed = draft[entry.field_key]?.trim()
      if (typed) return false
      return !effectiveValue(record, entry.field_key).trim()
    })
    .map((entry) => entry.field_key)
}

export function labelFor(catalogue: FieldDefinition[], key: string): string {
  return catalogue.find((definition) => definition.key === key)?.label ?? key
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return "—"
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString()
}
