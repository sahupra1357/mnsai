import { ArrowLeft, ArrowRight, ChevronRight, Github } from "lucide-react"
import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { KnowledgeShell } from "@/components/knowledge/knowledge-shell"
import { KnowledgeMarkdown, outline } from "@/components/knowledge/markdown"
import { githubBlobUrl } from "@/lib/knowledge/source"
import { fetchDocMarkdown, locateDoc } from "@/lib/knowledge/tree"

/**
 * /learn/<repo path without .md> — one page of the AISystems repo, rendered in
 * the hub frame. Public. Pages render on first request and are then cached
 * for an hour (ISR); nothing is pre-built, so a file added to the repo needs
 * no deploy. Only paths in the repo tree resolve — anything else is a 404.
 */
export const revalidate = 3600
export const dynamicParams = true

export function generateStaticParams() {
  return []
}

type Params = { params: Promise<{ slug: string[] }> }

function slugOf(parts: string[]): string {
  return parts.map(decodeURIComponent).join("/")
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const found = await locateDoc(slugOf((await params).slug))
  if (!found) return { title: "Not found" }
  const { doc, section } = found
  const title = doc.title === "Overview" && section ? section.title : doc.title
  return {
    title: `${title} · AI Engineering Hub`,
    description: section?.blurb || undefined,
  }
}

export default async function LearnPage({ params }: Params) {
  const found = await locateDoc(slugOf((await params).slug))
  if (!found) notFound()
  const { doc, section, group, prev, next } = found

  const markdown = await fetchDocMarkdown(doc.path)
  const toc = markdown ? outline(markdown) : []

  const crumbs = [
    section ? { label: section.number != null ? `${section.number}. ${section.title}` : section.title, href: section.overview ? `/learn/${section.overview.slug}` : undefined } : { label: "Start here" },
    group && section && section.groups.length > 1 ? { label: group.title } : null,
  ].filter(Boolean) as Array<{ label: string; href?: string }>

  const navLabel = (d: typeof prev) =>
    d ? (d.title === "Overview" ? `Stage overview` : d.short) : ""

  return (
    <KnowledgeShell activeSlug={doc.slug}>
      <div className="flex gap-10 px-6 py-10 lg:px-10 2xl:px-14">
        <article className="min-w-0 flex-1">
          <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1 text-[12px] text-muted-foreground">
            <Link href="/" className="hover:text-foreground">Hub</Link>
            {crumbs.map((c) => (
              <span key={c.label} className="flex items-center gap-1">
                <ChevronRight className="h-3 w-3" />
                {c.href ? <Link href={c.href} className="hover:text-foreground">{c.label}</Link> : <span>{c.label}</span>}
              </span>
            ))}
          </nav>

          {markdown ? (
            <KnowledgeMarkdown markdown={markdown} docPath={doc.path} />
          ) : (
            <div className="rounded-lg border border-border p-8 text-center">
              <p className="font-semibold text-foreground">This page couldn&apos;t be loaded right now.</p>
              <p className="mt-2 text-sm text-muted-foreground">
                GitHub didn&apos;t answer. You can read it there directly.
              </p>
            </div>
          )}

          <div className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
            <a
              href={githubBlobUrl(doc.path)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
            >
              <Github className="h-3.5 w-3.5" /> View on GitHub
            </a>
          </div>

          <nav aria-label="Pagination" className="mt-6 grid gap-3 sm:grid-cols-2">
            {prev ? (
              <Link href={`/learn/${prev.slug}`} className="group rounded-lg border border-border p-4 transition-colors hover:border-ui-main/40">
                <span className="flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  <ArrowLeft className="h-3 w-3" /> Previous
                </span>
                <span className="mt-1 block text-sm font-medium text-foreground group-hover:text-ui-accent">{navLabel(prev)}</span>
              </Link>
            ) : <span />}
            {next ? (
              <Link href={`/learn/${next.slug}`} className="group rounded-lg border border-border p-4 text-right transition-colors hover:border-ui-main/40">
                <span className="flex items-center justify-end gap-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                  Next <ArrowRight className="h-3 w-3" />
                </span>
                <span className="mt-1 block text-sm font-medium text-foreground group-hover:text-ui-accent">{navLabel(next)}</span>
              </Link>
            ) : null}
          </nav>
        </article>

        {toc.length > 2 ? (
          <aside className="sticky top-[84px] hidden max-h-[calc(100vh-108px)] w-56 shrink-0 self-start overflow-y-auto xl:block">
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">On this page</p>
            <ul className="space-y-1 border-l border-border text-[12.5px]">
              {toc.map((h) => (
                <li key={`${h.id}-${h.depth}`}>
                  <a
                    href={`#${h.id}`}
                    className={`-ml-px block border-l border-transparent py-0.5 text-muted-foreground hover:border-ui-main hover:text-foreground ${h.depth === 3 ? "pl-6" : "pl-3"}`}
                  >
                    {h.text}
                  </a>
                </li>
              ))}
            </ul>
          </aside>
        ) : null}
      </div>
    </KnowledgeShell>
  )
}
