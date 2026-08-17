import { type Paper, REVALIDATE_SECONDS } from "./types"

/**
 * Fresh Papers — latest AI submissions from the arXiv API.
 * arXiv's API is explicitly free to use; metadata is CC0. We show only
 * title/authors/date/category and link to the abstract page (no abstract
 * text reproduced). Attribution: "Data from arXiv.org" in the page footer.
 * The 30-min cache keeps us far under arXiv's requested rate limits.
 */
const ARXIV_URL =
  "https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG&sortBy=submittedDate&sortOrder=descending&max_results=6"

/** Minimal entity decode + whitespace collapse for Atom text nodes. */
function cleanText(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/\s+/g, " ")
    .trim()
}

export async function getLatestPapers(): Promise<Paper[]> {
  try {
    const res = await fetch(ARXIV_URL, {
      headers: { accept: "application/atom+xml" },
      next: { revalidate: REVALIDATE_SECONDS },
    })
    if (!res.ok) return []
    const xml = await res.text()

    const papers: Paper[] = []
    for (const [, entry] of xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)) {
      const title = entry.match(/<title>([\s\S]*?)<\/title>/)?.[1]
      const url = entry.match(/<id>(.*?)<\/id>/)?.[1]
      const published = entry.match(/<published>(.*?)<\/published>/)?.[1]
      const category =
        entry.match(/<arxiv:primary_category[^>]*term="([^"]+)"/)?.[1] ?? "cs"
      const authors = [...entry.matchAll(/<name>(.*?)<\/name>/g)].map(([, n]) =>
        cleanText(n),
      )
      if (!title || !url || !published) continue
      papers.push({
        url,
        title: cleanText(title),
        authors,
        published,
        category,
      })
    }
    return papers
  } catch {
    return []
  }
}
