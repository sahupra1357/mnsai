// Embeds the external vecsearch app — semantic/hybrid search over documents.
// Unlike the other embeds this one has a working public default, so it renders
// without any environment setup; NEXT_PUBLIC_SIMILARITY_SEARCH_URL overrides it
// (e.g. to point at a local instance during development).
const DEFAULT_SRC = "https://similaritysearch-x84d.onrender.com"

export default function SimilaritySearchPage() {
  const src = process.env.NEXT_PUBLIC_SIMILARITY_SEARCH_URL || DEFAULT_SRC

  return (
    <iframe
      src={src}
      className="w-full border-0"
      style={{ height: "calc(100vh - 60px)" }}
      title="Semantic Document Search"
    />
  )
}
