"use client"

import { FileUp, LoaderCircle, ShieldCheck } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface DocumentUploadProps {
  busy: boolean
  onUpload: (file: File) => Promise<void>
}

const ACCEPTED_FILES = ".pdf,.docx,.pptx,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp"

export function DocumentUpload({ busy, onUpload }: DocumentUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function submit(file: File | undefined) {
    if (file && !busy) void onUpload(file)
  }

  return (
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
          submit(event.dataTransfer.files[0])
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
            {busy ? "Extracting your document" : "Choose a document to review"}
          </h2>
          <p className="mx-auto max-w-xl text-sm text-muted-foreground">
            Upload a PDF, DOCX, PPTX, or common image. The document is
            classified and routed to the most suitable available extractor.
          </p>
        </div>
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept={ACCEPTED_FILES}
          disabled={busy}
          aria-label="Choose a document for extraction"
          onChange={(event) => {
            submit(event.target.files?.[0])
            event.target.value = ""
          }}
        />
        <Button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
        >
          {busy ? "Processing…" : "Browse files"}
        </Button>
        <p className="flex items-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck className="size-4" aria-hidden />
          Uploaded content is treated as untrusted data and is never executed.
        </p>
      </CardContent>
    </Card>
  )
}
