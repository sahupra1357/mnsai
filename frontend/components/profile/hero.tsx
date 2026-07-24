import Image from "next/image"
import { Sparkles } from "lucide-react"
import {
  profile,
  heroChips,
  featuredIn,
  featuredInLabel,
  featuredInPlaceholder,
} from "@/lib/profile-data"
import { getProfileHeadshotUrl } from "@/lib/profile-image"

/**
 * v3 reference-format hero: two columns. Left is a large circular avatar — the
 * headshot uploaded in User Settings → Profile photo, falling back to the
 * static `profile.headshot` path and then to an initials ring when neither
 * exists. Right is a greeting line, a huge gradient display headline of the
 * specialty, bold foreground descriptor lines, role-descriptor pill chips, and
 * an "As featured in" slot that renders a blank dashed placeholder (no press
 * yet). Server component; the dot-grid background is theme-aware.
 */
export async function Hero() {
  // Resolved on the server so a missing photo renders the initials ring rather
  // than a broken image. `unoptimized` because the bytes come from the API
  // proxy, already sized for an avatar, and are cache-busted by ?v=.
  const uploadedHeadshot = await getProfileHeadshotUrl()
  const headshot = uploadedHeadshot ?? profile.headshot

  return (
    <section className="relative overflow-hidden border-b border-border bg-background">
      <div
        aria-hidden
        className="dossier-dots dossier-dots-mask pointer-events-none absolute inset-0"
      />
      {/* Soft brand wash behind the hero */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-ui-accent/[0.07] via-transparent to-cyan-500/[0.06]"
      />

      <div className="relative mx-auto flex max-w-6xl flex-col items-center gap-10 px-6 pb-20 pt-20 sm:pt-24 lg:flex-row lg:items-center lg:gap-14">
        {/* Avatar */}
        <div className="relative shrink-0">
          <div className="relative flex h-40 w-40 items-center justify-center rounded-full bg-gradient-to-br from-ui-accent/20 to-cyan-400/20 p-1.5 shadow-xl shadow-ui-accent/10 ring-1 ring-border sm:h-48 sm:w-48">
            {headshot ? (
              <Image
                src={headshot}
                alt={profile.name}
                fill
                unoptimized={Boolean(uploadedHeadshot)}
                sizes="(min-width: 640px) 12rem, 10rem"
                className="rounded-full object-cover p-1.5"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-[#0f766e] to-[#06b6d4]">
                <span className="font-display text-5xl font-bold tracking-tight text-white sm:text-6xl">
                  {profile.initials}
                </span>
              </div>
            )}
          </div>
          <span className="absolute bottom-2 right-2 flex h-10 w-10 items-center justify-center rounded-full bg-ui-main text-white shadow-lg ring-4 ring-background">
            <Sparkles className="h-4 w-4" />
          </span>
        </div>

        {/* Text column */}
        <div className="min-w-0 flex-1 text-center lg:text-left">
          <p className="text-base text-muted-foreground sm:text-lg">
            {profile.greeting}
          </p>

          <h1 className="mt-2 font-display text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            <span className="bg-gradient-to-r from-[#0f766e] via-[#0d9488] to-[#0891b2] bg-clip-text text-transparent dark:from-[#2dd4bf] dark:via-[#22d3ee] dark:to-[#38bdf8]">
              {profile.headlineAccent}
            </span>
          </h1>

          <p className="mt-4 font-display text-2xl font-semibold leading-snug tracking-tight text-foreground sm:text-3xl">
            {profile.headlineLines.map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </p>

          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground lg:mx-0">
            {profile.supportingLine}
          </p>

          {/* Role-descriptor chips */}
          <ul className="mt-6 flex flex-wrap justify-center gap-2 lg:justify-start">
            {heroChips.map((chip) => (
              <li
                key={chip}
                className="rounded-full border border-border bg-card px-3.5 py-1.5 text-sm font-medium text-foreground shadow-sm"
              >
                {chip}
              </li>
            ))}
          </ul>

          {/* As featured in — blank placeholder until press exists */}
          <div className="mt-10">
            <p className="text-center font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground/70 lg:text-left">
              {featuredInLabel}
            </p>
            {featuredIn.length === 0 ? (
              <div className="mt-3 flex items-center justify-center gap-2 rounded-xl border border-dashed border-border/80 bg-muted/20 px-4 py-3 text-sm text-muted-foreground/70 lg:justify-start">
                {featuredInPlaceholder}
              </div>
            ) : (
              <div className="mt-3 flex flex-wrap items-center justify-center gap-6 lg:justify-start">
                {featuredIn.map((item) => (
                  <span key={item.name} className="text-sm font-semibold text-muted-foreground">
                    {item.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
