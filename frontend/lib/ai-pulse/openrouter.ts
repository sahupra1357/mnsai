import { REVALIDATE_SECONDS } from "./types"

/**
 * OpenRouter Watch — newest models on OpenRouter via their documented public
 * API (GET /api/v1/models, key-free). Factual catalog metadata only: name,
 * launch date, context window, price. Their usage *rankings* live on an
 * undocumented internal endpoint we deliberately don't consume — the module
 * header links out to openrouter.ai/rankings for that instead.
 */
const OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

export interface OpenRouterModel {
  id: string
  name: string
  /** Unix seconds when the model was added */
  created: number
  contextLength: number
  /** USD per 1M prompt / completion tokens */
  promptPerM: number
  completionPerM: number
  url: string
}

interface RawModel {
  id?: string
  name?: string
  created?: number
  context_length?: number
  pricing?: { prompt?: string; completion?: string }
}

export async function getNewOpenRouterModels(): Promise<OpenRouterModel[]> {
  try {
    const res = await fetch(OPENROUTER_MODELS_URL, {
      headers: { accept: "application/json" },
      next: { revalidate: REVALIDATE_SECONDS },
    })
    if (!res.ok) return []
    const data = (await res.json()) as { data?: RawModel[] }
    if (!Array.isArray(data.data)) return []

    return data.data
      .filter(
        (m): m is RawModel & { id: string; name: string; created: number } =>
          Boolean(m.id && m.name && m.created) &&
          // Skip router pseudo-models and duplicate :free/:extended variants —
          // the base listing is the launch that matters.
          !m.id!.startsWith("openrouter/") &&
          !m.id!.includes(":"),
      )
      .sort((a, b) => b.created - a.created)
      // Eight: these rows are more compact than the trending/paper rows, so
      // it takes a couple more to fill the middle column to the same depth.
      .slice(0, 8)
      .map((m) => ({
        id: m.id,
        // API names read "Org: Model" — the org gets its own line in the UI.
        name: m.name.includes(": ")
          ? m.name.split(": ").slice(1).join(": ")
          : m.name,
        created: m.created,
        contextLength: m.context_length ?? 0,
        promptPerM: Number(m.pricing?.prompt ?? 0) * 1_000_000,
        completionPerM: Number(m.pricing?.completion ?? 0) * 1_000_000,
        url: `https://openrouter.ai/${m.id}`,
      }))
  } catch {
    return []
  }
}
