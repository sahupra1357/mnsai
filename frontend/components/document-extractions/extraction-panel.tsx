"use client"

import { AlertTriangle, Bot, CheckCircle2, History } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

import type { PageResult } from "./types"

interface ExtractionPanelProps {
  page: PageResult
  drafts: Record<string, string>
  selectedElementId: string | null
  disabled: boolean
  onChange: (elementId: string, value: string) => void
  onSelectElement: (elementId: string) => void
}

function confidenceLabel(confidence: number | null) {
  return confidence === null
    ? "Not supplied"
    : `${Math.round(confidence * 100)}%`
}

function formatDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

export function ExtractionPanel({
  page,
  drafts,
  selectedElementId,
  disabled,
  onChange,
  onSelectElement,
}: ExtractionPanelProps) {
  return (
    <section
      className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-lg border bg-card"
      aria-labelledby="extraction-panel-title"
    >
      <header className="border-b px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 id="extraction-panel-title" className="font-semibold">
              Extracted result
            </h2>
            <p className="text-xs text-muted-foreground">
              Corrections are stored separately from parser output.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge
              variant="outline"
              title={page.confidence_source ?? "No page confidence source"}
            >
              Page confidence: {confidenceLabel(page.confidence)}
            </Badge>
            <Badge variant="outline">{page.classification}</Badge>
            <Badge
              variant={
                page.page_status === "failed" ||
                page.page_status === "manual_review_required"
                  ? "destructive"
                  : "secondary"
              }
            >
              {page.page_status.replaceAll("_", " ")}
            </Badge>
          </div>
        </div>
        {page.selected_parser && (
          <div className="mt-3 rounded-md bg-muted/60 p-3 text-xs">
            <span className="font-semibold">
              {page.selected_parser.name} {page.selected_parser.version}
            </span>
            <span className="text-muted-foreground">
              {" "}
              · {page.selected_parser.rationale}
            </span>
          </div>
        )}
      </header>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {page.warnings.length > 0 && (
          <div
            className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3"
            role="status"
          >
            <p className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="size-4 text-amber-600" aria-hidden />
              {page.warnings.length} extraction warning
              {page.warnings.length === 1 ? "" : "s"}
            </p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
              {page.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        )}

        {page.elements.length === 0 && (
          <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
            No extracted elements are available for this page. Inspect the
            attempt history or request reprocessing.
          </div>
        )}

        {page.elements.map((element) => {
          const selected = element.element_id === selectedElementId
          return (
            <article
              key={element.element_id}
              className={cn(
                "rounded-lg border p-3 transition-colors",
                selected &&
                  "border-primary bg-primary/5 ring-1 ring-primary/30",
              )}
              onFocusCapture={() => onSelectElement(element.element_id)}
            >
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{element.type}</Badge>
                  <span className="text-xs text-muted-foreground">
                    Order {element.reading_order + 1}
                  </span>
                  {element.model_derived && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Bot className="size-3" aria-hidden />
                      Model-derived
                    </span>
                  )}
                </div>
                <span
                  className="text-xs text-muted-foreground"
                  title={element.confidence_source ?? "No confidence source"}
                >
                  Confidence: {confidenceLabel(element.confidence)}
                </span>
              </div>
              <div className="rounded bg-muted/50 p-2 text-xs text-muted-foreground">
                <span className="sr-only">Original parser output: </span>
                {element.text || "No source text returned"}
              </div>
              <label
                className="mt-3 block text-xs font-medium"
                htmlFor={`reviewed-${element.element_id}`}
              >
                Reviewed text
              </label>
              <Textarea
                id={`reviewed-${element.element_id}`}
                className="mt-1 min-h-24 resize-y"
                value={drafts[element.element_id] ?? ""}
                disabled={disabled}
                onChange={(event) =>
                  onChange(element.element_id, event.target.value)
                }
              />
            </article>
          )
        })}

        <details className="rounded-lg border">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-3 text-sm font-medium">
            <History className="size-4" aria-hidden />
            Parser and fallback history ({page.attempts.length})
          </summary>
          <div className="space-y-2 border-t p-3">
            {page.attempts.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No parser attempts were recorded.
              </p>
            )}
            {page.attempts.map((attempt) => (
              <div
                key={attempt.run_id}
                className="rounded bg-muted/50 p-3 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold">
                    {attempt.parser} {attempt.version}
                  </span>
                  <span
                    className={cn(
                      "flex items-center gap-1",
                      attempt.status === "succeeded"
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-muted-foreground",
                    )}
                  >
                    {attempt.status === "succeeded" && (
                      <CheckCircle2 className="size-3" aria-hidden />
                    )}
                    {attempt.status.replaceAll("_", " ")}
                  </span>
                </div>
                <p className="mt-1 text-muted-foreground">
                  {formatDate(attempt.started_at)} · Confidence{" "}
                  {confidenceLabel(attempt.confidence)}
                </p>
                {attempt.error_message && (
                  <p className="mt-1 text-destructive">
                    {attempt.error_code ? `${attempt.error_code}: ` : ""}
                    {attempt.error_message}
                  </p>
                )}
              </div>
            ))}
          </div>
        </details>

        <details className="rounded-lg border">
          <summary className="cursor-pointer px-3 py-3 text-sm font-medium">
            Audit history ({page.audit_events.length})
          </summary>
          <ol className="space-y-2 border-t p-3">
            {page.audit_events.length === 0 && (
              <li className="text-xs text-muted-foreground">
                No review events have been recorded.
              </li>
            )}
            {page.audit_events.map((event) => (
              <li key={event.event_id} className="text-xs">
                <span className="font-medium">
                  {event.event_type.replaceAll("_", " ")}
                </span>
                <span className="text-muted-foreground">
                  {" "}
                  · {formatDate(event.occurred_at)}
                </span>
              </li>
            ))}
          </ol>
        </details>
      </div>
    </section>
  )
}
