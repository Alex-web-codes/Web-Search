// Client for the Python server in gui/server.py.

export type Hit = {
  doc_id: number
  name: string
  score: number
  words: number
  snippet: string
  highlights: [number, number][]
}

export type SearchResponse = {
  query: string
  hits: Hit[]
  expansions: Record<string, string[]>
  elapsed_ms: number
}

export type Stats = {
  documents: number
  terms: number
  tokens: number
  k: number
  names: string[]
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch("/api/stats")
  if (!res.ok) throw new Error("Couldn't load the index.")
  return res.json()
}

export async function searchCorpus(query: string): Promise<SearchResponse> {
  let res: Response
  try {
    res = await fetch("/api/search?q=" + encodeURIComponent(query))
  } catch {
    throw new Error("Couldn't reach the search server. Is run.py still running?")
  }
  const body = await res.json()
  if (!res.ok) throw new Error(body.error ?? "Search failed.")
  return body
}
