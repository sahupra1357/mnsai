import Link from "next/link"
import { Mail, Linkedin, ArrowRight } from "lucide-react"
import { profile, contactBand } from "./profile-data"

/**
 * Closing contact band. A deliberate ui-main panel (the page's one saturated
 * moment) with a mono eyebrow, question heading, and two direct actions. Copy is
 * data-driven; LinkedIn from the draft, GitHub omitted ([NEEDS INPUT]).
 */
export function ContactBand() {
  return (
    <section id="contact" className="px-6 py-20 sm:py-24">
      <div className="mx-auto max-w-3xl overflow-hidden rounded-3xl bg-ui-main px-8 py-14 text-white sm:px-12">
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-white/70">
          {contactBand.eyebrow}
        </p>
        <h2 className="mt-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
          {contactBand.heading}
        </h2>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-blue-50/90">
          {contactBand.sub}
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <Link
            href={`mailto:${profile.email}`}
            className="group inline-flex items-center justify-center gap-2 rounded-md bg-white px-5 py-3 text-sm font-semibold text-ui-main transition-colors hover:bg-blue-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <Mail className="h-4 w-4" />
            {contactBand.emailCta}
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link
            href={profile.linkedin}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-white/40 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <Linkedin className="h-4 w-4" />
            {contactBand.linkedinCta}
          </Link>
          <span className="font-mono text-xs text-white/70 sm:ml-1">
            {profile.email}
          </span>
        </div>
      </div>
    </section>
  )
}
