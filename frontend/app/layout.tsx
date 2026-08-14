import type { Metadata } from "next"
import localFont from "next/font/local"
import "./globals.css"
import { Providers } from "./providers"

// Fonts are self-hosted from ./fonts rather than pulled via `next/font/google`.
// The Google loader fetches the .woff2 files from fonts.gstatic.com during
// `next build`, so a CDN hiccup (Google rotating the hashed filenames while the
// CSS API still advertises the old ones) fails the whole build — which is what
// broke the Docker image. These are the latin-subset variable files; to refresh
// one, re-download it from the css2 API and drop it in place.
const inter = localFont({
  src: "./fonts/inter-latin-var.woff2",
  weight: "100 900",
  style: "normal",
  variable: "--font-inter",
  display: "swap",
})

const spaceGrotesk = localFont({
  src: "./fonts/space-grotesk-latin-var.woff2",
  weight: "300 700",
  style: "normal",
  variable: "--font-space-grotesk",
  display: "swap",
})

const jetbrainsMono = localFont({
  src: "./fonts/jetbrains-mono-latin-var.woff2",
  weight: "100 800",
  style: "normal",
  variable: "--font-jetbrains-mono",
  display: "swap",
})

export const metadata: Metadata = {
  title: "mnsAI",
  description: "mnsAI Platform",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
