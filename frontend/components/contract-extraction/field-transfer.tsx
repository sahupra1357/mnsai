"use client"

import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react"
import { useId, useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

import { requestedCount } from "./fields"
import type { FieldDefinition } from "./types"

interface FieldTransferProps {
  /** The ten fields exactly as `GET /fields` returned them, in catalogue order. */
  catalogue: FieldDefinition[]
  /** Optional keys the operator has selected. Any subset, from none to all five. */
  selected: string[]
  onChange: (selected: string[]) => void
  disabled?: boolean
}

type Side = "available" | "selected"

/** Dual-list field picker: available on the left, selected on the right.
 *
 *  Highlight one or more rows and move them across, or move the whole set at once.
 *  Double-clicking a row moves just that row.
 *
 *  **All ten fields are movable.** Five start on the right (the catalogue's
 *  `default_selected`), but that is a starting point, not a lock — any of them can be
 *  pushed back to the left, and the right-hand list may be emptied completely. When it
 *  is empty there is nothing to extract, so Extract is disabled; one field on the right
 *  is enough to proceed.
 *
 *  What lands on the right is what gets requested: a requested field that cannot be
 *  extracted is a failure and raises the record for human verification, while a field
 *  left on the left is never extracted and comes back blank. That is the point of
 *  showing both sets side by side rather than hiding them in a dropdown.
 */
export function FieldTransfer({
  catalogue,
  selected,
  onChange,
  disabled = false,
}: FieldTransferProps) {
  const [highlight, setHighlight] = useState<Record<Side, string[]>>({
    available: [],
    selected: [],
  })
  const availableId = useId()
  const selectedId = useId()
  const availableRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLDivElement>(null)

  // Both lists stay in catalogue order however the operator moved things, so a field
  // is always in the same place relative to its neighbours.
  const availableFields = catalogue.filter(
    (definition) => !selected.includes(definition.key),
  )
  const selectedFields = catalogue.filter((definition) =>
    selected.includes(definition.key),
  )

  /** Always rebuild from the catalogue so the persisted order never depends on the
   *  order the operator happened to click in. */
  function commit(keys: string[]) {
    onChange(
      catalogue
        .map((definition) => definition.key)
        .filter((key) => keys.includes(key)),
    )
  }

  function move(from: Side) {
    const moving = highlight[from]
    if (moving.length === 0) return
    commit(
      from === "available"
        ? [...selected, ...moving]
        : selected.filter((key) => !moving.includes(key)),
    )
    setHighlight((current) => ({ ...current, [from]: [] }))
  }

  function moveAll(from: Side) {
    commit(
      from === "available" ? catalogue.map((definition) => definition.key) : [],
    )
    setHighlight({ available: [], selected: [] })
  }

  function moveOne(from: Side, key: string) {
    commit(
      from === "available"
        ? [...selected, key]
        : selected.filter((item) => item !== key),
    )
    setHighlight((current) => ({
      ...current,
      [from]: current[from].filter((item) => item !== key),
    }))
  }

  function toggleHighlight(side: Side, key: string) {
    setHighlight((current) => ({
      ...current,
      [side]: current[side].includes(key)
        ? current[side].filter((item) => item !== key)
        : [...current[side], key],
    }))
  }

  /** Arrow keys walk the rows of one list. Every row is movable now, so nothing is
   *  skipped — the attribute selector simply keeps this scoped to option rows. */
  function moveFocus(side: Side, direction: 1 | -1) {
    const panel = side === "available" ? availableRef : selectedRef
    const rows = Array.from(
      panel.current?.querySelectorAll<HTMLElement>(
        '[role="option"][data-movable="true"]',
      ) ?? [],
    )
    if (rows.length === 0) return
    const current = rows.indexOf(document.activeElement as HTMLElement)
    const next =
      current === -1
        ? direction === 1
          ? 0
          : rows.length - 1
        : (current + direction + rows.length) % rows.length
    rows[next]?.focus()
  }

  const total = catalogue.length
  const chosen = requestedCount(catalogue, selected)

  function renderRow(definition: FieldDefinition, side: Side) {
    const active = highlight[side].includes(definition.key)
    return (
      <button
        key={definition.key}
        type="button"
        role="option"
        data-movable="true"
        data-field-option={definition.key}
        aria-selected={active}
        disabled={disabled}
        className={cn(
          "flex w-full flex-col items-start gap-0.5 rounded-sm px-2 py-1.5 text-left transition-colors",
          "hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          active && "bg-primary/10 hover:bg-primary/10",
          disabled && "cursor-not-allowed opacity-60",
        )}
        onClick={() => toggleHighlight(side, definition.key)}
        onDoubleClick={() => moveOne(side, definition.key)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault()
            moveFocus(side, 1)
          }
          if (event.key === "ArrowUp") {
            event.preventDefault()
            moveFocus(side, -1)
          }
          // Enter commits the row across; Space only highlights it.
          if (event.key === "Enter") {
            event.preventDefault()
            moveOne(side, definition.key)
          }
        }}
      >
        <span className="text-sm font-medium">{definition.label}</span>
        <span className="line-clamp-1 text-xs text-muted-foreground">
          {definition.description}
        </span>
      </button>
    )
  }

  const moveButtons: Array<{
    label: string
    icon: typeof ChevronRight
    off: boolean
    onClick: () => void
  }> = [
    {
      label: "Add highlighted fields",
      icon: ChevronRight,
      off: disabled || highlight.available.length === 0,
      onClick: () => move("available"),
    },
    {
      label: "Add all fields",
      icon: ChevronsRight,
      off: disabled || availableFields.length === 0,
      onClick: () => moveAll("available"),
    },
    {
      label: "Remove highlighted fields",
      icon: ChevronLeft,
      off: disabled || highlight.selected.length === 0,
      onClick: () => move("selected"),
    },
    {
      label: "Remove all fields",
      icon: ChevronsLeft,
      off: disabled || selectedFields.length === 0,
      onClick: () => moveAll("selected"),
    },
  ]

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr]">
        {/* Left: not requested. These come back blank and are never a failure. */}
        <div className="flex min-w-0 flex-col rounded-md border bg-background">
          <div className="flex items-baseline justify-between gap-2 border-b px-3 py-2">
            <h3 className="text-sm font-medium">Available fields</h3>
            <span className="text-xs text-muted-foreground">
              {availableFields.length} available
            </span>
          </div>
          <div
            ref={availableRef}
            id={availableId}
            role="listbox"
            aria-multiselectable="true"
            aria-label="Available fields, not selected"
            className="min-h-48 flex-1 space-y-0.5 overflow-y-auto p-1"
          >
            {availableFields.length === 0 ? (
              <p className="px-2 py-6 text-center text-xs text-muted-foreground">
                All ten fields are selected.
              </p>
            ) : (
              availableFields.map((definition) =>
                renderRow(definition, "available"),
              )
            )}
          </div>
          <p className="border-t px-3 py-2 text-xs text-muted-foreground">
            Left here: never extracted, returned blank.
          </p>
        </div>

        <div className="flex flex-row items-center justify-center gap-2 sm:flex-col">
          {moveButtons.map(({ label, icon: Icon, off, onClick }) => (
            <Button
              key={label}
              type="button"
              size="icon"
              variant="outline"
              className="size-9"
              aria-label={label}
              title={label}
              disabled={off}
              onClick={onClick}
            >
              <Icon className="size-4" aria-hidden />
            </Button>
          ))}
        </div>

        {/* Right: requested. A blank in any of these is a verification failure. */}
        <div className="flex min-w-0 flex-col rounded-md border bg-background">
          <div className="flex items-baseline justify-between gap-2 border-b px-3 py-2">
            <h3 className="text-sm font-medium">Selected for extraction</h3>
            <span className="text-xs text-muted-foreground">
              {chosen} of {total}
            </span>
          </div>
          <div
            ref={selectedRef}
            id={selectedId}
            role="listbox"
            aria-multiselectable="true"
            aria-label="Fields selected for extraction"
            className="min-h-48 flex-1 space-y-0.5 overflow-y-auto p-1"
          >
            {selectedFields.length === 0 ? (
              <p className="px-2 py-6 text-center text-xs text-muted-foreground">
                No fields selected. Move at least one across to extract.
              </p>
            ) : (
              selectedFields.map((definition) =>
                renderRow(definition, "selected"),
              )
            )}
          </div>
          <p className="border-t px-3 py-2 text-xs text-muted-foreground">
            A blank in any of these is a failure to verify.
          </p>
        </div>
      </div>

      <p className="text-xs text-muted-foreground" aria-live="polite">
        <span className="font-medium text-foreground">
          {chosen} of {total} fields
        </span>{" "}
        {chosen === 0
          ? "selected — move at least one field across to extract"
          : "will be extracted · every field can be moved either way"}
      </p>
    </div>
  )
}
