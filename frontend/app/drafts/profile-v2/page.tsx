// Frozen snapshot of the second profile-page draft (v2, "evidence-driven dossier").
// Kept for design comparison. Do not evolve this page; the live profile is
// frontend/app/page.tsx.
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Hero } from "./_components/hero"
import { ProofTiles } from "./_components/proof-tiles"
import { SectionRail } from "./_components/section-rail"
import { SectionHeading } from "./_components/section-heading"
import { Services } from "./_components/services"
import { Highlights } from "./_components/highlights"
import { ProjectsShowcase } from "./_components/projects-showcase"
import { SkillsGrid } from "./_components/skills-grid"
import { ChatBox } from "./_components/chat-box"
import { ChatLauncher } from "./_components/chat-launcher"
import { ContactBand } from "./_components/contact-band"
import { sections, profile, footer } from "./_components/profile-data"

export const metadata = {
  title: "Profile v2 (2nd draft) — Pradeep Sahu",
  robots: { index: false, follow: false },
}

export default function DraftProfileV2Page() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <WithSubnavigation />

      <div className="bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 text-center text-xs py-1.5 px-4">
        Archived 2nd draft of the profile page — the live version is on the homepage.
      </div>

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
