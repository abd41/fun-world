"use client";

/**
 * The browser half of research R2.
 *
 * The page above this renders from a server component using
 * `API_URL_INTERNAL`. That address is resolved on the machine running Next and
 * says nothing about whether a browser — on a laptop, or on the LG television —
 * can reach the API itself. This island asks that question from the browser,
 * with `NEXT_PUBLIC_API_URL`.
 *
 * It exists so the second variable is exercised rather than declared. R2's
 * warning is that collapsing the two produces "works in the browser, 500s on
 * hard refresh"; an app that never fetches from the browser would satisfy the
 * letter of the split while proving nothing about it, and the day someone adds
 * the first client fetch is the day they find out.
 *
 * It is a button rather than an effect on mount: the page must render its
 * answer on the server, and a second automatic fetch would make it ambiguous
 * which context produced what is on screen.
 *
 * ## Known to fail today, and that is the point
 *
 * Verified 2026-08-28 against the running API, driving headless Chrome over the
 * DevTools protocol from origin `http://<FW_HOST>:3002`:
 *
 *     Access to fetch at 'http://<FW_HOST>:8000/api/titles' from origin
 *     'http://<FW_HOST>:3002' has been blocked by CORS policy: No
 *     'Access-Control-Allow-Origin' header is present on the requested
 *     resource.
 *     corsErrorStatus = { corsError: "MissingAllowOriginHeader" }
 *
 * The API sends no CORS headers and answers a preflight `OPTIONS` with 405.
 * Web and API are always different origins here — the same host on different
 * ports, 3000 and 8000 in normal use, 3002 and 8000 in the run quoted above —
 * so every browser-side call is blocked, and this button reports "cannot reach
 * the server" while the server is healthy.
 *
 * That is an `apps/api` change and `web-agent` may not make it (§8), so it is
 * reported rather than worked around. Nothing in `apps/web` can fix it: a proxy
 * route here would hide the gap by turning the browser call back into a
 * server-side one, which is the opposite of what this component is for.
 *
 * The component is deliberately left in place as the canary. When CORS is
 * configured on the API this button starts returning titles with no change to
 * this file — and if this paragraph still describes reality then, it means
 * nobody has closed the gap yet.
 */
import { useState } from "react";

import { TitlesView } from "@/components/TitlesView";
import { loadTitles, type TitlesResult } from "@/lib/titles";

// Next replaces this expression with a string literal at build time, driven by
// the `env` key in `next.config.ts`. Verified against a production build: the
// address appears in exactly one file under `.next/static/chunks/`, and
// `process.env.NEXT_PUBLIC_API_URL` appears in none of them.
//
// The `as string` is a CAST, not a check — it asserts nothing and would happily
// let `undefined` through. What actually guarantees a value is `env.config.ts`,
// which throws at config load rather than resolving to a blank URL. If that
// guard is ever removed, this line goes back to being a silent `undefined`.
const BROWSER_API_URL = process.env.NEXT_PUBLIC_API_URL as string;

type State = { phase: "idle" } | { phase: "loading" } | { phase: "done"; result: TitlesResult };

export function BrowserTitles() {
  const [state, setState] = useState<State>({ phase: "idle" });

  async function check() {
    setState({ phase: "loading" });
    setState({ phase: "done", result: await loadTitles(BROWSER_API_URL) });
  }

  return (
    <section>
      <h2>From this browser</h2>
      <p>
        Fetched by the browser from <code>NEXT_PUBLIC_API_URL</code>, which is a
        different network position from the server component above.
      </p>
      <button type="button" onClick={check} disabled={state.phase === "loading"}>
        {state.phase === "loading" ? "Checking…" : "Fetch titles from this browser"}
      </button>
      {state.phase === "done" && (
        <TitlesView result={state.result} baseUrl={BROWSER_API_URL} />
      )}
    </section>
  );
}
