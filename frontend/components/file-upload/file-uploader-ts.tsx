"use client"

import { useState, useRef, type ChangeEvent } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

function FileUploaderTS() {
  const [selectedFile, setSelectedFile] = useState<File | undefined>(undefined)
  const [filePath, setFilePath] = useState("")
  const [documentType, setDocumentType] = useState("")
  const [responseJson, setResponseJson] = useState("")
  const [isLoading, setIsLoading] = useState<boolean>(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleButtonClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    setSelectedFile(file)
    setDocumentType("")
    setResponseJson("")
    if (file) {
      setFilePath(file.name)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    setIsLoading(true)
    setDocumentType("")
    setResponseJson("")

    try {
      const form = new FormData()
      form.append("file", selectedFile)

      const res = await fetch("/api/gptfiles/ocr-json", {
        method: "POST",
        body: form,
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data?.detail ?? `Server error ${res.status}`)
      }

      setDocumentType(data.document_type)
      setResponseJson(JSON.stringify(data.data, null, 2))
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error)
      setResponseJson(`Error uploading file: ${message}`)
    }
    setIsLoading(false)
  }

  return (
    <>
      <div className="py-4">
        <div className="flex items-center gap-2 w-full">
          <Input
            type="text"
            value={filePath}
            readOnly
            placeholder="File path will be displayed here"
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
            onClick={handleButtonClick}
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
      <div>
        {isLoading ? (
          <Loader2 className="h-8 w-8 animate-spin text-ui-main" />
        ) : (
          responseJson && (
            <div className="mt-4 space-y-2">
              {documentType && (
                <p className="text-sm font-medium text-muted-foreground">
                  Document type:{" "}
                  <span className="font-semibold text-foreground capitalize">
                    {documentType.replace(/_/g, " ")}
                  </span>
                </p>
              )}
              <textarea
                value={responseJson}
                readOnly
                placeholder="..."
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
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
