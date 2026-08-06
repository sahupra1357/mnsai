"use client"

import {
  Braces,
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  LoaderCircle,
  Redo2,
  Save,
  Upload,
  X,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

import {
  jsonExportUrl,
  loadCapabilities,
  reprocessPage,
  reviewPage,
} from "./api"
import { ExtractionPanel } from "./extraction-panel"
import { JsonExtractionPanel } from "./json-extraction-panel"
import { SourceViewer } from "./source-viewer"
import type {
  AdapterCapability,
  DocumentResult,
  PageResult,
  ReviewAction,
  ReviewElementUpdate,
} from "./types"

interface ReviewWorkspaceProps {
  initialDocument: DocumentResult
  onDocumentChange: (document: DocumentResult) => void
  onStartOver: () => void
}

function draftsForPage(page: PageResult): Record<string, string> {
  return Object.fromEntries(
    page.elements.map((element) => [
      element.element_id,
      element.reviewed_text ?? element.text,
    ]),
  )
}

function pageWithNumber(document: DocumentResult, pageNumber: number) {
  return (
    document.pages.find((page) => page.page_number === pageNumber) ??
    document.pages[0]
  )
}

const PARSER_LABELS: Record<string, string> = {
  tesseract: "Tesseract",
  mistral: "Mistral OCR",
  "mistral-ocr": "Mistral OCR",
  "openai-vision-terra": "GPT-5.6 Terra",
  "openai-vision-sol": "GPT-5.6 Sol",
  docling: "Docling",
  paddleocr: "PaddleOCR",
  "paddleocr-vl": "PaddleOCR-VL",
  mineru: "MinerU",
  marker: "Marker",
}

function parserLabel(capability: AdapterCapability): string {
  return PARSER_LABELS[capability.name] ?? capability.name
}

function supportsPage(
  capability: AdapterCapability,
  classification: string,
): boolean {
  return (
    capability.classifications.length === 0 ||
    capability.classifications.includes(classification)
  )
}

export function ReviewWorkspace({
  initialDocument,
  onDocumentChange,
  onStartOver,
}: ReviewWorkspaceProps) {
  const [document, setDocument] = useState(initialDocument)
  const [pageNumber, setPageNumber] = useState(
    initialDocument.pages[0]?.page_number ?? 1,
  )
  const page = pageWithNumber(document, pageNumber)
  const [drafts, setDrafts] = useState<Record<string, string>>(() =>
    page ? draftsForPage(page) : {},
  )
  const [savedDrafts, setSavedDrafts] = useState<Record<string, string>>(() =>
    page ? draftsForPage(page) : {},
  )
  const [selectedElementId, setSelectedElementId] = useState<string | null>(
    page?.elements[0]?.element_id ?? null,
  )
  const [busyAction, setBusyAction] = useState<
    ReviewAction | "reprocess" | null
  >(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showPageDetails, setShowPageDetails] = useState(false)
  const [capabilities, setCapabilities] = useState<AdapterCapability[]>([])
  const [capabilitiesLoading, setCapabilitiesLoading] = useState(true)
  const [capabilitiesError, setCapabilitiesError] = useState<string | null>(
    null,
  )
  const [requestedParser, setRequestedParser] = useState("")

  const dirty = useMemo(
    () => JSON.stringify(drafts) !== JSON.stringify(savedDrafts),
    [drafts, savedDrafts],
  )

  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ""
    }
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [dirty])

  useEffect(() => {
    let active = true
    void loadCapabilities()
      .then((response) => {
        if (!active) return
        setCapabilities(response.adapters)
        setCapabilitiesError(null)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setCapabilitiesError(
          caught instanceof Error
            ? caught.message
            : "Parser availability could not be loaded.",
        )
      })
      .finally(() => {
        if (active) setCapabilitiesLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const replacePage = useCallback(
    (nextPage: PageResult) => {
      const nextDocument = {
        ...document,
        status:
          nextPage.page_status === "extracting"
            ? ("extracting" as const)
            : document.status,
        pages: document.pages.map((existing) =>
          existing.page_number === nextPage.page_number ? nextPage : existing,
        ),
        updated_at: new Date().toISOString(),
      }
      setDocument(nextDocument)
      onDocumentChange(nextDocument)
      const nextDrafts = draftsForPage(nextPage)
      setDrafts(nextDrafts)
      setSavedDrafts(nextDrafts)
      setSelectedElementId(nextPage.elements[0]?.element_id ?? null)
    },
    [document, onDocumentChange],
  )

  const navigate = useCallback(
    (nextPageNumber: number) => {
      const nextPage = pageWithNumber(document, nextPageNumber)
      if (!nextPage || nextPage.page_number === page?.page_number) return
      if (
        dirty &&
        !window.confirm(
          "You have unsaved corrections. Leave this page and discard them?",
        )
      ) {
        return
      }
      const nextDrafts = draftsForPage(nextPage)
      setPageNumber(nextPage.page_number)
      setDrafts(nextDrafts)
      setSavedDrafts(nextDrafts)
      setSelectedElementId(nextPage.elements[0]?.element_id ?? null)
      setError(null)
      setMessage(null)
    },
    [dirty, document, page?.page_number],
  )

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (!event.altKey || event.target instanceof HTMLTextAreaElement) return
      if (event.key === "ArrowLeft") {
        event.preventDefault()
        navigate(pageNumber - 1)
      } else if (event.key === "ArrowRight") {
        event.preventDefault()
        navigate(pageNumber + 1)
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [navigate, pageNumber])

  if (!page) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <p className="font-medium">No pages are available to review.</p>
        <p className="mt-2 text-sm text-muted-foreground">
          The document was accepted but no normalized page results were
          returned.
        </p>
        <Button className="mt-4" variant="outline" onClick={onStartOver}>
          Upload another document
        </Button>
      </div>
    )
  }

  const pageIndex = document.pages.findIndex(
    (candidate) => candidate.page_number === page.page_number,
  )
  const reviewElements: ReviewElementUpdate[] = page.elements.map(
    (element) => ({
      element_id: element.element_id,
      reviewed_text: drafts[element.element_id] ?? element.text,
    }),
  )

  async function submitReview(action: ReviewAction) {
    setBusyAction(action)
    setError(null)
    setMessage(null)
    try {
      const nextPage = await reviewPage(
        document.document_id,
        page.page_number,
        action,
        reviewElements,
      )
      replacePage(nextPage)
      setMessage(
        action === "save"
          ? "Corrections saved."
          : action === "approve"
            ? "Page approved."
            : "Page rejected.",
      )
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The review could not be saved.",
      )
    } finally {
      setBusyAction(null)
    }
  }

  async function reprocess() {
    const parser = requestedParser || null
    const requestedLabel = parser
      ? parserLabel(
          capabilities.find((capability) => capability.name === parser) ?? {
            name: parser,
            version: null,
            available: true,
            reason: null,
            classifications: [],
          },
        )
      : "Automatic chain"
    if (
      dirty &&
      !window.confirm(
        "Reprocessing will discard unsaved corrections. Continue?",
      )
    ) {
      return
    }
    setBusyAction("reprocess")
    setError(null)
    setMessage(null)
    try {
      const nextPage = await reprocessPage(
        document.document_id,
        page.page_number,
        parser,
      )
      replacePage(nextPage)
      if (nextPage.page_status === "extracting") {
        setMessage(`${requestedLabel} was queued for asynchronous Modal processing.`)
        return
      }
      const selected = nextPage.selected_parser?.name
      const selectedCapability = capabilities.find(
        (capability) => capability.name === selected,
      )
      const selectedLabel = selectedCapability
        ? parserLabel(selectedCapability)
        : (selected ?? "no parser")
      const requestedAttempt = parser
        ? [...nextPage.attempts]
            .reverse()
            .find((attempt) => attempt.parser === parser)
        : null
      const fallbackReason =
        requestedAttempt?.error_message ??
        (requestedAttempt && requestedAttempt.status !== "succeeded"
          ? requestedAttempt.status.replaceAll("_", " ")
          : null)
      setMessage(
        parser && selected !== parser
          ? `${requestedLabel} did not produce the selected result${
              fallbackReason ? `: ${fallbackReason}` : ""
            }. The fallback chain selected ${selectedLabel}.`
          : `${requestedLabel} was requested. ${selectedLabel} produced the selected result.`,
      )
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The page could not be reprocessed.",
      )
    } finally {
      setBusyAction(null)
    }
  }

  function startOver() {
    if (
      !dirty ||
      window.confirm(
        "You have unsaved corrections. Upload another document and discard them?",
      )
    ) {
      onStartOver()
    }
  }

  return (
    <div className="space-y-4">
      <header className="flex flex-col gap-4 rounded-lg border bg-card p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-semibold">
              {document.source.source_name}
            </h1>
            <Badge variant="secondary">
              {document.status.replaceAll("_", " ")}
            </Badge>
            {document.reused_extraction && (
              <Badge variant="outline">Loaded from saved extraction</Badge>
            )}
            {dirty && <Badge variant="outline">Unsaved changes</Badge>}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {document.source.media_type} ·{" "}
            {(document.source.size_bytes / 1024).toLocaleString(undefined, {
              maximumFractionDigits: 1,
            })}{" "}
            KB · SHA-256 {document.source.source_sha256.slice(0, 12)}…
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild type="button" variant="outline">
            <a href={jsonExportUrl(document.document_id)} download>
              <Download aria-hidden />
              Download JSON
            </a>
          </Button>
          {showPageDetails && (
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowPageDetails(false)}
            >
              <Braces aria-hidden />
              View JSON
            </Button>
          )}
          <Button type="button" variant="outline" onClick={startOver}>
            <Upload aria-hidden />
            New document
          </Button>
        </div>
      </header>

      <nav
        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2"
        aria-label="Document page navigation"
      >
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={pageIndex <= 0}
          onClick={() => navigate(document.pages[pageIndex - 1].page_number)}
        >
          <ChevronLeft aria-hidden />
          Previous
        </Button>
        <div className="flex items-center gap-2">
          <label htmlFor="page-select" className="text-sm font-medium">
            Page
          </label>
          <select
            id="page-select"
            className="h-9 rounded-md border bg-background px-3 text-sm"
            value={page.page_number}
            onChange={(event) => navigate(Number(event.target.value))}
          >
            {document.pages.map((candidate) => (
              <option key={candidate.page_number} value={candidate.page_number}>
                {candidate.page_number}
              </option>
            ))}
          </select>
          <span className="text-sm text-muted-foreground">
            of {document.source.page_count}
          </span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={pageIndex >= document.pages.length - 1}
          onClick={() => navigate(document.pages[pageIndex + 1].page_number)}
        >
          Next
          <ChevronRight aria-hidden />
        </Button>
      </nav>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <SourceViewer
          key={page.page_number}
          documentId={document.document_id}
          mediaType={document.source.media_type}
          page={page}
          selectedElementId={selectedElementId}
          onSelectElement={setSelectedElementId}
        />
        {showPageDetails ? (
          <ExtractionPanel
            page={page}
            drafts={drafts}
            selectedElementId={selectedElementId}
            disabled={busyAction !== null}
            onSelectElement={setSelectedElementId}
            onChange={(elementId, value) => {
              setDrafts((current) => ({ ...current, [elementId]: value }))
              setMessage(null)
            }}
          />
        ) : (
          <JsonExtractionPanel
            page={page}
            onViewDetails={() => setShowPageDetails(true)}
          />
        )}
      </div>

      {(message || error) && (
        <div
          className={
            error
              ? "rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
              : "rounded-md border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-800 dark:text-emerald-300"
          }
          role={error ? "alert" : "status"}
        >
          {error ?? message}
        </div>
      )}

      {showPageDetails && (
        <footer className="sticky bottom-3 z-20 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background/95 p-3 shadow-lg backdrop-blur">
          <div className="flex flex-wrap items-end gap-2">
            <div className="space-y-1">
              <label
                htmlFor="reprocess-parser"
                className="block text-xs font-medium text-muted-foreground"
              >
                Reprocess with
              </label>
              <select
                id="reprocess-parser"
                className="h-9 max-w-64 rounded-md border bg-background px-3 text-sm"
                value={requestedParser}
                disabled={busyAction !== null || capabilitiesLoading}
                onChange={(event) => setRequestedParser(event.target.value)}
              >
                <option value="">Automatic chain (recommended)</option>
                {capabilities.map((capability) => (
                  <option
                    key={capability.name}
                    value={capability.name}
                    disabled={!capability.available}
                  >
                    {parserLabel(capability)}
                    {capability.version ? ` · ${capability.version}` : ""}
                    {!capability.available
                      ? " · unavailable"
                      : !supportsPage(capability, page.classification)
                        ? " · operator override"
                        : ""}
                  </option>
                ))}
              </select>
            </div>
            <Button
              type="button"
              variant="outline"
              disabled={busyAction !== null || capabilitiesLoading}
              onClick={() => void reprocess()}
            >
              {busyAction === "reprocess" ? (
                <LoaderCircle className="animate-spin" aria-hidden />
              ) : (
                <Redo2 aria-hidden />
              )}
              Reprocess
            </Button>
            {capabilitiesError && (
              <p className="max-w-72 text-xs text-destructive" role="alert">
                {capabilitiesError} Automatic routing remains available.
              </p>
            )}
            {!capabilitiesError &&
              capabilities.some((capability) => !capability.available) && (
                <details className="max-w-80 text-xs text-muted-foreground">
                  <summary className="cursor-pointer">
                    Why are some parsers unavailable?
                  </summary>
                  <ul className="mt-1 space-y-1">
                    {capabilities
                      .filter((capability) => !capability.available)
                      .map((capability) => (
                        <li key={capability.name}>
                          <span className="font-medium">
                            {parserLabel(capability)}:
                          </span>{" "}
                          {capability.reason ?? "Not configured"}
                        </li>
                      ))}
                  </ul>
                </details>
              )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={busyAction !== null}
              onClick={() => void submitReview("save")}
            >
              {busyAction === "save" ? (
                <LoaderCircle className="animate-spin" aria-hidden />
              ) : (
                <Save aria-hidden />
              )}
              Save
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={busyAction !== null}
              onClick={() => void submitReview("reject")}
            >
              {busyAction === "reject" ? (
                <LoaderCircle className="animate-spin" aria-hidden />
              ) : (
                <X aria-hidden />
              )}
              Reject
            </Button>
            <Button
              type="button"
              disabled={busyAction !== null}
              onClick={() => void submitReview("approve")}
            >
              {busyAction === "approve" ? (
                <LoaderCircle className="animate-spin" aria-hidden />
              ) : (
                <Check aria-hidden />
              )}
              Approve
            </Button>
          </div>
        </footer>
      )}

      <p className="text-center text-xs text-muted-foreground">
        Keyboard: Alt + Left/Right Arrow changes pages. Source text is
        immutable; only reviewed values are changed.
      </p>
    </div>
  )
}
