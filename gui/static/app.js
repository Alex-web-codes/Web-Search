"use strict";

const form = document.getElementById("search-form");
const input = document.getElementById("q");
const results = document.getElementById("results");
const statsLine = document.getElementById("stats");

const MAX_EXPANSIONS_SHOWN = 14;
let corpus = null;
let latestRequest = 0;

// --- helpers ----------------------------------------------------------------

function el(tag, className, ...children) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  for (const child of children) {
    if (child == null) continue;
    node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

const number = (n) => n.toLocaleString("en-US");
const plural = (n, word, many = word + "s") => `${number(n)} ${n === 1 ? word : many}`;

function show(...nodes) {
  results.replaceChildren(...nodes);
}

// Build the snippet text with <mark> around each [start, end) range.
function highlighted(text, ranges) {
  const p = el("p", "snippet");
  let cursor = 0;
  for (const [start, end] of ranges) {
    if (start > cursor) p.append(text.slice(cursor, start));
    p.append(el("mark", null, text.slice(start, end)));
    cursor = end;
  }
  p.append(text.slice(cursor));
  return p;
}

// --- rendering --------------------------------------------------------------

function renderIdle() {
  if (!corpus) return show();
  show(
    el("p", "summary", el("span", null, "Indexed documents"), el("span", "time", plural(corpus.documents, "file"))),
    el("ul", "doclist", ...corpus.names.map((name) => el("li", null, name))),
  );
}

function renderError(message) {
  show(el("p", "notice error", message));
}

function renderResults(data) {
  const count = data.hits.length;
  const nodes = [
    el(
      "p",
      "summary",
      el("span", null, count ? `${plural(count, "document")} for ` : "Nothing found for ", el("code", null, data.query)),
      el("span", "time", `${data.elapsed_ms.toFixed(2)} ms`),
    ),
  ];

  for (const [pattern, terms] of Object.entries(data.expansions)) {
    let list = terms.length ? terms.slice(0, MAX_EXPANSIONS_SHOWN).join(", ") : "no matching terms";
    if (terms.length > MAX_EXPANSIONS_SHOWN) list += ` and ${number(terms.length - MAX_EXPANSIONS_SHOWN)} more`;
    nodes.push(el("p", "expansion", el("code", null, pattern), el("span", "arrow", "→"), list));
  }

  if (!count) {
    nodes.push(el("p", "notice", "No document satisfies this query. Try OR instead of AND, or a wildcard."));
    return show(...nodes);
  }

  const list = el("ol", "hits");
  data.hits.forEach((hit, i) => {
    const meta = [hit.score ? plural(hit.score, "occurrence") : null, plural(hit.words, "word")];
    list.append(
      el(
        "li",
        "hit",
        el("span", "rank", String(i + 1).padStart(2, "0")),
        el(
          "div",
          null,
          el("h2", "doc", hit.name),
          highlighted(hit.snippet, hit.highlights),
          el("p", "meta", meta.filter(Boolean).join(" · ")),
        ),
      ),
    );
  });
  nodes.push(list);
  show(...nodes);
}

// --- data -------------------------------------------------------------------

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    corpus = await res.json();
    statsLine.textContent =
      `${plural(corpus.documents, "document")} · ${plural(corpus.terms, "term")} · ${plural(corpus.tokens, "token")}`;
    if (!input.value.trim()) renderIdle();
  } catch {
    statsLine.textContent = "Index unavailable";
  }
}

async function search(query, { updateHistory = true } = {}) {
  query = query.trim();
  if (!query) {
    input.focus();
    return;
  }

  if (updateHistory) {
    const url = new URL(location.href);
    url.searchParams.set("q", query);
    history.pushState({ q: query }, "", url);
  }

  const request = ++latestRequest;
  results.classList.add("is-loading");
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    if (request !== latestRequest) return; // a newer search has started
    data.error ? renderError(data.error) : renderResults(data);
  } catch {
    if (request === latestRequest) renderError("Couldn't reach the search server. Is run.py still running?");
  } finally {
    if (request === latestRequest) results.classList.remove("is-loading");
  }
}

// --- events -----------------------------------------------------------------

form.addEventListener("submit", (event) => {
  event.preventDefault();
  search(input.value);
});

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.query;
    search(input.value);
  });
});

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== input) {
    event.preventDefault();
    input.focus();
    input.select();
  }
});

window.addEventListener("popstate", () => {
  const q = new URL(location.href).searchParams.get("q") || "";
  input.value = q;
  q ? search(q, { updateHistory: false }) : renderIdle();
});

// --- start ------------------------------------------------------------------

const initial = new URL(location.href).searchParams.get("q");
if (initial) {
  input.value = initial;
  search(initial, { updateHistory: false });
}
loadStats();
