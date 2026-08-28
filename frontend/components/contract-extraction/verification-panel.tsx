"use client"

import {
  AlertCircle,
  Ban,
  ClipboardCheck,
  LoaderCircle,
  Save,
  ShieldCheck,
} from "lucide-react"
import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import { verifyContractExtraction } from "./api"
import {
  effectiveValue,
  hasHumanValue,
  isRequested,
  labelFor,
  reasonLabel,
  stillBlankKeys,
  unresolvedByKey,
} from "./fields"
import type {
  ContractFieldResult,
  FieldDefinition,
  VerificationAction,
} from "./types"

interface VerificationPanelProps {
  result: ContractFieldResult
  catalogue: FieldDefinition[]
  onUpdated: (result: ContractFieldResult) => void
}

/** The right pane during verification: everything the human has to fill in, beside
 *  the document so the value can be read straight off the source.
 *
 *  Human input never touches the ten machine columns — it is sent to
 *  `verified_values`, and the machine value stays visible beside it. Approve is
 *  blocked inline while any unresolved field is still blank; the backend refuses the
 *  same call with a 422, whose message is surfaced here rather than swallowed.
 */
export function VerificationPanel({
  result,
  catalogue,
  onUpdated,
}: VerificationPanelProps) {
  const [draft, setDraft] = useState<Record<string, string>>(() => ({
    ...(result.verified_values ?? {}),
  }))
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState<VerificationAction | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)

  const unresolved = result.unresolved_fields ?? []
  const unresolvedMap = unresolvedByKey(unresolved)
  const blocking = stillBlankKeys(result, draft)
  const settled =
    result.extraction_status === "verified" ||
    result.extraction_status === "rejected"

  /** Requested fields the machine did resolve — context only, never editable. */
  const machineFields = useMemo(
    () =>
      catalogue.filter(
        (definition) =>
          isRequested(definition, result.selected_fields) &&
          !unresolvedMap.has(definition.key),
      ),
    [catalogue, result.selected_fields, unresolvedMap],
  )

  function payload(): Record<string, string> {
    const values: Record<string, string> = {}
    for (const entry of unresolved) {
      const typed = draft[entry.field_key]?.trim()
      if (typed) values[entry.field_key] = typed
    }
    return values
  }

  async function submit(action: VerificationAction) {
    setError(null)
    setNotice(null)
    setBlockedMessage(null)

    if (action === "approve" && blocking.length > 0) {
      setBlockedMessage(
        `Fill in every unresolved field before approving. Still blank: ${blocking
          .map((key) => labelFor(catalogue, key))
          .join(", ")}.`,
      )
      return
    }
    if (action === "reject" && !note.trim()) {
      setBlockedMessage("Add a note explaining why the extraction is unusable.")
      return
    }

    setBusy(action)
    try {
      const updated = await verifyContractExtraction(
        result.extraction_id,
        action,
        payload(),
        note.trim() || null,
      )
      onUpdated(updated)
      setNotice(
        action === "save"
          ? "Progress saved. The record still needs verification."
          : action === "approve"
            ? "Approved. The record is now verified."
            : "Rejected. The record is kept for the audit trail.",
      )
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The verification could not be saved.",
      )
    } finally {
      setBusy(null)
    }
  }

  return (
    <section
      className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-lg border bg-card"
      aria-labelledby="contract-verification-title"
    >
      <header className="border-b px-4 py-3">
        <h2
          id="contract-verification-title"
          className="flex items-center gap-2 font-semibold"
        >
          <ClipboardCheck className="size-4" aria-hidden />
          Human verification
        </h2>
        <p className="text-xs text-muted-foreground">
          {unresolved.length} field{unresolved.length === 1 ? "" : "s"} to
          confirm · read the value off the document on the left
        </p>
      </header>

      <div className="flex-1 space-y-6 overflow-y-auto p-4">
        {error && (
          <div
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {error}
          </div>
        )}
        {blockedMessage && (
          <div
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
            role="alert"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {blockedMessage}
          </div>
        )}
        {notice && (
          <div
            className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-sm"
            role="status"
          >
            <ShieldCheck
              className="mt-0.5 size-4 shrink-0 text-primary"
              aria-hidden
            />
            {notice}
          </div>
        )}

        <div className="space-y-4">
          <h3 className="text-sm font-semibold">Fields to fill in</h3>
          {unresolved.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Nothing is outstanding — every requested field was extracted.
            </p>
          ) : (
            unresolved.map((entry) => {
              const inputId = `verify-${entry.field_key}`
              const value = draft[entry.field_key] ?? ""
              const filled = Boolean(value.trim())
              return (
                <div
                  key={entry.field_key}
                  className={cn(
                    "space-y-2 rounded-lg border-l-2 bg-muted/20 p-3",
                    filled ? "border-primary" : "border-destructive",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Label htmlFor={inputId} className="font-medium">
                      {labelFor(catalogue, entry.field_key)}
                    </Label>
                    <Badge
                      variant={filled ? "secondary" : "destructive"}
                      className="text-[0.7rem]"
                    >
                      {filled ? "filled in" : "blank"}
                    </Badge>
                  </div>
                  <p className="text-xs text-destructive">
                    {reasonLabel(entry)}
                  </p>
                  <Input
                    id={inputId}
                    value={value}
                    disabled={settled || busy !== null}
                    placeholder={
                      catalogue.find(
                        (definition) => definition.key === entry.field_key,
                      )?.description ?? "Value read from the document"
                    }
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        [entry.field_key]: event.target.value,
                      }))
                    }
                  />
                </div>
              )
            })
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold">
            Extracted for context (read-only)
          </h3>
          <p className="text-xs text-muted-foreground">
            These are the machine values. They are never overwritten by a human
            correction.
          </p>
          <dl className="divide-y rounded-lg border">
            {machineFields.map((definition) => (
              <div
                key={definition.key}
                className="flex flex-wrap items-baseline justify-between gap-2 px-3 py-2"
              >
                <dt className="text-sm text-muted-foreground">
                  {definition.label}
                </dt>
                <dd className="flex items-center gap-2 font-mono text-sm">
                  {hasHumanValue(result, definition.key) && (
                    <Badge variant="secondary" className="font-sans">
                      human
                    </Badge>
                  )}
                  <span>
                    &quot;{effectiveValue(result, definition.key)}&quot;
                  </span>
                </dd>
              </div>
            ))}
            {machineFields.length === 0 && (
              <p className="px-3 py-2 text-sm text-muted-foreground">
                No requested field was resolved by the extractor.
              </p>
            )}
          </dl>
        </div>

        <div className="space-y-2">
          <Label htmlFor="verify-note">Note</Label>
          <Textarea
            id="verify-note"
            value={note}
            rows={3}
            disabled={settled || busy !== null}
            placeholder="Optional for save and approve, required to reject."
            onChange={(event) => setNote(event.target.value)}
          />
        </div>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t bg-card px-4 py-3">
        <p className="text-xs text-muted-foreground">
          {settled
            ? "This record has been settled by a human."
            : blocking.length > 0
              ? `${blocking.length} field${
                  blocking.length === 1 ? "" : "s"
                } still blank — approve is blocked.`
              : "Every unresolved field has a value. Approve is available."}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={settled || busy !== null}
            onClick={() => void submit("save")}
          >
            {busy === "save" ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Save className="size-4" aria-hidden />
            )}
            Save
          </Button>
          <Button
            type="button"
            variant="destructive"
            disabled={settled || busy !== null}
            onClick={() => void submit("reject")}
          >
            {busy === "reject" ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <Ban className="size-4" aria-hidden />
            )}
            Reject
          </Button>
          {/* Deliberately not `disabled` while fields are blank: clicking must
              explain *why* approve is refused, and a disabled control says
              nothing. The backend refuses the same call with a 422. */}
          <Button
            type="button"
            disabled={settled || busy !== null}
            aria-disabled={blocking.length > 0}
            className={cn(blocking.length > 0 && "opacity-60")}
            onClick={() => void submit("approve")}
          >
            {busy === "approve" ? (
              <LoaderCircle className="size-4 animate-spin" aria-hidden />
            ) : (
              <ShieldCheck className="size-4" aria-hidden />
            )}
            Approve
          </Button>
        </div>
      </footer>
    </section>
  )
}
