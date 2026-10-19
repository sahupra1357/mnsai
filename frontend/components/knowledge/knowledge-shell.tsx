import WithSubnavigation from "@/components/common/with-subnavigation"
import { MobileSidebar } from "@/components/knowledge/mobile-sidebar"
import {
  KnowledgeSidebar,
  type SidebarProject,
} from "@/components/knowledge/sidebar"
import { getKnowledgeTree } from "@/lib/knowledge/tree"
import { SOLUTIONS, solutionNavHref, solutionStatus } from "@/lib/solutions"

/**
 * Docs-style frame shared by the hub home ("/") and every lesson
 * ("/learn/..."): the site nav on top, the folding table of contents on the
 * left (a drawer below lg), the page on the right.
 */
export async function KnowledgeShell({
  activeSlug,
  children,
}: {
  activeSlug?: string
  children: React.ReactNode
}) {
  const tree = await getKnowledgeTree()
  // Icons are components and can't cross into the client sidebar; it only
  // needs a name, a destination and a status.
  const projects: SidebarProject[] = SOLUTIONS.map((s) => ({
    title: s.title,
    // Same rule as the nav: a tool without a route lands on its card.
    href: solutionNavHref(s),
    status: solutionStatus(s),
  }))
  const sidebarProps = {
    start: tree.start,
    sections: tree.sections,
    projects,
    activeSlug,
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <div className="flex w-full flex-1">
        <aside className="sticky top-[60px] hidden h-[calc(100vh-60px)] w-72 shrink-0 overflow-y-auto lg:block">
          <KnowledgeSidebar {...sidebarProps} />
        </aside>

        <div className="min-w-0 flex-1">
          <MobileSidebar {...sidebarProps} />
          {children}
        </div>
      </div>
    </div>
  )
}
