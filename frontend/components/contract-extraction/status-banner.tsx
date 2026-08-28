"use client"

import { AlertTriangle, Ban, CheckCircle2, ShieldCheck } from "lucide-react"

import { Button } from "@/components/ui/button"

import { labelFor } from "./fields"
import type { ContractFieldResult, FieldDefinition } from "./types"

interface StatusBannerProps {
  result: ContractFieldResult
  catalogue: FieldDefinition[]
  /** Omitted while the verification view is already open. */
  onVerify?: () => void
}

/** The outcome of the extraction, stated above both panes.
 *
 *  `needs_verification` is the failure state: one blank requested field is enough.
 *  That banner is deliberately not dismissible — a failure must never be silently
 *  scrolled past — and it names the count and the exact keys that failed.
 */
export function StatusBanner({
  result,
  catalogue,
  onVerify,
}: StatusBannerProps) {
  const status = result.extraction_status
  const unresolved = result.unresolved_fields ?? []

  if (status === "needs_verification") {
    const labels = unresolved.map((entry) =>
      labelFor(catalogue, entry.field_key),
    )
    return (
      <div
        role="alert"
        className="flex flex-col gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-destructive sm:flex-row sm:items-center sm:justify-between"
      >
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden />
          <div className="space-y-1">
            <p className="font-semibold">
              {unresolved.length} requested field
              {unresolved.length === 1 ? "" : "s"} could not be extracted —
              human verification required
            </p>
            <p className="text-sm">
              Blank: {labels.join(", ")}. The record is saved and waiting for a
              human; nothing was guessed to fill the gap.
            </p>
          </div>
        </div>
        {onVerify && (
          <Button
            type="button"
            variant="destructive"
            className="shrink-0"
            onClick={onVerify}
          >
            Verify now
          </Button>
        )}
      </div>
    )
  }

  if (status === "verified") {
    return (
      <div
        role="status"
        className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-foreground"
      >
        <ShieldCheck className="size-4 shrink-0 text-primary" aria-hidden />
        Verified by a human. Corrections are stored separately — the extracted
        columns are unchanged.
      </div>
    )
  }

  if (status === "rejected") {
    return (
      <div
        role="status"
        className="flex items-center gap-2 rounded-lg border bg-muted/40 px-4 py-3 text-sm text-muted-foreground"
      >
        <Ban className="size-4 shrink-0" aria-hidden />
        Rejected by a reviewer. The record is kept for the audit trail.
      </div>
    )
  }

  return (
    <div
      role="status"
      className="flex items-center gap-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm text-foreground"
    >
      <CheckCircle2 className="size-4 shrink-0 text-primary" aria-hidden />
      Every requested field was extracted and grounded in the document. No human
      action needed.
    </div>
  )
}
