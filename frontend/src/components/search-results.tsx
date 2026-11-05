import * as React from "react"

import type { Hit, SearchResponse } from "@/lib/api"
import { cn } from "@/lib/utils"

export type ResultState =
  | { status: "idle" }
  | { status: "loading"; previous?: SearchResponse }
  | { status: "done"; data: SearchResponse }
  | { status: "error"; message: string }

const MAX_EXPANSIONS = 14

const plural = (n: number, word: string) => `${n.toLocaleString("en-US")} ${n === 1 ? word : word + "s"}`

/** Read-only result area, printed on the same paper as the poster above it. */
export const SearchResults = React.forwardRef<HTMLElement, { state: ResultState; documents?: string[] }>(
  function SearchResults({ state, documents = [] }, ref) {
    const data = state.status === "done" ? state.data : state.status === "loading" ? state.previous : undefined

    let right = data ? `${data.elapsed_ms.toFixed(2)} ms` : plural(documents.length, "document")
    if (state.status === "error") right = "query error"

    return (
      <section
        ref={ref}
        id="results"
        aria-label="Search results"
        aria-live="polite"
        aria-busy={state.status === "loading"}
        className="mx-auto max-w-3xl scroll-mt-6 px-5 pt-16 pb-28 sm:px-8 sm:pt-24"
      >
        <div className="flex items-end justify-between gap-6 border-b border-ink pb-4">
          <h2 className="text-[clamp(2.75rem,8vw,4.75rem)] leading-[.9] font-medium tracking-[-0.055em]">results.</h2>
          <p className="pb-1 text-[11px] tracking-[.08em] text-ink-faint uppercase tabular-nums">{right}</p>
        </div>

        <div className={cn("transition-opacity duration-200", state.status === "loading" && "opacity-40")}>
          {state.status === "error" ? (
            <p key="error" className="rise mt-8 text-lg text-sheet">{state.message}</p>
          ) : data ? (
            <Found key={data.query + data.elapsed_ms} data={data} />
          ) : (
            <Idle documents={documents} />
          )}
        </div>
      </section>
    )
  },
)

function Idle({ documents }: { documents: string[] }) {
  return (
    <div className="rise">
      <p className="mt-8 max-w-md text-lg leading-snug text-ink-soft">
        Nothing searched yet. Type a query on the poster, or pick one of its examples.
      </p>
      {documents.length > 0 && (
        <>
          <p className="mt-12 text-[11px] tracking-[.08em] text-ink-faint uppercase">Indexed documents</p>
          <ul className="mt-3 grid gap-x-10 border-t border-rule sm:grid-cols-2">
            {documents.map((name) => (
              <li key={name} className="border-b border-rule py-2.5 text-[15px] text-ink-soft">
                {name}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function Found({ data }: { data: SearchResponse }) {
  const count = data.hits.length
  return (
    <div className="rise">
      <p className="mt-6 text-[15px] text-ink-soft">
        {count ? plural(count, "document") : "Nothing"} for{" "}
        <span className="rounded-full bg-ink/[.06] px-2.5 py-0.5 text-ink">{data.query}</span>
      </p>

      {Object.entries(data.expansions).map(([pattern, terms]) => (
        <p key={pattern} className="mt-2 text-[13px] leading-relaxed text-ink-faint">
          <span className="text-ink">{pattern}</span>
          <span className="px-2">→</span>
          {terms.length ? terms.slice(0, MAX_EXPANSIONS).join(", ") : "no matching terms"}
          {terms.length > MAX_EXPANSIONS && ` and ${terms.length - MAX_EXPANSIONS} more`}
        </p>
      ))}

      {count === 0 ? (
        <p className="mt-10 max-w-md text-lg leading-snug text-ink-soft">
          No document satisfies this query. Try OR instead of AND, or a wildcard.
        </p>
      ) : (
        <ol className="mt-6 border-t border-rule">
          {data.hits.map((hit, i) => (
            <Result key={hit.doc_id} hit={hit} rank={i + 1} />
          ))}
        </ol>
      )}
    </div>
  )
}

function Result({ hit, rank }: { hit: Hit; rank: number }) {
  const meta = [hit.score ? plural(hit.score, "occurrence") : null, plural(hit.words, "word")].filter(Boolean)
  return (
    <li className="grid grid-cols-[2.75rem_1fr] border-b border-rule py-6 sm:grid-cols-[4rem_1fr]">
      <span className="pt-0.5 text-sm text-sheet tabular-nums">{String(rank).padStart(2, "0")}</span>
      <div>
        <h3 className="text-[17px] font-medium tracking-[-0.01em]">{hit.name}</h3>
        <p className="mt-1.5 text-[15px] leading-[1.65] text-ink-soft">
          <Highlighted text={hit.snippet} ranges={hit.highlights} />
        </p>
        <p className="mt-2.5 text-[11px] tracking-[.08em] text-ink-faint uppercase">{meta.join(" · ")}</p>
      </div>
    </li>
  )
}

function Highlighted({ text, ranges }: { text: string; ranges: [number, number][] }) {
  const parts: React.ReactNode[] = []
  let cursor = 0
  ranges.forEach(([start, end], i) => {
    if (start > cursor) parts.push(text.slice(cursor, start))
    parts.push(
      <mark key={i} className="rounded-[3px] bg-sheet/15 px-0.5 text-ink">
        {text.slice(start, end)}
      </mark>,
    )
    cursor = end
  })
  parts.push(text.slice(cursor))
  return <>{parts}</>
}
