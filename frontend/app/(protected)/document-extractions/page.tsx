"use client"

import { AlertCircle, LoaderCircle } from "lucide-react"
import { useEffect, useState } from "react"

import {
  loadDocument,
  uploadDocument,
} from "@/components/document-extractions/api"
import { DocumentUpload } from "@/components/document-extractions/document-upload"
import { ReviewWorkspace } from "@/components/document-extractions/review-workspace"
import type { DocumentResult } from "@/components/document-extractions/types"
import { Button } from "@/components/ui/button"

export default function DocumentExtractionsPage() {
  const [document, setDocument] = useState<DocumentResult | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const processing =
    document?.status === "queued" ||
    document?.status === "classifying" ||
    document?.status === "extracting" ||
    document?.status === "fallback"

  useEffect(() => {
    if (!document || !processing) return
    const timer = window.setTimeout(() => {
      void loadDocument(document.document_id)
        .then(setDocument)
        .catch((caught: unknown) => {
          setError(
            caught instanceof Error
              ? caught.message
              : "Extraction status could not be refreshed.",
          )
          setDocument((current) => (current ? { ...current } : current))
        })
    }, 2000)
    return () => window.clearTimeout(timer)
  }, [document, processing])

  async function upload(file: File) {
    setUploading(true)
    setError(null)
    try {
      setDocument(await uploadDocument(file))
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The document could not be uploaded.",
      )
    } finally {
      setUploading(false)
    }
  }

  if (document && processing) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-3xl items-center justify-center px-4 py-10">
        <div
          className="w-full rounded-xl border bg-card p-8 text-center shadow-sm"
          role="status"
          aria-live="polite"
        >
          <LoaderCircle className="mx-auto mb-4 size-9 animate-spin text-primary" aria-hidden />
          <h1 className="text-xl font-semibold">Extraction is running on Modal</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            The source is safely stored and each page is being processed. This page
            will open the review workspace automatically when the result is ready.
          </p>
          {error && <p className="mt-4 text-sm text-destructive">{error}</p>}
          <Button className="mt-5" variant="outline" onClick={() => setDocument(null)}>
            Start another upload
          </Button>
        </div>
      </main>
    )
  }

  if (document) {
    return (
      <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6">
        <ReviewWorkspace
          initialDocument={document}
          onDocumentChange={setDocument}
          onStartOver={() => {
            setDocument(null)
            setError(null)
          }}
        />
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-16">
      <div className="mb-8 space-y-3 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
          Human validation workspace
        </p>
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Visual document extraction
        </h1>
        <p className="mx-auto max-w-2xl text-muted-foreground">
          Compare every source page with normalized extraction results, correct
          values, inspect provenance, and approve with a complete audit trail.
        </p>
      </div>

      {error && (
        <div
          className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          <span className="flex items-start gap-2">
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
            {error}
          </span>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setError(null)}
          >
            Dismiss
          </Button>
        </div>
      )}

      <DocumentUpload busy={uploading} onUpload={upload} />
    </main>
  )
}
