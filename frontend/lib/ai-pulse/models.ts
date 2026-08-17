import { REVALIDATE_SECONDS, type TrendingModel } from "./types"

/**
 * Model Watch — trending models from the Hugging Face Hub public API.
 * Free, unauthenticated, factual metadata; every row links back to the Hub.
 */
const HF_TRENDING_URL =
  "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=8"

interface HfModel {
  id?: string
  modelId?: string
  downloads?: number
  likes?: number
  pipeline_tag?: string
}

export async function getTrendingModels(): Promise<TrendingModel[]> {
  try {
    const res = await fetch(HF_TRENDING_URL, {
      headers: { accept: "application/json" },
      next: { revalidate: REVALIDATE_SECONDS },
    })
    if (!res.ok) return []
    const data = (await res.json()) as HfModel[]
    if (!Array.isArray(data)) return []

    return data
      .map((m): TrendingModel | null => {
        const id = m.id ?? m.modelId
        if (!id) return null
        const slash = id.indexOf("/")
        return {
          id,
          org: slash > 0 ? id.slice(0, slash) : "—",
          name: slash > 0 ? id.slice(slash + 1) : id,
          downloads: m.downloads ?? 0,
          likes: m.likes ?? 0,
          pipelineTag: m.pipeline_tag,
          url: `https://huggingface.co/${id}`,
        }
      })
      .filter((m): m is TrendingModel => m !== null)
  } catch {
    // Module hides itself when the source is unreachable — never an error page.
    return []
  }
}
