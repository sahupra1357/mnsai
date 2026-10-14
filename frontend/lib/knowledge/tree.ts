import { cache } from "react"
import snapshot from "./snapshot.json"
import {
  KNOWLEDGE_REPO,
  KNOWLEDGE_REVALIDATE_SECONDS,
  RAW_BASE,
  START_HERE,
} from "./source"

/**
 * Builds the knowledge hub's table of contents from the AISystems repo.
 *
 * The file list comes from GitHub's tree API, so anything added to the repo
 * appears here on the next revalidation with no code change. Titles and
 * reading order come from the repo's own README files (the root README's
 * stage table, and each stage README's link list); a file the READMEs don't
 * mention yet still appears, titled from its filename, in natural sort order.
 *
 * Resilience: if the tree API is unreachable or rate-limited (60 anonymous
 * calls/hour, shared per egress IP on a PaaS), the bundled `snapshot.json` is
 * used instead, so the sidebar never comes back empty. Refresh it with
 *   gh api "repos/sahupra1357/AISystems/git/trees/main?recursive=1" \
 *     --jq '[.tree[] | select(.type=="blob" and (.path|endswith(".md"))) | .path]' \
 *     > lib/knowledge/snapshot.json
 */

export type KDoc = {
  /** Repo path, e.g. "06-rag/apply/2-chunking/04.1.1_fixed_size_overlap.md". */
  path: string
  /** URL path under /learn — the repo path without ".md"; a stage README is its folder. */
  slug: string
  /** Full title, number stripped. */
  title: string
  /** Sidebar label: the specific topic after the last "→", when there is one. */
  short: string
  /** Leading section number, e.g. "04.1.1" or "6.1". */
  number?: string
}

export type KGroup = {
  key: string
  title: string
  kind: "learn" | "apply" | "other"
  docs: KDoc[]
}

export type KSection = {
  /** Top-level folder, e.g. "06-rag". Also the stage overview's slug. */
  key: string
  number: number | null
  title: string
  blurb: string
  overview?: KDoc
  groups: KGroup[]
  learnCount: number
  applyCount: number
}

export type KTree = {
  start: KDoc[]
  sections: KSection[]
  /** Every page in reading order — drives prev/next. */
  flat: KDoc[]
  source: "live" | "snapshot"
}

const collator = new Intl.Collator("en", { numeric: true, sensitivity: "base" })

export function slugForPath(path: string): string {
  const noExt = path.replace(/\.md$/i, "")
  return noExt.replace(/\/README$/i, "")
}

/** Splits "Lesson 6.1 — RAG Deep Dive" / "0.1.1 Source ingestion → X" /
 *  "05.10_sandboxing" into a number and the rest. */
function splitNumber(text: string): { number?: string; rest: string } {
  const m = text.match(/^(?:lesson\s+)?(\d+(?:\.\d+)*)\.?(?:\s*[—–-]\s*|\s+|_)(.+)$/i)
  if (m) return { number: m[1], rest: m[2].trim() }
  return { rest: text.trim() }
}

