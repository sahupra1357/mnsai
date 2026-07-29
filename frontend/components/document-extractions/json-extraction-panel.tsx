"use client"

import { Braces, Eye } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

import { pageExtractedContent } from "./extracted-json"
import type { PageResult } from "./types"

interface JsonExtractionPanelProps {
  page: PageResult
  onViewDetails: () => void
}

function selectedProviderLabel(page: PageResult) {
  const selected = page.selected_parser
  if (!selected) return "Unavailable"
  const attempt = page.attempts.find(
    (item) => item.run_id === selected.run_id,
  )
  const model = attempt?.model || selected.version

  if (selected.name === "mistral-ocr")
    return `Mistral OCR · ${model}`
  if (selected.name === "openai-vision-terra")
    return `OpenAI · ${model || "GPT-5.6 Terra"}`
  if (selected.name === "openai-vision-sol")
    return `OpenAI · ${model || "GPT-5.6 Sol"}`
  if (selected.name === "tesseract")
    return `Tesseract · ${selected.version}`
  return `${selected.name} · ${selected.version}`
}

export function JsonExtractionPanel({
  page,
  onViewDetails,
}: JsonExtractionPanelProps) {
  const value = JSON.stringify(pageExtractedContent(page), null, 2)
  const confidence =
    page.confidence === null
      ? "Unavailable"
      : `${Math.round(page.confidence * 100)}%`
  const selectedProvider = selectedProviderLabel(page)

  return (
    <section
      className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-lg border bg-card"
      aria-labelledby="json-extraction-title"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div>
          <h2
            id="json-extraction-title"
            className="flex items-center gap-2 font-semibold"
          >
            <Braces className="size-4" aria-hidden />
            Extracted result
          </h2>
          <p className="text-xs text-muted-foreground">
            Extracted content only · JSON
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            title={page.selected_parser?.rationale ?? "No parser selected"}
          >
            Used: {selectedProvider}
          </Badge>
          <Badge
            variant="secondary"
            title={page.confidence_source ?? "No page confidence source"}
          >
            Page confidence: {confidence}
          </Badge>
          <Button type="button" variant="outline" onClick={onViewDetails}>
            <Eye aria-hidden />
            View details
          </Button>
        </div>
      </header>
      <div className="flex flex-1 p-4">
        <Textarea
          readOnly
          spellCheck={false}
          aria-label={`Extracted JSON for page ${page.page_number}`}
          className="min-h-[29rem] flex-1 resize-none font-mono text-sm leading-6"
          value={value}
        />
      </div>
    </section>
  )
}
