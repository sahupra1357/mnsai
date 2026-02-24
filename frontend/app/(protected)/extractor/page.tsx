"use client"

import FileUploaderTS from "@/components/file-upload/file-uploader-ts"

export default function ExtractorPage() {
  return (
    <div className="container mx-auto max-w-full">
      <h1 className="text-2xl font-semibold pt-12 text-center md:text-left">
        Data Extraction
      </h1>
      <FileUploaderTS />
    </div>
  )
}
