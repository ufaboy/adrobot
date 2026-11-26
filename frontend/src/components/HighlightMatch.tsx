interface HighlightMatchProps {
  text: string
  query: string
}

/** Renders `text` with every case-insensitive occurrence of `query` emphasized. */
export function HighlightMatch({ text, query }: HighlightMatchProps) {
  const needle = query.trim().toLowerCase()
  if (!needle) return <>{text}</>

  const parts: { text: string; match: boolean }[] = []
  const haystack = text.toLowerCase()
  let start = 0
  for (let at = haystack.indexOf(needle); at !== -1; at = haystack.indexOf(needle, start)) {
    if (at > start) parts.push({ text: text.slice(start, at), match: false })
    parts.push({ text: text.slice(at, at + needle.length), match: true })
    start = at + needle.length
  }
  if (start < text.length) parts.push({ text: text.slice(start), match: false })

  return (
    <>
      {parts.map((part, i) =>
        part.match ? (
          <mark key={i} className="bg-transparent font-semibold text-foreground">
            {part.text}
          </mark>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </>
  )
}
