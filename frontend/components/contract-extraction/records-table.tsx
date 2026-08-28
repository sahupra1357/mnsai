"use client"

import { AlertCircle, LoaderCircle, RefreshCw } from "lucide-react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useCallback, useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

import { listContractExtractions } from "./api"
import {
  STATUS_LABEL,
  effectiveValue,
  formatTimestamp,
  hasHumanValue,
  isRequested,
  labelFor,
  statusBadgeVariant,
  unresolvedByKey,
} from "./fields"
import type {
  ContractFieldRecordRow,
  ExtractionStatus,
  FieldDefinition,
} from "./types"

const PAGE_SIZE = 25

const FILTERS: Array<{ label: string; value: ExtractionStatus | null }> = [
  { label: "All", value: null },
  { label: "Needs verification", value: "needs_verification" },
  { label: "Complete", value: "complete" },
  { label: "Verified", value: "verified" },
  { label: "Rejected", value: "rejected" },
]

export function verificationHref(extractionId: string): string {
  return `/contract-extraction?extraction=${encodeURIComponent(
    extractionId,
  )}&view=verify`
}

interface RecordsTableProps {
  catalogue: FieldDefinition[]
}

/** The persisted rows: ten field columns plus source, status, and timestamp.
 *
 *  Cells show the **effective** value — the human's correction when there is one,
 *  otherwise the machine value — and mark which ones a human supplied. There is no
 *  sorting on the date columns on purpose: they hold `DD/MM/YYYY` text, which sorts
 *  lexically rather than chronologically, so offering it would be a lie.
 */
export function RecordsTable({ catalogue }: RecordsTableProps) {
  const router = useRouter()
  const [rows, setRows] = useState<ContractFieldRecordRow[]>([])
  const [count, setCount] = useState(0)
  const [skip, setSkip] = useState(0)
  const [filter, setFilter] = useState<ExtractionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const page = await listContractExtractions({
        extractionStatus: filter,
        skip,
        limit: PAGE_SIZE,
      })
      setRows(page.data ?? [])
      setCount(page.count ?? 0)
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "The extraction records could not be loaded.",
      )
    } finally {
      setLoading(false)
    }
  }, [filter, skip])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex flex-wrap gap-1"
          role="group"
          aria-label="Filter records by status"
        >
          {FILTERS.map((option) => (
            <Button
              key={option.label}
              type="button"
              size="sm"
              variant={filter === option.value ? "default" : "outline"}
              aria-pressed={filter === option.value}
              onClick={() => {
                setFilter(option.value)
                setSkip(0)
              }}
            >
              {option.label}
            </Button>
          ))}
        </div>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw
            className={cn("size-4", loading && "animate-spin")}
            aria-hidden
          />
          Refresh
        </Button>
      </div>

      {error && (
        <div
          className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border">
        <Table className="min-w-[80rem]">
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[12rem]">Source</TableHead>
              <TableHead className="min-w-[10rem]">Status</TableHead>
              {catalogue.map((definition) => (
                <TableHead key={definition.key} className="min-w-[12rem]">
                  {definition.label}
                </TableHead>
              ))}
              <TableHead className="min-w-[11rem]">Extracted</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={catalogue.length + 3}>
                  <span className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
                    <LoaderCircle className="size-4 animate-spin" aria-hidden />
                    Loading records…
                  </span>
                </TableCell>
              </TableRow>
            )}
            {!loading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={catalogue.length + 3}>
                  <span className="block py-6 text-sm text-muted-foreground">
                    No extraction matches this filter yet.
                  </span>
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => {
              const unresolved = unresolvedByKey(row.unresolved_fields)
              return (
                <TableRow
                  key={row.extraction_id}
                  className="cursor-pointer"
                  onClick={() =>
                    router.push(verificationHref(row.extraction_id))
                  }
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      router.push(verificationHref(row.extraction_id))
                    }
                  }}
                >
                  <TableCell className="font-medium">
                    <Link
                      href={verificationHref(row.extraction_id)}
                      className="underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {row.source_name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusBadgeVariant(row.extraction_status)}>
                      {STATUS_LABEL[row.extraction_status]}
                    </Badge>
                  </TableCell>
                  {catalogue.map((definition) => {
                    const requested = isRequested(
                      definition,
                      row.selected_fields,
                    )
                    const value = effectiveValue(row, definition.key)
                    const failed = unresolved.has(definition.key)
                    return (
                      <TableCell
                        key={definition.key}
                        className={cn(!requested && "opacity-60")}
                      >
                        {value ? (
                          <span
                            className="flex items-center gap-2"
                            title={value}
                          >
                            <span className="line-clamp-2 max-w-[16rem]">
                              {value}
                            </span>
                            {hasHumanValue(row, definition.key) && (
                              <Badge
                                variant="secondary"
                                className="shrink-0 text-[0.65rem]"
                                title="Supplied by a human during verification"
                              >
                                human
                              </Badge>
                            )}
                          </span>
                        ) : failed ? (
                          <span className="text-xs text-destructive">
                            blank — {labelFor(catalogue, definition.key)} not
                            extracted
                          </span>
                        ) : requested ? (
                          <span className="text-muted-foreground">—</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            not selected
                          </span>
                        )}
                      </TableCell>
                    )
                  })}
                  <TableCell className="text-sm text-muted-foreground">
                    {formatTimestamp(row.created_at)}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          {count === 0
            ? "No records"
            : `Showing ${skip + 1}–${Math.min(
                skip + rows.length,
                count,
              )} of ${count}`}
          {" · "}
          Dates are stored as DD/MM/YYYY text, so the table is ordered by
          extraction time and the date columns are not sortable.
        </p>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={skip === 0 || loading}
            onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
          >
            Previous
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={skip + rows.length >= count || loading}
            onClick={() => setSkip(skip + PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}
