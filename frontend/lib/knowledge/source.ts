/**
 * Where the knowledge hub's content lives. The hub is a reader over this
 * repository: every markdown file in it becomes a page under /learn, and every
 * top-level stage folder becomes a section in the sidebar. Adding a file or a
 * stage to the repo is all it takes to publish it here — no code change.
 */
export const KNOWLEDGE_REPO = {
  owner: "sahupra1357",
  repo: "AISystems",
  branch: "main",
} as const

export const KNOWLEDGE_REPO_URL = `https://github.com/${KNOWLEDGE_REPO.owner}/${KNOWLEDGE_REPO.repo}`

/** Raw file host — not subject to the REST API's 60/hour anonymous limit. */
export const RAW_BASE = `https://raw.githubusercontent.com/${KNOWLEDGE_REPO.owner}/${KNOWLEDGE_REPO.repo}/${KNOWLEDGE_REPO.branch}`

/** GitHub's own view of a file, for "View on GitHub". */
export function githubBlobUrl(path: string): string {
  return `${KNOWLEDGE_REPO_URL}/blob/${KNOWLEDGE_REPO.branch}/${path}`
}

/** How long a fetched tree or document is reused before GitHub is asked again. */
export const KNOWLEDGE_REVALIDATE_SECONDS = 3600

/** Root-level documents promoted into a "Start here" section, in this order.
 *  Any other root markdown file (except README) is listed after them. */
export const START_HERE: Record<string, { title: string; blurb: string }> = {
  "AI_ENGINEERING_GUIDE.md": {
    title: "The AI Engineering Guide",
    blurb: "Every stage summarised, with the rules worth memorising.",
  },
  "AI_System.md": {
    title: "Field manual on one page",
    blurb: "The whole build order: ingest → parse → … → operate.",
  },
}
