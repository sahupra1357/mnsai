"use client"

import { Braces, Check, Copy, Eye } from "lucide-react"
import { useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"

import {
  effectiveValue,
  fieldValue,
  fieldsJson,
  hasHumanValue,
  isRequested,
  labelFor,
  reasonLabel,
  unresolvedByKey,
} from "./fields"
import type { ContractFieldResult, FieldDefinition } from "./types"

interface FieldsJsonPanelProps {
  result: ContractFieldResult
  catalogue: FieldDefinition[]
}

/** The right-hand pane: the ten-key JSON, read-only.
 *
 *  All ten keys always render, in catalogue order, whatever the operator selected —
 *  the key set is static. A blank value shows as `""`, visibly empty and never
 *  hidden. The two kinds of blank are deliberately not allowed to look alike:
 *  an unselected optional field is dimmed and badged "not selected", while a blank
 *  *requested* field is a failure and is shown in the destructive tone with the
 *  reason it failed on the row.
 */
export function FieldsJsonPanel({ result, catalogue }: FieldsJsonPanelProps) {
  const [copied, setCopied] = useState(false)
  const unresolved = unresolvedByKey(result.unresolved_fields)
  const json = fieldsJson(catalogue, result)

  async function copy() {
    try {
      await navigator.clipboard.writeText(json)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard permission can be denied; the JSON stays selectable on screen.
    }
  }

  return (
    <section
      className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-lg border bg-card"
      aria-labelledby="contract-json-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h2
            id="contract-json-title"
            className="flex items-center gap-2 font-semibold"
          >
            <Braces className="size-4" aria-hidden />
            Extracted fields
          </h2>
          <p className="text-xs text-muted-foreground">
            {catalogue.length} keys, always the same, always in this order ·
            JSON
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ResultDetails result={result} catalogue={catalogue} />
          <Button type="button" variant="outline" onClick={() => void copy()}>
            {copied ? (
              <Check className="size-4" aria-hidden />
            ) : (
              <Copy className="size-4" aria-hidden />
            )}
            {copied ? "Copied" : "Copy JSON"}
          </Button>
        </div>
      </header>

      {/* `role="group"` so the label is actually exposed: aria-label on a bare
          generic element is ignored by assistive tech. */}
      <div
        role="group"
        className="flex-1 overflow-auto p-4"
        aria-label="Extracted contract fields as JSON"
      >
        <div className="font-mono text-sm leading-6">
          <p className="text-muted-foreground">{"{"}</p>
          {catalogue.map((definition, index) => {
            const requested = isRequested(definition, result.selected_fields)
            const value = effectiveValue(result, definition.key)
            const human = hasHumanValue(result, definition.key)
            // A field a human has since filled in is no longer a failure: it keeps
            // its place in the list but drops the destructive tone and reason.
            const failure = human ? undefined : unresolved.get(definition.key)
            const last = index === catalogue.length - 1
            return (
              <div
                key={definition.key}
                data-field={definition.key}
                className={cn(
                  "rounded-sm border-l-2 py-0.5 pl-3 pr-2",
                  failure
                    ? "border-destructive bg-destructive/5"
                    : "border-transparent",
                  !requested && "opacity-60",
                )}
              >
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <span className="whitespace-pre">{"  "}</span>
                  <span
                    className={cn(
                      "text-primary",
                      failure && "text-destructive",
                    )}
                  >
                    &quot;{definition.key}&quot;
                  </span>
                  <span className="text-muted-foreground">:</span>
                  <span
                    className={cn(
                      "break-all",
                      failure && "text-destructive",
                      !value && "text-muted-foreground",
                    )}
                  >
                    &quot;{value}&quot;
                  </span>
                  {!last && <span className="text-muted-foreground">,</span>}
                  {!requested && (
                    <Badge variant="outline" className="ml-1 font-sans">
                      not selected
                    </Badge>
                  )}
                  {failure && (
                    <Badge variant="destructive" className="ml-1 font-sans">
                      not extracted
                    </Badge>
                  )}
                  {human && (
                    <Badge variant="secondary" className="ml-1 font-sans">
                      human verified
                    </Badge>
                  )}
                </div>
                {failure && (
                  <p className="pl-6 font-sans text-xs text-destructive">
                    {labelFor(catalogue, definition.key)}:{" "}
                    {reasonLabel(failure)}
                  </p>
                )}
                {human && (
                  <p className="pl-6 font-sans text-xs text-muted-foreground">
                    Supplied during human verification. The machine value stays
                    blank on the record — see View details.
                  </p>
                )}
                {!requested && (
                  <p className="pl-6 font-sans text-xs text-muted-foreground">
                    {definition.label} was not selected, so it was never
                    extracted.
                  </p>
                )}
              </div>
            )
          })}
          <p className="text-muted-foreground">{"}"}</p>
        </div>
      </div>
    </section>
  )
}

/** Provenance, the selection list, and warnings — everything that is not one of the
 *  ten keys lives behind this, so the pane itself renders `fields` only. */
function ResultDetails({ result, catalogue }: FieldsJsonPanelProps) {
  const provenance = result.field_provenance ?? []
  const warnings = result.warnings ?? []
  const selected = result.selected_fields ?? []
  // Catalogue order, so this reads in the same sequence as the JSON above it.
  const humanKeys = catalogue
    .map((definition) => definition.key)
    .filter((key) => hasHumanValue(result, key))

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button type="button" variant="outline">
          <Eye className="size-4" aria-hidden />
          View details
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Extraction details</DialogTitle>
          <DialogDescription>
            What was requested, where each value came from, and anything the
            extractor refused to guess.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 text-sm">
          <div>
            <h3 className="mb-2 font-semibold">Optional fields requested</h3>
            {selected.length === 0 ? (
              <p className="text-muted-foreground">
                None — the five fixed fields only.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {selected.map((key) => (
                  <Badge key={key} variant="secondary">
                    {labelFor(catalogue, key)}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {humanKeys.length > 0 && (
            <div>
              <h3 className="mb-2 font-semibold">Human verification</h3>
              <p className="mb-2 text-xs text-muted-foreground">
                The JSON shows these values. The machine column is kept exactly
                as extracted and is never overwritten.
              </p>
              <ul className="space-y-2">
                {humanKeys.map((key) => (
                  <li key={key} className="rounded-md border bg-muted/30 p-3">
                    <p className="font-medium">{labelFor(catalogue, key)}</p>
                    <dl className="mt-1 grid gap-x-3 text-xs sm:grid-cols-[7.5rem_1fr]">
                      <dt className="text-muted-foreground">Human value</dt>
                      <dd className="break-all font-mono">
                        &quot;{result.verified_values?.[key]}&quot;
                      </dd>
                      <dt className="text-muted-foreground">Machine value</dt>
                      <dd className="break-all font-mono text-muted-foreground">
                        &quot;{fieldValue(result.fields, key)}&quot;
                      </dd>
                    </dl>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="mb-2 font-semibold">Provenance</h3>
            {provenance.length === 0 ? (
              <p className="text-muted-foreground">
                No grounded value carried provenance.
              </p>
            ) : (
              <ul className="space-y-2">
                {provenance.map((entry) => (
                  <li
                    key={entry.field_key}
                    className="rounded-md border bg-muted/30 p-3"
                  >
                    <p className="font-medium">
                      {labelFor(catalogue, entry.field_key)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Page {entry.page_number} · {entry.grounding_status} ·{" "}
                      {entry.confidence === null ||
                      entry.confidence === undefined
                        ? "confidence unavailable"
                        : `${Math.round(entry.confidence * 100)}% confidence`}
                    </p>
                    <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                      {entry.source_element_ids.join(", ")}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h3 className="mb-2 font-semibold">Warnings</h3>
            {warnings.length === 0 ? (
              <p className="text-muted-foreground">None.</p>
            ) : (
              <ul className="list-inside list-disc space-y-1 text-muted-foreground">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
