import Link from "next/link"
import { Mail, Linkedin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { profile, contactBand } from "./profile-data"

export function ContactBand() {
  return (
    <section id="contact" className="px-6 py-20 bg-ui-main text-white text-center">
      <div className="mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold sm:text-4xl">{contactBand.heading}</h2>
        <p className="mt-4 text-blue-100 text-lg">{contactBand.sub}</p>

        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <Button
            asChild
            size="lg"
            className="bg-white text-ui-main hover:bg-blue-50 font-semibold px-8 h-12 rounded-lg"
          >
            <Link href={`mailto:${profile.email}`}>
              <Mail className="mr-2 h-4 w-4" /> {profile.email}
            </Link>
          </Button>
          <Button
            asChild
            size="lg"
            variant="outline"
            className="border-white text-white hover:bg-white/10 h-12 px-8 rounded-lg font-semibold bg-transparent"
          >
            <Link
              href={profile.linkedin}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Linkedin className="mr-2 h-4 w-4" /> LinkedIn
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}
