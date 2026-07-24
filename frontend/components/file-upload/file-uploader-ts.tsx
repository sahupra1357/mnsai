"use client"

import { useState, useRef, type ChangeEvent } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

type OutputFormat = "json" | "markdown"

function FileUploaderTS() {
  const [selectedFile, setSelectedFile] = useState<File | undefined>(undefined)
  const [filePath, setFilePath] = useState("")
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("json")
  const [documentType, setDocumentType] = useState("")
  // Cache each format's result separately so toggling JSON ⇄ Markdown keeps
  // whatever has already been extracted instead of wiping it.
  const [jsonText, setJsonText] = useState("")
  const [markdownText, setMarkdownText] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const responseText = outputFormat === "json" ? jsonText : markdownText

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    setSelectedFile(file)
    // A new document invalidates any previously extracted results.
    setDocumentType("")
    setJsonText("")
    setMarkdownText("")
    if (file) setFilePath(file.name)
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    // Only touch the result for the format being extracted; the other
    // format's cached result stays intact.
    const setResult = outputFormat === "json" ? setJsonText : setMarkdownText
    setIsLoading(true)
    if (outputFormat === "json") setDocumentType("")
    setResult("")

    try {
      const form = new FormData()
      form.append("file", selectedFile)

      const endpoint =
        outputFormat === "json"
          ? "/api/gptfiles/ocr-json"
          : "/api/gptfiles/ocr"

      const res = await fetch(endpoint, { method: "POST", body: form })
      const data = await res.json()

      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`)
      }

      if (outputFormat === "json") {
        setDocumentType(data.document_type)
        setJsonText(JSON.stringify(data.data, null, 2))
      } else {
        setMarkdownText(data.text)
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error)
      setResult(`Error uploading file: ${message}`)
    }

    setIsLoading(false)
  }

  return (
    <>
      {/* ── Controls row ── */}
      <div className="py-4 space-y-3">
        {/* Format toggle */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            Output format
          </span>
          <Tabs
            value={outputFormat}
            onValueChange={(v) => setOutputFormat(v as OutputFormat)}
          >
            <TabsList>
              <TabsTrigger value="json">JSON</TabsTrigger>
              <TabsTrigger value="markdown">Markdown</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* File picker + upload */}
        <div className="flex items-center gap-2 w-full">
          <Input
            type="text"
            value={filePath}
            readOnly
            placeholder="No file chosen"
            className="flex-1 min-w-0"
          />
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="bg-ui-main hover:bg-[#00766C] text-white font-bold"
          >
            Choose File
          </Button>
          {selectedFile && (
            <Button
              type="button"
              onClick={handleUpload}
              className="bg-ui-main hover:bg-[#00766C] text-white font-bold"
            >
              Upload
            </Button>
          )}
        </div>
      </div>

      {/* ── Result area ── */}
      <div>
        {isLoading ? (
          <Loader2 className="h-8 w-8 animate-spin text-ui-main" />
        ) : (
          responseText && (
            <div className="mt-2 space-y-2">
              {outputFormat === "json" && documentType && (
                <p className="text-sm font-medium text-muted-foreground">
                  Document type:{" "}
                  <span className="font-semibold text-foreground capitalize">
                    {documentType.replace(/_/g, " ")}
                  </span>
                </p>
              )}
              <textarea
                value={responseText}
                readOnly
                className={[
                  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm",
                  "focus:outline-none focus:ring-2 focus:ring-ring",
                  outputFormat === "json" ? "font-mono" : "",
                ].join(" ")}
                rows={30}
              />
            </div>
          )
        )}
      </div>
    </>
  )
}

export default FileUploaderTS
