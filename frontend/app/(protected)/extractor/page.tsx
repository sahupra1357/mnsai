"use client"

import FileUploaderTS from "@/components/file-upload/file-uploader-ts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function ExtractorPage() {
  return (
    <div className="container mx-auto max-w-3xl px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-semibold">Data Extraction</CardTitle>
        </CardHeader>
        <CardContent>
          <FileUploaderTS />
        </CardContent>
      </Card>
    </div>
  )
}
