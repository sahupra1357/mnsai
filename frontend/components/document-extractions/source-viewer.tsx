"use client"

import { Focus, LoaderCircle, RotateCw, ZoomIn, ZoomOut } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

import { loadPagePreview, sourceDownloadUrl } from "./api"
import type { ExtractedElement, PageResult } from "./types"

interface SourceViewerProps {
  documentId: string
  mediaType: string
  page: PageResult
  selectedElementId: string | null
  onSelectElement: (elementId: string) => void
}

function boxStyle(element: ExtractedElement) {
  const box = element.bounding_box
  const space = element.coordinate_space
  if (!box || !space || space.origin !== "top-left") return undefined
  return {
    left: `${(box.left / space.width) * 100}%`,
    top: `${(box.top / space.height) * 100}%`,
    width: `${((box.right - box.left) / space.width) * 100}%`,
    height: `${((box.bottom - box.top) / space.height) * 100}%`,
  }
}

export function SourceViewer({
  documentId,
  mediaType,
  page,
  selectedElementId,
  onSelectElement,
}: SourceViewerProps) {
  const [sourceUrl, setSourceUrl] = useState<string | null>(null)
  const [sourceError, setSourceError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [fitToPage, setFitToPage] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    let objectUrl: string | null = null
    setSourceUrl(null)
    setSourceError(null)

    loadPagePreview(documentId, page.page_number, controller.signal)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setSourceUrl(objectUrl)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return
        setSourceError(
          error instanceof Error
            ? error.message
            : "The source could not be loaded.",
        )
      })

    return () => {
      controller.abort()
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [documentId, page.page_number])

  const coordinateSpace = useMemo(
    () =>
      page.elements.find((element) => element.coordinate_space)
        ?.coordinate_space ?? null,
    [page.elements],
  )

  // Not every parser reports where on the page each run of text sits: the
  // markdown-based ones (mineru, marker) have no coordinates at all. Without
  // them the overlay silently renders nothing, which reads as a broken page
  // rather than a parser that never had the data — so say which it is.
  const positionedCount = useMemo(
    () => page.elements.filter((element) => boxStyle(element)).length,
    [page.elements],
  )
  const positionsUnavailable = page.elements.length > 0 && positionedCount === 0

  return (
    <section
      className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-lg border bg-muted/20"
      aria-labelledby="source-panel-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b bg-card px-4 py-3">
        <div>
          <h2 id="source-panel-title" className="font-semibold">
            Original source
          </h2>
          <p className="text-xs text-muted-foreground">
            Page {page.page_number} · immutable
          </p>
          {positionsUnavailable && (
            <p className="mt-1 max-w-prose text-xs text-muted-foreground">
              {page.selected_parser
                ? `${page.selected_parser.name} extracted this text without positions,`
                : "This parser extracted the text without positions,"}{" "}
              so the document cannot be highlighted. The extracted values are
              unaffected.
            </p>
          )}
        </div>
        <div
          className="flex items-center gap-1"
          aria-label="Source view controls"
        >
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label="Zoom out"
            disabled={!sourceUrl || zoom <= 0.5}
            onClick={() => {
              setFitToPage(false)
              setZoom((value) => Math.max(0.5, value - 0.25))
            }}
          >
            <ZoomOut aria-hidden />
          </Button>
          <span className="w-12 text-center text-xs tabular-nums">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label="Zoom in"
            disabled={!sourceUrl || zoom >= 3}
            onClick={() => {
              setFitToPage(false)
              setZoom((value) => Math.min(3, value + 0.25))
            }}
          >
            <ZoomIn aria-hidden />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label="Rotate clockwise"
            disabled={!sourceUrl}
            onClick={() => {
              setFitToPage(false)
              setRotation((value) => (value + 90) % 360)
            }}
          >
            <RotateCw aria-hidden />
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            aria-label="Fit source to page"
            disabled={!sourceUrl}
            onClick={() => {
              setZoom(1)
              setRotation(0)
              setFitToPage(true)
            }}
          >
            <Focus aria-hidden />
          </Button>
        </div>
      </header>

      <div className="relative flex flex-1 items-center justify-center overflow-auto bg-black/5 p-5 dark:bg-black/20">
        {!sourceUrl && !sourceError && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Loading source…
          </div>
        )}
        {sourceUrl && (
          <div
            className="relative origin-center shadow-xl transition-transform"
            style={{
              width:
                fitToPage || !coordinateSpace ? "100%" : coordinateSpace.width,
              maxWidth: fitToPage ? "100%" : "none",
              aspectRatio: coordinateSpace
                ? `${coordinateSpace.width} / ${coordinateSpace.height}`
                : undefined,
              transform: `scale(${zoom}) rotate(${rotation}deg)`,
            }}
          >
            {/* The blob URL is same-origin data returned by the authenticated API. */}
            <img
              src={sourceUrl}
              alt={`Original page ${page.page_number}`}
              className="block size-full object-contain"
            />
            {page.elements.map((element) => {
              const position = boxStyle(element)
              if (!position) return null
              const selected = element.element_id === selectedElementId
              return (
                <button
                  key={element.element_id}
                  type="button"
                  style={position}
                  aria-label={`Select extracted ${element.type} ${
                    element.reading_order + 1
                  }`}
                  aria-pressed={selected}
                  className={cn(
                    "absolute min-h-2 min-w-2 border-2 bg-primary/10 transition-colors hover:bg-primary/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    selected
                      ? "z-10 border-primary bg-primary/25"
                      : "border-primary/40",
                  )}
                  onClick={() => onSelectElement(element.element_id)}
                />
              )
            })}
          </div>
        )}
        {sourceError && (
          <div
            className="max-w-md rounded-lg border bg-card p-6 text-center"
            role="alert"
          >
            <p className="font-medium">Page preview unavailable</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {sourceError} The converter for {mediaType} may not be configured.
              You can still review the normalized extraction and download the
              immutable source.
            </p>
            <Button asChild variant="outline" className="mt-4">
              <a href={sourceDownloadUrl(documentId)} download>
                Download source
              </a>
            </Button>
          </div>
        )}
      </div>
    </section>
  )
}
