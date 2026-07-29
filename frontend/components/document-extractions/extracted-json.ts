import type { ExtractedElement, PageResult } from "./types"

type ExtractedContent = Record<string, unknown>

const KNOWN_LABELS = new Set([
  "address",
  "certifications",
  "currently",
  "education",
  "email",
  "experience",
  "github",
  "languages",
  "linkedin",
  "location",
  "name",
  "phone",
  "projects",
  "role",
  "skills",
  "summary",
  "title",
  "website",
])

function elementText(element: ExtractedElement) {
  return (element.reviewed_text || element.text).trim()
}

function tableRows(text: string) {
  const rows = text
    .split("\n")
    .map((line) => line.trim().replace(/^\||\|$/g, ""))
    .filter(Boolean)
    .map((line) =>
      line
        .split(/\t+|\s*\|\s*|\s{2,}/)
        .map((cell) => cell.trim())
        .filter(Boolean),
    )
  return rows.length > 0 ? rows : [[text]]
}

function keyFor(value: string) {
  return (
    value
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "field"
  )
}

function sameVisualLine(left: ExtractedElement, right: ExtractedElement) {
  if (!left.bounding_box || !right.bounding_box) return false
  const overlap =
    Math.min(left.bounding_box.bottom, right.bounding_box.bottom) -
    Math.max(left.bounding_box.top, right.bounding_box.top)
  const smallerHeight = Math.min(
    left.bounding_box.bottom - left.bounding_box.top,
    right.bounding_box.bottom - right.bounding_box.top,
  )
  return smallerHeight > 0 && overlap / smallerHeight >= 0.5
}

function tesseractLines(elements: ExtractedElement[]) {
  if (elements.some((element) => element.source_line_number != null)) {
    const groups = new Map<string, ExtractedElement[]>()
    for (const element of elements) {
      const key = [
        element.source_block_number ?? 0,
        element.source_paragraph_number ?? 0,
        element.source_line_number ?? 0,
      ].join(":")
      groups.set(key, [...(groups.get(key) ?? []), element])
    }
    return [...groups.entries()]
      .sort(([left], [right]) => {
        const a = left.split(":").map(Number)
        const b = right.split(":").map(Number)
        return a[0] - b[0] || a[1] - b[1] || a[2] - b[2]
      })
      .map(([, words]) =>
        words
          .sort(
            (left, right) =>
              (left.source_word_number ?? left.reading_order) -
              (right.source_word_number ?? right.reading_order),
          )
          .map(elementText)
          .filter(Boolean)
          .join(" "),
      )
  }
  if (
    elements.length > 0 &&
    elements.every((element) => !element.bounding_box)
  ) {
    return [elements.map(elementText).filter(Boolean).join(" ")]
  }
  const lines: ExtractedElement[][] = []
  for (const element of elements) {
    const current = lines.at(-1)
    if (!current || !sameVisualLine(current[current.length - 1], element)) {
      lines.push([element])
    } else {
      current.push(element)
    }
  }
  return lines.map((line) =>
    [...line]
      .sort(
        (left, right) =>
          (left.bounding_box?.left ?? left.reading_order) -
          (right.bounding_box?.left ?? right.reading_order),
      )
      .map(elementText)
      .filter(Boolean)
      .join(" "),
  )
}

function tesseractParagraphs(elements: ExtractedElement[]) {
  if (!elements.some((element) => element.source_line_number != null))
    return tesseractLines(elements)
  const groups = new Map<string, ExtractedElement[]>()
  for (const element of elements) {
    const key = [
      element.source_block_number ?? 0,
      element.source_paragraph_number ?? 0,
    ].join(":")
    groups.set(key, [...(groups.get(key) ?? []), element])
  }
  return [...groups.entries()]
    .sort(([left], [right]) => {
      const a = left.split(":").map(Number)
      const b = right.split(":").map(Number)
      return a[0] - b[0] || a[1] - b[1]
    })
    .map(([, words]) => {
      const lines = new Map<number, ExtractedElement[]>()
      for (const word of words) {
        const line = word.source_line_number ?? 0
        lines.set(line, [...(lines.get(line) ?? []), word])
      }
      return [...lines.entries()]
        .sort(([left], [right]) => left - right)
        .map(([, lineWords]) =>
          lineWords
            .sort(
              (left, right) =>
                (left.source_word_number ?? left.reading_order) -
                (right.source_word_number ?? right.reading_order),
            )
            .map(elementText)
            .filter(Boolean)
            .join(" "),
        )
        .filter(Boolean)
        .join(" ")
    })
    .filter(Boolean)
}

function orderedSections(lines: string[]): ExtractedContent {
  const sections: Array<Record<string, unknown>> = []
  let pendingLabel: string | null = null

  for (const line of lines) {
    const clean = line.trim()
    if (!clean) continue
    if (pendingLabel) {
      sections.push({ type: pendingLabel, text: clean })
      pendingLabel = null
      continue
    }
    const colonMatch = clean.match(
      /^([A-Za-z][A-Za-z0-9 /&_-]{0,40})\s*:\s*(.+)$/,
    )
    if (colonMatch) {
      sections.push({
        type: keyFor(colonMatch[1]),
        text: colonMatch[2].trim(),
      })
      continue
    }
    const words = clean.split(/\s+/)
    const possiblePrefix = keyFor(words[0])
    if (KNOWN_LABELS.has(possiblePrefix) && words.length > 1) {
      sections.push({
        type: possiblePrefix,
        text: words.slice(1).join(" "),
      })
      continue
    }
    const possibleLabel = keyFor(clean.replace(/:$/, ""))
    if (KNOWN_LABELS.has(possibleLabel) && words.length <= 3) {
      pendingLabel = possibleLabel
      continue
    }
    sections.push({ type: "paragraph", text: clean })
  }

  if (pendingLabel) {
    sections.push({
      type: "heading",
      text: pendingLabel
        .replaceAll("_", " ")
        .replace(/\b\w/g, (value) => value.toUpperCase()),
    })
  }
  return { sections }
}

export function pageExtractedContent(page: PageResult): ExtractedContent {
  if (page.semantic_result?.final_content)
    return page.semantic_result.final_content
  const sections: Array<Record<string, unknown>> = []
  const words: ExtractedElement[] = []
  const isTesseract = page.selected_parser?.name === "tesseract"
  for (const element of [...page.elements].sort(
    (left, right) => left.reading_order - right.reading_order,
  )) {
    const text = elementText(element)
    if (!text) continue
    if (isTesseract && element.type === "paragraph") {
      words.push(element)
      continue
    }
    if (element.type === "table" || element.type === "table_cell") {
      sections.push({ type: "table", rows: tableRows(text) })
      continue
    }
    sections.push({ type: element.type, text })
  }

  if (words.length > 0)
    return orderedSections(tesseractParagraphs(words))
  return { sections }
}
