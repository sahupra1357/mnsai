// Embeds the external Career Explorer Empowered by AI app (field exploration +
// course-driven college aggregator). The env var keeps its original
// NEXT_PUBLIC_COURSE_SEARCH_URL name so deployed environments don't need
// reconfiguring; only the user-facing labels name the current app.
export default function CareerExplorationPage() {
  const src = process.env.NEXT_PUBLIC_COURSE_SEARCH_URL

  if (!src) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-60px)] text-muted-foreground text-sm">
        Career Explorer Empowered by AI is not configured. Set{" "}
        <code className="mx-1 px-1 bg-muted rounded text-xs">
          NEXT_PUBLIC_COURSE_SEARCH_URL
        </code>{" "}
        in your environment.
      </div>
    )
  }

  return (
    <iframe
      src={src}
      className="w-full border-0"
      style={{ height: "calc(100vh - 60px)" }}
      title="Career Explorer Empowered by AI"
    />
  )
}
