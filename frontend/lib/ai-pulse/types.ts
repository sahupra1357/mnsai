/**
 * AI Pulse — the dashboard's live intelligence layer.
 *
 * All data is factual metadata (names, titles, links, counts) fetched
 * server-side from public/free APIs and always linked back to the original
 * source. We never reproduce article/abstract body text or hotlink images.
 */

export interface TrendingModel {
  /** Full repo id, e.g. "meta-llama/Llama-4-70B" */
  id: string
  org: string
  name: string
  downloads: number
  likes: number
  pipelineTag?: string
  url: string
}

export interface Paper {
  /** arXiv id URL, also the canonical link */
  url: string
  title: string
  authors: string[]
  /** ISO date string */
  published: string
  /** Primary category, e.g. "cs.CL" */
  category: string
}

export interface WireItem {
  title: string
  url: string
  /** Human-readable source name shown next to the headline */
  source: string
  /** ISO date string when known */
  publishedAt?: string
}

/** Shared cache window (seconds) for every external fetch — ~2 requests/hour
 *  per source regardless of traffic, well inside every source's rate limits. */
export const REVALIDATE_SECONDS = 1800
