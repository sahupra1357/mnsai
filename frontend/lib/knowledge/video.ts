/**
 * Video embeds for repo lessons. A lesson embeds a video by putting the link
 * on a line of its own; the renderer swaps that paragraph for a player. On
 * GitHub the same line is still a plain, clickable link — which is why this is
 * a link convention rather than raw <iframe>/<video> HTML, which the renderer
 * deliberately does not allow from remote content.
 */
export type VideoEmbed =
  | { kind: "iframe"; src: string; provider: "YouTube" | "Vimeo" }
  | { kind: "file"; src: string }

const YOUTUBE_ID = /^[\w-]{11}$/

function youtubeId(url: URL): string | null {
  const host = url.hostname.replace(/^(www\.|m\.)/, "")
  let id: string | null = null
  if (host === "youtu.be") {
    id = url.pathname.slice(1).split("/")[0]
  } else if (host === "youtube.com" || host === "youtube-nocookie.com") {
    if (url.pathname === "/watch") id = url.searchParams.get("v")
    else {
      const m = url.pathname.match(/^\/(?:embed|shorts|live)\/([^/]+)/)
      id = m ? m[1] : null
    }
  }
  return id && YOUTUBE_ID.test(id) ? id : null
}

/** YouTube's `t=` / `start=` as seconds: "90", "90s", "1m30s", "1h2m3s". */
function startSeconds(url: URL): number | null {
  const raw = url.searchParams.get("t") ?? url.searchParams.get("start")
  if (!raw) return null
  if (/^\d+$/.test(raw)) return Number(raw)
  const m = raw.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$/)
  if (!m || !m[0]) return null
  return Number(m[1] ?? 0) * 3600 + Number(m[2] ?? 0) * 60 + Number(m[3] ?? 0)
}

/**
 * The embed for an already-resolved absolute URL, or null when it is not a
 * recognised video. Direct files must be .mp4/.webm/.ogg/.mov.
 */
export function videoEmbed(href: string): VideoEmbed | null {
  let url: URL
  try {
    url = new URL(href)
  } catch {
    return null
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") return null

  const yt = youtubeId(url)
  if (yt) {
    const start = startSeconds(url)
    return {
      kind: "iframe",
      provider: "YouTube",
      // The no-cookie host: no tracking cookies until the visitor presses play.
      src: `https://www.youtube-nocookie.com/embed/${yt}${
        start ? `?start=${start}` : ""
      }`,
    }
  }

  const host = url.hostname.replace(/^www\./, "")
  if (host === "vimeo.com" || host === "player.vimeo.com") {
    const m = url.pathname.match(/(?:^|\/)(\d{6,})(?:\/|$)/)
    if (m) {
      return {
        kind: "iframe",
        provider: "Vimeo",
        src: `https://player.vimeo.com/video/${m[1]}?dnt=1`,
      }
    }
  }

  if (/\.(mp4|webm|ogg|mov)$/i.test(url.pathname)) {
    return { kind: "file", src: url.toString() }
  }
  return null
}