function humanize(name: string): string {
  const words = name.replace(/[_-]+/g, " ").trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function titleFromFilename(path: string): string {
  const base = path.split("/").pop()!.replace(/\.md$/i, "")
  return humanize(splitNumber(base).rest)
}

function makeDoc(path: string, linkText: string | undefined): KDoc {
  const base = path.split("/").pop()!.replace(/\.md$/i, "")
  const fromFile = splitNumber(base)
  const fromLink = linkText ? splitNumber(linkText) : undefined
  const title = fromLink?.rest || titleFromFilename(path)
  const arrow = title.lastIndexOf("→")
  const short = arrow >= 0 ? title.slice(arrow + 1).trim() : title
  return {
    path,
    slug: slugForPath(path),
    title,
    short,
    number: fromLink?.number ?? fromFile.number,
  }
}

async function fetchText(url: string, init?: RequestInit): Promise<string | null> {
  try {
    const res = await fetch(url, {
      ...init,
      next: { revalidate: KNOWLEDGE_REVALIDATE_SECONDS },
    })
    return res.ok ? await res.text() : null
  } catch {
    return null
  }
}

async function fetchPaths(): Promise<{ paths: string[]; source: KTree["source"] }> {
  const { owner, repo, branch } = KNOWLEDGE_REPO
  const headers: Record<string, string> = { Accept: "application/vnd.github+json" }
  // Optional: lifts the anonymous 60/hour limit. Read server-side only.
  if (process.env.GITHUB_TOKEN) headers.Authorization = `Bearer ${process.env.GITHUB_TOKEN}`

  const body = await fetchText(
    `https://api.github.com/repos/${owner}/${repo}/git/trees/${branch}?recursive=1`,
    { headers },
  )
  if (body) {
    try {
      const json = JSON.parse(body) as { tree?: Array<{ path: string; type: string }> }
      const paths = (json.tree ?? [])
        .filter((e) => e.type === "blob" && /\.md$/i.test(e.path))
        .map((e) => e.path)
      if (paths.length > 0) return { paths, source: "live" }
    } catch {
      // fall through to the snapshot
    }
  }
  return { paths: snapshot as string[], source: "snapshot" }
}

/** Every `[text](target.md)` in a README, resolved against its folder, in order. */
function parseLinks(markdown: string, dir: string): Map<string, { text: string; order: number }> {
  const out = new Map<string, { text: string; order: number }>()
  const re = /\[([^\]]+)\]\(([^)#\s]+\.md)(?:#[^)]*)?\)/g
  let m: RegExpExecArray | null
  let order = 0
  while ((m = re.exec(markdown))) {
    const resolved = new URL(m[2], `https://x/${dir ? `${dir}/` : ""}`).pathname.slice(1)
    if (!out.has(resolved)) out.set(resolved, { text: m[1].replace(/`/g, ""), order: order++ })
  }
  return out
}

/** Root README's stage table: `| 6 | [RAG](06-rag/README.md) | What it covers |`. */
function parseStageTable(markdown: string): Map<string, { title: string; blurb: string }> {
  const out = new Map<string, { title: string; blurb: string }>()
  const re = /^\|\s*\d+\s*\|\s*\[([^\]]+)\]\(([^/)]+)\/README\.md\)\s*\|\s*([^|]+)\|/gm
  let m: RegExpExecArray | null
  while ((m = re.exec(markdown))) out.set(m[2], { title: m[1].trim(), blurb: m[3].trim() })
  return out
}

function groupFor(rest: string): { key: string; title: string; kind: KGroup["kind"] } {
  const parts = rest.split("/")
  if (parts[0] === "learn") return { key: "learn", title: "Learn", kind: "learn" }
  if (parts[0] === "apply") {
    if (parts.length <= 2) return { key: "apply", title: "Apply", kind: "apply" }
    const sub = parts[1]
    const name = humanize(sub.replace(/^\d+-/, "")).replace(/\bGpu\b|\bgpu\b/g, "GPU")
    return { key: `apply/${sub}`, title: name, kind: "apply" }
  }
  return { key: "other", title: "More", kind: "other" }
}

const KIND_ORDER: Record<KGroup["kind"], number> = { learn: 0, apply: 1, other: 2 }

export const getKnowledgeTree = cache(async (): Promise<KTree> => {
  const { paths, source } = await fetchPaths()

  const rootDocs = paths.filter((p) => !p.includes("/") && !/^README\.md$/i.test(p))
  const sectionKeys = [...new Set(paths.filter((p) => p.includes("/")).map((p) => p.split("/")[0]))]
    .filter((k) => !k.startsWith("."))

  const readmes = await Promise.all([
    fetchText(`${RAW_BASE}/README.md`),
    ...sectionKeys.map((k) =>
      paths.includes(`${k}/README.md`) ? fetchText(`${RAW_BASE}/${k}/README.md`) : null,
    ),
  ])
  const stageMeta = parseStageTable(readmes[0] ?? "")
  const rootLinks = parseLinks(readmes[0] ?? "", "")

  const start = rootDocs
    .sort((a, b) => {
      const ia = Object.keys(START_HERE).indexOf(a)
      const ib = Object.keys(START_HERE).indexOf(b)
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || collator.compare(a, b)
    })
    .map((p) => {
      const doc = makeDoc(p, START_HERE[p]?.title ?? rootLinks.get(p)?.text)
      return doc
    })

  const sections: KSection[] = sectionKeys.map((key, i) => {
    const links = parseLinks(readmes[i + 1] ?? "", key)
    const numMatch = key.match(/^(\d+)-/)
    const meta = stageMeta.get(key)
    const groups = new Map<string, KGroup>()
    let overview: KDoc | undefined

    for (const p of paths) {
      if (!p.startsWith(`${key}/`)) continue
      const rest = p.slice(key.length + 1)
      if (/^README\.md$/i.test(rest)) {
        overview = { ...makeDoc(p, undefined), title: "Overview", short: "Overview", number: undefined }
        continue
      }
      const g = groupFor(rest)
      if (!groups.has(g.key)) groups.set(g.key, { ...g, docs: [] })
      groups.get(g.key)!.docs.push(makeDoc(p, links.get(p)?.text))
    }

    const sortedGroups = [...groups.values()].sort(
      (a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || collator.compare(a.key, b.key),
    )
    for (const g of sortedGroups) {
      g.docs.sort((a, b) => {
        const oa = links.get(a.path)?.order ?? Number.MAX_SAFE_INTEGER
        const ob = links.get(b.path)?.order ?? Number.MAX_SAFE_INTEGER
        return oa - ob || collator.compare(a.path, b.path)
      })
    }

    const count = (kind: KGroup["kind"]) =>
      sortedGroups.filter((g) => g.kind === kind).reduce((n, g) => n + g.docs.length, 0)

    return {
      key,
      number: numMatch ? Number(numMatch[1]) : null,
      title: meta?.title ?? humanize(key.replace(/^\d+-/, "")),
      blurb: meta?.blurb ?? "",
      overview,
      groups: sortedGroups,
      learnCount: count("learn"),
      applyCount: count("apply") + count("other"),
    }
  })

  sections.sort(
    (a, b) => (a.number ?? Number.MAX_SAFE_INTEGER) - (b.number ?? Number.MAX_SAFE_INTEGER) ||
      collator.compare(a.key, b.key),
  )

  const flat: KDoc[] = [
    ...start,
    ...sections.flatMap((s) => [
      ...(s.overview ? [s.overview] : []),
      ...s.groups.flatMap((g) => g.docs),
    ]),
  ]

  return { start, sections, flat, source }
})

export type KLocated = {
  doc: KDoc
  section?: KSection
  group?: KGroup
  prev?: KDoc
  next?: KDoc
}

/** Resolves a /learn slug to a known page. Only paths present in the tree are
 *  ever fetched, so the route can't be used to pull arbitrary URLs. */
export async function locateDoc(slug: string): Promise<KLocated | null> {
  const tree = await getKnowledgeTree()
  const idx = tree.flat.findIndex((d) => d.slug === slug)
  if (idx < 0) return null
  const doc = tree.flat[idx]
  const section = tree.sections.find((s) => doc.path.startsWith(`${s.key}/`))
  const group = section?.groups.find((g) => g.docs.some((d) => d.path === doc.path))
  return { doc, section, group, prev: tree.flat[idx - 1], next: tree.flat[idx + 1] }
}

export async function fetchDocMarkdown(path: string): Promise<string | null> {
  return fetchText(`${RAW_BASE}/${path.split("/").map(encodeURIComponent).join("/")}`)
}
