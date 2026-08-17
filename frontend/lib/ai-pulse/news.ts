import { REVALIDATE_SECONDS, type WireItem } from "./types"

/**
 * AI Wire — headline-and-link aggregation only. Two source families:
 *  - Hacker News front page (Algolia public API), filtered to AI stories,
 *    linking to the original article.
 *  - Official vendor blogs via their public RSS feeds (headline + link).
 * We never reproduce article text or images; each item links to its source.
 * A failed source is skipped silently (Promise.allSettled) so one outage
 * never empties the wire.
 */

const HN_URL =
  "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"

const RSS_FEEDS: { source: string; url: string }[] = [
  { source: "OpenAI", url: "https://openai.com/news/rss.xml" },
  { source: "Google AI", url: "https://blog.google/technology/ai/rss/" },
  { source: "DeepMind", url: "https://deepmind.google/blog/rss.xml" },
]

const AI_TERMS =
  /\b(AI|A\.I\.|LLMs?|GPT[-\w]*|Claude|Gemini|Llama|Mistral|Anthropic|OpenAI|DeepMind|machine learning|deep learning|neural|transformer|diffusion|agents?|copilot|chatbot|model)\b/i

function cleanText(s: string): string {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/\s+/g, " ")
    .trim()
}

interface HnHit {
  title?: string
  url?: string
  objectID?: string
  created_at?: string
}

async function fetchHackerNews(): Promise<WireItem[]> {
  const res = await fetch(HN_URL, {
    headers: { accept: "application/json" },
    next: { revalidate: REVALIDATE_SECONDS },
  })
  if (!res.ok) return []
  const data = (await res.json()) as { hits?: HnHit[] }
  return (data.hits ?? [])
    .filter((h) => h.title && AI_TERMS.test(h.title))
    .slice(0, 8)
    .map((h) => ({
      title: h.title as string,
      // Ask HN etc. have no external URL — link to the HN discussion instead.
      url: h.url ?? `https://news.ycombinator.com/item?id=${h.objectID}`,
      source: "Hacker News",
      publishedAt: h.created_at,
    }))
}

async function fetchRss(source: string, url: string): Promise<WireItem[]> {
  const res = await fetch(url, {
    headers: { accept: "application/rss+xml, application/xml, text/xml" },
    next: { revalidate: REVALIDATE_SECONDS },
  })
  if (!res.ok) return []
  const xml = await res.text()

  const items: WireItem[] = []
  for (const [, item] of xml.matchAll(/<item>([\s\S]*?)<\/item>/g)) {
    const title = item.match(/<title>([\s\S]*?)<\/title>/)?.[1]
    const link = item.match(/<link>([\s\S]*?)<\/link>/)?.[1]
    const pubDate = item.match(/<pubDate>([\s\S]*?)<\/pubDate>/)?.[1]
    if (!title || !link) continue
    const parsed = pubDate ? new Date(cleanText(pubDate)) : null
    items.push({
      title: cleanText(title),
      url: cleanText(link),
      source,
      publishedAt:
        parsed && !Number.isNaN(parsed.getTime())
          ? parsed.toISOString()
          : undefined,
    })
    if (items.length >= 4) break
  }
  return items
}

export async function getWireItems(): Promise<WireItem[]> {
  const results = await Promise.allSettled([
    fetchHackerNews(),
    ...RSS_FEEDS.map((f) => fetchRss(f.source, f.url)),
  ])
  const items = results
    .filter(
      (r): r is PromiseFulfilledResult<WireItem[]> => r.status === "fulfilled",
    )
    .flatMap((r) => r.value)

  // Newest first; undated items sink to the end. Cap keeps the ticker snappy.
  return items
    .sort((a, b) => (b.publishedAt ?? "").localeCompare(a.publishedAt ?? ""))
    .slice(0, 14)
}
