"use client"

import { useEffect, useState } from "react"

import { loadFieldCatalogue } from "./api"
import type { FieldDefinition } from "./types"

interface CatalogueState {
  catalogue: FieldDefinition[]
  /** The keys the picker starts with on the selected side. */
  defaultFields: string[]
  loading: boolean
  error: string | null
}

/** The ten-field schema, fetched from the backend catalogue.
 *
 *  The frontend never keeps a second copy of the field list: order, labels, and which
 *  five start selected all come from `GET /fields`.
 *
 *  `defaultFields` is the picker's starting selection, not a constraint — every one of
 *  the ten fields can be moved in or out. */
export function useFieldCatalogue(): CatalogueState {
  const [catalogue, setCatalogue] = useState<FieldDefinition[]>([])
  const [defaultFields, setDefaultFields] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void loadFieldCatalogue()
      .then((response) => {
        if (!active) return
        const fields = response.fields ?? []
        setCatalogue(fields)
        setDefaultFields(
          response.default_fields ??
            fields.filter((field) => field.default_selected).map((f) => f.key),
        )
        setError(null)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(
          caught instanceof Error
            ? caught.message
            : "The field schema could not be loaded.",
        )
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return { catalogue, defaultFields, loading, error }
}
