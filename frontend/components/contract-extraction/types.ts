/** Types for the contract field-extraction workspace.
 *
 *  Everything here re-exports the generated OpenAPI client so the ten-key schema
 *  keeps a single source of truth in the backend catalogue. Nothing in this folder
 *  hardcodes a second copy of the field list — it always comes from
 *  `GET /contract-extractions/fields`.
 */

export type {
  ContractFieldRecordRow,
  ContractFieldResult,
  ContractFields,
  ContractFieldsPage,
  ExtractionStatus,
  FieldCatalogueResponse,
  FieldDefinition,
  FieldProvenance,
  UnresolvedField,
  UnresolvedReason,
  VerificationRequest,
} from "@/src/client"

/** What the operator asked a verification call to do. Mirrors the review vocabulary
 *  the existing pipeline already uses. */
export type VerificationAction = "save" | "approve" | "reject"
