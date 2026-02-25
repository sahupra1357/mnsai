import Link from "next/link"
import { Button } from "@/components/ui/button"
import WithSubnavigation from "@/components/common/with-subnavigation"

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <WithSubnavigation />

      {/* Hero Section */}
      <main className="flex flex-1 flex-col items-center justify-center px-6 text-center gap-6 py-20">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Welcome to{" "}
          <span className="text-ui-main">mnsAI</span>
        </h1>
        <p className="max-w-xl text-lg text-muted-foreground">
          Intelligent data extraction and management powered by AI.
          Sign in to access your dashboard, items, and settings.
        </p>
        <div className="flex gap-4">
          <Button asChild size="lg" className="bg-ui-main hover:bg-[#003d8f] text-white">
            <Link href="/login">Sign In</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/signup">Get Started</Link>
          </Button>
        </div>
      </main>
    </div>
  )
}
