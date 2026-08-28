"use client"

import {
  AlertCircle,
  Braces,
  ClipboardCheck,
  LoaderCircle,
  RotateCcw,
  Table2,
} from "lucide-react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"

import { createContractExtraction, loadContractExtraction } from "./api"
import { ContractSourcePane } from "./contract-source-pane"
import { ContractUpload } from "./contract-upload"
import { FieldsJsonPanel } from "./fields-json-panel"
import { StatusBanner } from "./status-banner"
import type { ContractFieldResult } from "./types"
import { useFieldCatalogue } from "./use-field-catalogue"
import { VerificationPanel } from "./verification-panel"

type View = "result" | "verify"

/** The whole `/contract-extraction` route: select & upload, the two-pane result,
 *  and the verification view, with the table one click away.
 *
 *  A `needs_verification` result is a 200 like any other — it lands here with its
 *  row already persisted, and the banner above both panes refuses to be dismissed
 *  until a human has dealt with it.
 */
export function ContractExtractionWorkspace() {
  const searchParams = useSearchParams()
  const requestedId = searchParams.get("extraction")
  const requestedView = searchParams.get("view")

  const {
    catalogue,
    defaultFields,
    loading: catalogueLoading,
    error: catalogueError,
  } = useFieldCatalogue()
  // Starts empty and is seeded from the catalogue's defaults once it loads. The
  // operator is free to empty it again — Extract is simply disabled while it is.
  const [selected, setSelected] = useState<string[]>([])
  const [seeded, setSeeded] = useState(false)
  const [result, setResult] = useState<ContractFieldResult | null>(null)
  const [view, setView] = useState<View>("result")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Seed the picker once, the first time the catalogue arrives. Guarded so a later
  // render never re-adds fields the operator has deliberately moved out.
  useEffect(() => {
    if (seeded || requestedId || defaultFields.length === 0) return
    setSelected(defaultFields)
    setSeeded(true)
  }, [seeded, requestedId, defaultFields])

  // Opened from the records table: load that row straight into the workspace.
  useEffect(() => {
    if (!requestedId) return
    let active = true
    setBusy(true)
    void loadContractExtraction(requestedId)
      .then((loaded) => {
        if (!active) return
        setResult(loaded)
        setSelected(loaded.selected_fields ?? [])
        setSeeded(true)
        setView(requestedView === "verify" ? "verify" : "result")
        setError(null)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(
          caught instanceof Error
            ? caught.message
            : "That extraction could not be loaded.",
        )
      })
      .finally(() => {
        if (active) setBusy(false)
      })
    return () => {
      active = false
    }
  }, [requestedId, requestedView])

  async function extract(file: File) {
    setBusy(true)
    setError(null)
    try {
      const created = await createContractExtraction(file, selected)
      setResult(created)
      // A failed extraction opens on the result, not the form: the operator has to
      // see which requested fields came back blank before doing anything else.
      setView("result")
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The contract could not be extracted.",
      )
    } finally {
      setBusy(false)
    }
  }

  const inlineError = error ?? catalogueError

  return (
    <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            Operator workspace
          </p>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Contract field extraction
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Ten fields, always the same ten keys. A value that cannot be
            grounded in the contract stays blank and is raised for a human — it
            is never guessed.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/contract-extraction/records">
              <Table2 className="size-4" aria-hidden />
              Open table
            </Link>
          </Button>
          {result && (
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setResult(null)
                setError(null)
                setView("result")
              }}
            >
              <RotateCcw className="size-4" aria-hidden />
              Start over
            </Button>
          )}
        </div>
      </header>

      {inlineError && (
        <div
          className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          <span className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {inlineError}
          </span>
          {error && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setError(null)}
            >
              Dismiss
            </Button>
          )}
        </div>
      )}

      {catalogueLoading ? (
        <div
          className="flex min-h-[24rem] items-center justify-center rounded-lg border bg-card"
          role="status"
          aria-live="polite"
        >
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Loading the field schema…
          </p>
        </div>
      ) : result ? (
        <div className="space-y-4">
          <StatusBanner
            result={result}
            catalogue={catalogue}
            onVerify={view === "verify" ? undefined : () => setView("verify")}
          />

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant={view === "result" ? "default" : "outline"}
              aria-pressed={view === "result"}
              onClick={() => setView("result")}
            >
              <Braces className="size-4" aria-hidden />
              Extracted JSON
            </Button>
            <Button
              type="button"
              size="sm"
              variant={view === "verify" ? "default" : "outline"}
              aria-pressed={view === "verify"}
              onClick={() => setView("verify")}
            >
              <ClipboardCheck className="size-4" aria-hidden />
              Verification
            </Button>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <ContractSourcePane
              documentId={result.document_id}
              extractionId={result.extraction_id}
            />
            {view === "verify" ? (
              <VerificationPanel
                result={result}
                catalogue={catalogue}
                onUpdated={setResult}
              />
            ) : (
              <FieldsJsonPanel result={result} catalogue={catalogue} />
            )}
          </div>
        </div>
      ) : (
        <div className="mx-auto max-w-3xl">
          <ContractUpload
            catalogue={catalogue}
            selected={selected}
            onSelectedChange={setSelected}
            busy={busy}
            onExtract={extract}
          />
        </div>
      )}
    </main>
  )
}
