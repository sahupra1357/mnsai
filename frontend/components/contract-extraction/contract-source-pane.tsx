"use client"

import {
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Download,
  LoaderCircle,
} from "lucide-react"
import { useEffect, useState } from "react"

import { loadDocument } from "@/components/document-extractions/api"
import { SourceViewer } from "@/components/document-extractions/source-viewer"
import type { DocumentResult } from "@/components/document-extractions/types"
import { Button } from "@/components/ui/button"

import { contractSourceUrl } from "./api"

interface ContractSourcePaneProps {
  /** The `document_extraction` row this contract extraction was derived from. */
  documentId: string
  /** Used only for the download link, which is served owner-scoped by the
   *  contract-extraction route. */
  extractionId: string
}

/** The left pane: the contract itself.
 *
 *  The viewer is the existing `SourceViewer`, imported as-is — this feature reads
 *  what that pipeline produced and adds nothing to how a page is rendered. All this
 *  wrapper does is fetch the document record, page through it, and offer the stored
 *  source for download from the contract-extraction endpoint.
 */
export function ContractSourcePane({
  documentId,
  extractionId,
}: ContractSourcePaneProps) {
  const [document, setDocument] = useState<DocumentResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [selectedElementId, setSelectedElementId] = useState<string | null>(
    null,
  )

  useEffect(() => {
    let active = true
    setDocument(null)
    setError(null)
    setPageNumber(1)
    void loadDocument(documentId)
      .then((loaded) => {
        if (active) setDocument(loaded)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(
          caught instanceof Error
            ? caught.message
            : "The source document could not be loaded.",
        )
      })
    return () => {
      active = false
    }
  }, [documentId])

  if (error) {
    return (
      <section
        className="flex min-h-[34rem] min-w-0 flex-col items-center justify-center gap-4 rounded-lg border bg-muted/20 p-8 text-center"
        aria-label="Original contract"
      >
        <div
          className="flex items-start gap-2 text-sm text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          {error}
        </div>
        <Button asChild variant="outline">
          <a href={contractSourceUrl(extractionId)} download>
            <Download className="size-4" aria-hidden />
            Download source
          </a>
        </Button>
      </section>
    )
  }

  if (!document) {
    return (
      <section
        className="flex min-h-[34rem] min-w-0 items-center justify-center rounded-lg border bg-muted/20"
        aria-label="Original contract"
        aria-busy="true"
      >
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" aria-hidden />
          Loading the contract…
        </p>
      </section>
    )
  }

  const page =
    document.pages.find((item) => item.page_number === pageNumber) ??
    document.pages[0]

  if (!page) {
    return (
      <section
        className="flex min-h-[34rem] min-w-0 items-center justify-center rounded-lg border bg-muted/20 p-8 text-center"
        aria-label="Original contract"
      >
        <p className="text-sm text-muted-foreground">
          This document has no rendered pages.
        </p>
      </section>
    )
  }

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <SourceViewer
        documentId={document.document_id}
        mediaType={document.source.media_type}
        page={page}
        selectedElementId={selectedElementId}
        onSelectElement={setSelectedElementId}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-label="Previous page"
            disabled={page.page_number <= 1}
            onClick={() => {
              setPageNumber(page.page_number - 1)
              setSelectedElementId(null)
            }}
          >
            <ChevronLeft className="size-4" aria-hidden />
          </Button>
          <span className="px-2 text-xs tabular-nums text-muted-foreground">
            Page {page.page_number} of {document.pages.length}
          </span>
          <Button
            type="button"
            size="sm"
            variant="outline"
            aria-label="Next page"
            disabled={page.page_number >= document.pages.length}
            onClick={() => {
              setPageNumber(page.page_number + 1)
              setSelectedElementId(null)
            }}
          >
            <ChevronRight className="size-4" aria-hidden />
          </Button>
        </div>
        <Button asChild size="sm" variant="ghost">
          <a href={contractSourceUrl(extractionId)} download>
            <Download className="size-4" aria-hidden />
            Download source
          </a>
        </Button>
      </div>
    </div>
  )
}
