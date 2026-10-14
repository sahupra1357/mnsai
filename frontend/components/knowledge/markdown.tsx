import Link from "next/link"
import type { ReactNode } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { slugForPath } from "@/lib/knowledge/tree"
import { githubBlobUrl, RAW_BASE } from "@/lib/knowledge/source"

/** GitHub's heading-anchor rule, so `file.md#8-stage-6-...` links land. */
export function headingId(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/\s/g, "-")
}

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node)
  if (Array.isArray(node)) return node.map(textOf).join("")
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children)
  }
  return ""
}

/** Where a link inside the repo's markdown should go on this site. */
function resolveHref(
  href: string,
  docPath: string,
): { href: string; internal: boolean } {
  if (href.startsWith("#")) return { href, internal: true }
  if (/^[a-z]+:/i.test(href)) return { href, internal: false }
  const url = new URL(href, `https://repo/${docPath}`)
  const path = decodeURIComponent(url.pathname.slice(1))
  if (/\.md$/i.test(path)) {
    const slug = slugForPath(path)
    // The root README is the hub home itself.
    return {
      href: (slug === "README" ? "/" : `/learn/${slug}`) + url.hash,
      internal: true,
    }
  }
  // Folders, code and anything else: GitHub renders those better than we would.
  return { href: githubBlobUrl(path) + url.hash, internal: false }
}

function heading(Tag: "h1" | "h2" | "h3" | "h4") {
  return function Heading({ children }: { children?: ReactNode }) {
    const id = headingId(textOf(children))
    return (
      <Tag id={id} className="group scroll-mt-20">
        {children}
        <a
          href={`#${id}`}
          aria-hidden
          tabIndex={-1}
          className="ml-2 font-normal no-underline opacity-0 transition-opacity group-hover:opacity-40"
        >
          #
        </a>
      </Tag>
    )
  }
}

export function KnowledgeMarkdown({
  markdown,
  docPath,
}: { markdown: string; docPath: string }) {
  const components: Components = {
    h1: heading("h1"),
    h2: heading("h2"),
    h3: heading("h3"),
    h4: heading("h4"),
    a({ href = "", children }) {
      const r = resolveHref(href, docPath)
      return r.internal ? (
        <Link href={r.href}>{children}</Link>
      ) : (
        <a href={r.href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
    img({ src = "", alt }) {
      const url =
        typeof src === "string" && !/^[a-z]+:/i.test(src)
          ? `${RAW_BASE}/${new URL(
              src,
              `https://repo/${docPath}`,
            ).pathname.slice(1)}`
          : String(src)
      // biome-ignore lint/performance/noImgElement: arbitrary remote repo images; next/image would need every host allow-listed
      return <img src={url} alt={alt ?? ""} loading="lazy" />
    },
    table({ children }) {
      return (
        <div className="not-prose my-6 overflow-x-auto rounded-lg border border-border">
          <table className="w-full border-collapse text-left text-[13px] [&_td]:border-t [&_td]:border-border [&_td]:px-3 [&_td]:py-2 [&_td]:align-top [&_th]:bg-muted/60 [&_th]:px-3 [&_th]:py-2 [&_th]:font-semibold">
            {children}
          </table>
        </div>
      )
    },
  }

  return (
    <div className="prose prose-slate max-w-none dark:prose-invert prose-headings:font-display prose-headings:tracking-tight prose-a:text-ui-accent prose-a:no-underline hover:prose-a:underline prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-normal prose-code:before:content-none prose-code:after:content-none prose-pre:border prose-pre:border-border prose-pre:bg-muted/50 prose-pre:text-foreground prose-pre:text-[12.5px] prose-pre:leading-relaxed prose-blockquote:font-normal prose-blockquote:not-italic prose-blockquote:border-l-ui-main/50 prose-blockquote:text-muted-foreground [&_blockquote_p]:before:content-none [&_blockquote_p]:after:content-none [&_pre_code]:bg-transparent [&_pre_code]:p-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

/** h2/h3 outline for "On this page", skipping fenced code. */
export function outline(
  markdown: string,
): Array<{ depth: 2 | 3; text: string; id: string }> {
  const out: Array<{ depth: 2 | 3; text: string; id: string }> = []
  let fenced = false
  for (const line of markdown.split("\n")) {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced
    if (fenced) continue
    const m = line.match(/^(##|###)\s+(.+?)\s*#*\s*$/)
    if (!m) continue
    // Strip inline markdown so the label and id match the rendered heading.
    const text = m[2]
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/[`*]/g, "")
    out.push({ depth: m[1].length as 2 | 3, text, id: headingId(text) })
  }
  return out
}
