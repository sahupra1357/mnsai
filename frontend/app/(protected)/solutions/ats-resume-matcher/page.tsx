export default function AtsResumeMatcherPage() {
  const src = process.env.NEXT_PUBLIC_ATS_RESUME_MATCHER_URL

  if (!src) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-60px)] text-muted-foreground text-sm">
        ATS Resume Matcher is not configured. Set{" "}
        <code className="mx-1 px-1 bg-muted rounded text-xs">
          NEXT_PUBLIC_ATS_RESUME_MATCHER_URL
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
      title="ATS Resume Matcher"
    />
  )
}
