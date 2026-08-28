"use client"

import { AlertCircle, ArrowLeft, LoaderCircle } from "lucide-react"
import Link from "next/link"

import { RecordsTable } from "@/components/contract-extraction/records-table"
import { useFieldCatalogue } from "@/components/contract-extraction/use-field-catalogue"
import { Button } from "@/components/ui/button"

export default function ContractExtractionRecordsPage() {
  const { catalogue, loading, error } = useFieldCatalogue()

  return (
    <main className="mx-auto max-w-[1800px] px-4 py-6 sm:px-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            Stored extractions
          </p>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Contract field records
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            One row per extraction, ten field columns wide. Cells show the
            effective value — a human correction when there is one, otherwise
            the extracted value. Open a row to verify it.
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/contract-extraction">
            <ArrowLeft className="size-4" aria-hidden />
            New extraction
          </Link>
        </Button>
      </header>

      {error && (
        <div
          className="mb-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          {error}
        </div>
      )}

      {loading ? (
        <div
          className="flex min-h-[16rem] items-center justify-center rounded-lg border bg-card"
          role="status"
          aria-live="polite"
        >
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <LoaderCircle className="size-4 animate-spin" aria-hidden />
            Loading the field schema…
          </p>
        </div>
      ) : (
        <RecordsTable catalogue={catalogue} />
      )}
    </main>
  )
}
