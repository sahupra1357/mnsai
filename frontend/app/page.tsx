import WithSubnavigation from "@/components/common/with-subnavigation"
import { Hero } from "@/components/profile/hero"
import { SectionHeading } from "@/components/profile/section-heading"
import { Experience } from "@/components/profile/experience"
import { ProjectsGrid } from "@/components/profile/projects-grid"
import { Sharing } from "@/components/profile/sharing"
import { EducationCerts } from "@/components/profile/education-certs"
import { SkillsChips } from "@/components/profile/skills-chips"
import { PageRail } from "@/components/profile/page-rail"
import { ChatWidget } from "@/components/profile/chat-widget"
import { ContactBand } from "@/components/profile/contact-band"
import { sections, profile, footer } from "@/lib/profile-data"

/**
 * v3 profile homepage — "reference-format portfolio". Server component; only the
 * scrollspy rail and the floating chat widget opt into "use client". All copy
 * lives in lib/profile-data.ts, and empty arrays/nulls there drive the blank
 * placeholder slots. The chat exists ONLY as the floating widget — there is no
 * in-page chat section. Page stays public (not in middleware protected paths).
 */
export default function HomePage() {
  return (
    <div className="dossier-dots flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <main className="flex-1">
        <Hero />

        <div className="mx-auto max-w-6xl px-6">
          <div className="flex gap-10 py-20 sm:py-24">
            <PageRail />

            <div className="min-w-0 flex-1 space-y-24">
              <section id={sections.work.id} className="scroll-mt-24">
                <SectionHeading meta={sections.work} />
                <Experience />
              </section>

              <section id={sections.projects.id} className="scroll-mt-24">
                <SectionHeading meta={sections.projects} />
                <ProjectsGrid />
              </section>

              <section id={sections.sharing.id} className="scroll-mt-24">
                <SectionHeading meta={sections.sharing} />
                <Sharing />
              </section>

              <section id={sections.learning.id} className="scroll-mt-24">
                <SectionHeading meta={sections.learning} />
                <EducationCerts />
              </section>

              <section id={sections.skills.id} className="scroll-mt-24">
                <SectionHeading meta={sections.skills} />
                <SkillsChips />
              </section>
            </div>
          </div>
        </div>

        <ContactBand />
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-background px-6 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 sm:flex-row">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} {profile.name}. All rights
            reserved.
          </p>
          <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {footer.tagline}
          </p>
        </div>
      </footer>

      <ChatWidget />
    </div>
  )
}
