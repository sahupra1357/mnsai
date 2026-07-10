// Frozen snapshot of the first profile-page draft (v1) — kept for design comparison.
// Do not evolve this page; the live profile is frontend/app/page.tsx.
import WithSubnavigation from "@/components/common/with-subnavigation"
import { Hero } from "./_components/hero"
import { SkillsGrid } from "./_components/skills-grid"
import { Services } from "./_components/services"
import { ProjectsShowcase } from "./_components/projects-showcase"
import { ChatBox } from "./_components/chat-box"
import { ChatLauncher } from "./_components/chat-launcher"
import { ContactBand } from "./_components/contact-band"
import { chatSection } from "./_components/profile-data"

export const metadata = {
  title: "Profile v1 (1st draft) — Pradeep Sahu",
  robots: { index: false, follow: false },
}

export default function DraftProfileV1Page() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      <div className="bg-amber-100 dark:bg-amber-950 text-amber-900 dark:text-amber-200 text-center text-xs py-1.5 px-4">
        Archived 1st draft of the profile page — the live version is on the homepage.
      </div>

      <Hero />
      <SkillsGrid />
      <Services />
      <ProjectsShowcase />

      {/* ── Chat ── */}
      <section id="chat" className="px-6 py-20 scroll-mt-20">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">
              {chatSection.heading}
            </h2>
            <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
              {chatSection.sub}
            </p>
          </div>
          <ChatBox />
        </div>
      </section>

      <ContactBand />

      {/* ── Footer ── */}
      <footer className="px-6 py-8 border-t text-center text-sm text-muted-foreground">
        &copy; {new Date().getFullYear()} Pradeep Sahu. All rights reserved.
      </footer>

      <ChatLauncher />
    </div>
  )
}
