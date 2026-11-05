import * as React from "react"

import { SearchResults, type ResultState } from "@/components/search-results"
import PushpinTearFooter, { type TearLink } from "@/components/ui/pushpin-tear-footer"
import { fetchStats, searchCorpus, type Stats } from "@/lib/api"

const REPO = "https://github.com/Alex-web-codes/Web-Search"
const LOCAL_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone

const initialQuery = () => new URLSearchParams(window.location.search).get("q") ?? ""

export default function App() {
  const [query, setQuery] = React.useState(initialQuery)
  const [stats, setStats] = React.useState<Stats | null>(null)
  const [result, setResult] = React.useState<ResultState>({ status: "idle" })
  const inputRef = React.useRef<HTMLInputElement>(null)
  const resultsRef = React.useRef<HTMLElement>(null)
  const latest = React.useRef(0)

  const showResults = React.useCallback(() => {
    resultsRef.current?.scrollIntoView({ block: "start" })
  }, [])

  const run = React.useCallback(
    async (raw: string, opts: { history?: boolean; scroll?: boolean } = {}) => {
      const q = raw.trim()
      if (!q) {
        inputRef.current?.focus()
        return
      }
      if (opts.history !== false) {
        const url = new URL(window.location.href)
        url.searchParams.set("q", q)
        window.history.pushState({ q }, "", url)
      }
      const id = ++latest.current
      setResult((prev) => ({ status: "loading", previous: prev.status === "done" ? prev.data : undefined }))
      if (opts.scroll !== false) showResults()
      try {
        const data = await searchCorpus(q)
        if (id === latest.current) setResult({ status: "done", data })
      } catch (err) {
        if (id === latest.current) setResult({ status: "error", message: (err as Error).message })
      }
    },
    [showResults],
  )

  // index stats, and a search from the URL on first load
  React.useEffect(() => {
    fetchStats().then(setStats, () => setStats(null))
    const q = initialQuery()
    if (q) run(q, { history: false, scroll: false })
  }, [run])

  // back / forward
  React.useEffect(() => {
    const onPop = () => {
      const q = initialQuery()
      setQuery(q)
      if (q) run(q, { history: false, scroll: false })
      else setResult({ status: "idle" })
    }
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [run])

  // "/" jumps to the search field
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === "/" && !typing) {
        e.preventDefault()
        window.scrollTo({ top: 0 })
        inputRef.current?.focus()
        inputRef.current?.select()
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const example = (q: string): TearLink => ({
    label: q,
    onClick: () => {
      setQuery(q)
      run(q)
    },
  })

  const hits = result.status === "done" ? result.data.hits.length : null

  return (
    <>
      <PushpinTearFooter
        as="header"
        brand="corpus."
        name="web search & mining"
        logo={<span style={{ fontSize: "1.5em", fontWeight: 600, letterSpacing: "-0.03em" }}>corpus.</span>}
        logoHref="/"
        sheet="#ff4a1c"
        paper="#f1ede4"
        paperInk="#1b1712"
        seed={23}
        email={null}
        copy={{ label: "copy search link", text: () => window.location.href, toast: "link copied" }}
        newsletter={null}
        search={{
          label: stats ? `search ${stats.documents} documents, boolean or wildcard` : "search the collection",
          placeholder: "index AND (boolean OR retriev*)",
          value: query,
          onChange: setQuery,
          onSubmit: (q) => run(q),
          buttonLabel: "Search",
          inputRef,
        }}
        status={{ label: stats ? "index ready" : "reading index", onClick: showResults }}
        mark={stats ? `${stats.terms} terms` : "indexing"}
        timeZone={LOCAL_ZONE}
        timeLabel="local"
        socials={[{ icon: "github", label: "Source on GitHub", href: REPO }]}
        columns={[
          {
            title: "boolean",
            links: [example("index AND postings"), example("crawler OR graph"), example("web AND NOT crawling")],
            cta: { label: "search.", onClick: () => inputRef.current?.focus() },
          },
          {
            title: "wildcard",
            links: [example("retriev*"), example("*ization"), example("r*v*l")],
            cta: { label: "results.", onClick: showResults },
          },
        ]}
        chat={{ label: hits === null ? "results" : `${hits} found`, onClick: showResults }}
        sideLinks={[
          { icon: "doc", label: "readme", href: REPO + "#readme" },
          { icon: "github", label: "source", href: REPO },
        ]}
        copyright="© 2026 web search & mining"
        credit="inverted index · k-gram wildcards"
        handle={{ label: "@Alex-web-codes", href: "https://github.com/Alex-web-codes" }}
      />

      <main>
        <SearchResults ref={resultsRef} state={result} documents={stats?.names} />
      </main>
    </>
  )
}
