"use client"

import { FileText, FileUp, LoaderCircle, ShieldCheck, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import { loadCapabilities } from "@/components/document-extractions/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

import { FieldTransfer } from "./field-transfer"
import { requestedCount } from "./fields"
import type { FieldDefinition } from "./types"

interface ContractUploadProps {
  catalogue: FieldDefinition[]
  selected: string[]
  onSelectedChange: (selected: string[]) => void
  busy: boolean
  onExtract: (file: File) => Promise<void>
}

/** Same accepted types as the document-extraction dropzone — this feature reads what
 *  that pipeline produces, so it can never accept a file that pipeline cannot. */
const ACCEPTED_FILES = ".pdf,.docx,.pptx,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"

function formatBytes(bytes: number): string {
  const megabytes = bytes / (1024 * 1024)
  return megabytes >= 1
    ? `${Math.round(megabytes)} MB`
    : `${Math.round(bytes / 1024)} KB`
}

export function ContractUpload({
  catalogue,
  selected,
  onSelectedChange,
  busy,
  onExtract,
}: ContractUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [limits, setLimits] = useState<string | null>(null)

  // Upload limits come from the extraction pipeline this feature sits on top of, so
  // the number shown is the number actually enforced. Silently omitted if it fails.
  useEffect(() => {
    let active = true
    void loadCapabilities()
      .then((response) => {
        if (!active) return
        setLimits(
          `Up to ${formatBytes(response.max_upload_bytes)} and ${
            response.max_pages
          } pages.`,
        )
      })
      .catch(() => {
        if (active) setLimits(null)
      })
    return () => {
      active = false
    }
  }, [])

  const chosen = requestedCount(catalogue, selected)

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-dashed bg-card/70">
        <CardContent
          className={cn(
            "flex min-h-64 flex-col items-center justify-center gap-5 p-8 text-center transition-colors",
            dragging && "bg-primary/5",
          )}
          onDragEnter={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={(event) => {
            if (!event.currentTarget.contains(event.relatedTarget as Node)) {
              setDragging(false)
            }
          }}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            const dropped = event.dataTransfer.files[0]
            if (dropped && !busy) setFile(dropped)
          }}
        >
          <div className="rounded-2xl bg-primary/10 p-4 text-primary">
            {busy ? (
              <LoaderCircle className="size-8 animate-spin" aria-hidden />
            ) : (
              <FileUp className="size-8" aria-hidden />
            )}
          </div>
          <div className="space-y-2">
            <h2 className="text-xl font-semibold">
              {busy ? "Extracting contract fields" : "Choose a contract"}
            </h2>
            <p className="mx-auto max-w-xl text-sm text-muted-foreground">
              Upload a PDF, DOCX, PPTX, or common image. The contract is
              extracted once, then the selected fields are pulled from what the
              extractor found — nothing is guessed.{limits ? ` ${limits}` : ""}
            </p>
          </div>

          <input
            ref={inputRef}
            className="sr-only"
            type="file"
            accept={ACCEPTED_FILES}
            disabled={busy}
            aria-label="Choose a contract for field extraction"
            onChange={(event) => {
              const picked = event.target.files?.[0]
              if (picked) setFile(picked)
              event.target.value = ""
            }}
          />

          {file ? (
            <div className="flex max-w-full flex-wrap items-center justify-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm">
              <FileText className="size-4 shrink-0 text-primary" aria-hidden />
              <span className="max-w-[18rem] truncate font-medium">
                {file.name}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatBytes(file.size)}
              </span>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-7"
                aria-label={`Remove ${file.name}`}
                disabled={busy}
                onClick={() => setFile(null)}
              >
                <X className="size-4" aria-hidden />
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
            >
              Browse files
            </Button>
          )}

          {file && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
            >
              Choose a different file
            </Button>
          )}

          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="size-4" aria-hidden />
            Uploaded content is treated as untrusted data and is never executed.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="space-y-1">
            <h2 className="text-base font-medium">Fields to extract</h2>
            <p className="text-sm text-muted-foreground">
              Five fields start selected. Move any of the ten either way —
              extract as few as one, or all ten.
            </p>
          </div>

          <div id="contract-field-picker">
            <FieldTransfer
              catalogue={catalogue}
              selected={selected}
              onChange={onSelectedChange}
              disabled={busy}
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
            <p className="text-sm text-muted-foreground">
              A field that cannot be grounded in the document stays blank and is
              raised for human verification — never guessed.
            </p>
            <Button
              type="button"
              // Nothing on the right means nothing to extract; the backend refuses an
              // empty selection with a 422, so the button refuses it first.
              disabled={busy || !file || chosen === 0}
              onClick={() => {
                if (file && chosen > 0) void onExtract(file)
              }}
            >
              {busy ? (
                <>
                  <LoaderCircle className="size-4 animate-spin" aria-hidden />
                  Extracting…
                </>
              ) : chosen === 0 ? (
                "Select a field to extract"
              ) : (
                `Extract ${chosen} field${chosen === 1 ? "" : "s"}`
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
