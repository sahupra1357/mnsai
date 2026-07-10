import Link from "next/link"
import { Sparkles, MessageCircle, Mail } from "lucide-react"
import { Button } from "@/components/ui/button"
import { profile, credentials } from "./profile-data"

export function Hero() {
  return (
    <section className="relative flex flex-col items-center justify-center text-center px-6 pt-24 pb-16 overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(0,74,173,0.12) 0%, transparent 70%)",
        }}
      />

      <span className="inline-flex items-center gap-2 rounded-full border border-ui-main/20 bg-ui-main/5 px-4 py-1.5 text-xs font-semibold text-ui-main uppercase tracking-widest mb-6">
        <Sparkles className="h-3.5 w-3.5" />
        {profile.eyebrow}
      </span>

      <h1 className="text-5xl font-extrabold tracking-tight text-foreground sm:text-6xl lg:text-7xl max-w-4xl leading-tight">
        {profile.name}
      </h1>

      <p className="mt-4 text-lg font-semibold text-ui-main sm:text-xl">
        {profile.title}
      </p>

      <p className="mt-6 max-w-2xl text-lg text-muted-foreground leading-relaxed">
        {profile.valueProposition}
      </p>

      <p className="mt-3 max-w-2xl text-base text-muted-foreground/90 leading-relaxed">
        {profile.supportingLine}
      </p>

      <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
        <Button
          asChild
          size="lg"
          className="bg-ui-main hover:bg-[#003d8f] text-white font-semibold px-8 h-12 rounded-lg shadow-md"
        >
          <a href="#chat">
            <MessageCircle className="mr-2 h-4 w-4" /> Ask my AI assistant
          </a>
        </Button>
        <Button
          asChild
          size="lg"
          variant="outline"
          className="h-12 px-8 rounded-lg font-semibold"
        >
          <Link href={`mailto:${profile.email}`}>
            <Mail className="mr-2 h-4 w-4" /> Contact
          </Link>
        </Button>
      </div>

      {/* Credentials strip */}
      <div className="mt-12 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 max-w-3xl">
        {credentials.map(({ icon: Icon, label }) => (
          <span
            key={label}
            className="inline-flex items-center gap-2 text-xs sm:text-sm text-muted-foreground"
          >
            <Icon className="h-4 w-4 text-ui-main shrink-0" />
            {label}
          </span>
        ))}
      </div>
    </section>
  )
}
