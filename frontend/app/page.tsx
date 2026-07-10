import WithSubnavigation from "@/components/common/with-subnavigation"
import { Hero } from "@/components/profile/hero"
import { ProofTiles } from "@/components/profile/proof-tiles"
import { SectionRail } from "@/components/profile/section-rail"
import { SectionHeading } from "@/components/profile/section-heading"
import { Services } from "@/components/profile/services"
import { Highlights } from "@/components/profile/highlights"
import { ProjectsShowcase } from "@/components/profile/projects-showcase"
import { SkillsGrid } from "@/components/profile/skills-grid"
import { ChatBox } from "@/components/profile/chat-box"
import { ChatLauncher } from "@/components/profile/chat-launcher"
import { ContactBand } from "@/components/profile/contact-band"
import { sections, profile, footer } from "@/lib/profile-data"

/**
 * v2 profile homepage — "evidence-driven dossier". Server component; only the
 * chat pieces and the scrollspy rail opt into "use client". All copy lives in
 * lib/profile-data.ts. Page stays public (not in middleware protected paths).
 */
export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <main className="flex-1">
        <Hero />
        <ProofTiles />

        {/* Editorial body: narrow reading column + sticky rail on xl+ */}
        <div className="mx-auto max-w-6xl px-6">
          <div className="xl:flex xl:gap-14">
            <div className="pt-16 xl:pt-20">
              <SectionRail />
            </div>

            <div className="mx-auto min-w-0 max-w-3xl space-y-24 py-16 xl:mx-0 xl:flex-1 xl:py-20">
              <Services />
              <Highlights />
              <ProjectsShowcase />
              <SkillsGrid />

              {/* Chat (UI stub until the chat-agent phase) */}
              <section id={sections.chat.id} className="scroll-mt-24">
                <SectionHeading meta={sections.chat} />
                <ChatBox />
              </section>
            </div>
          </div>
        </div>

        <ContactBand />
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-6 py-10">
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

      <ChatLauncher />
    </div>
  )
}
