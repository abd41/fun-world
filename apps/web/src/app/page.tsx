import { BrowserTitles } from "@/components/BrowserTitles";
import { TitlesView } from "@/components/TitlesView";
import { loadTitles } from "@/lib/titles";

/**
 * Rendered on every request, never prerendered.
 *
 * SC-002 requires that changing a stored name and reloading shows the new name
 * with no code change and no redeployment. A statically prerendered page would
 * bake the catalogue in at build time and quietly fail that — and it would also
 * make `next build` reach out to the API, so a build with the server down would
 * fail for a reason that has nothing to do with the build.
 */
export const dynamic = "force-dynamic";

/** Resolved by `next.config.ts` from the single `FW_HOST`. Read here, in the
 *  server component, because this fetch leaves the machine running Next — a
 *  different network position from the browser (research R2). */
const INTERNAL_API_URL = process.env.API_URL_INTERNAL as string;

export default async function HomePage() {
  const result = await loadTitles(INTERNAL_API_URL);

  return (
    <main>
      <h1>Fun World</h1>

      <section>
        <h2>From the server</h2>
        <p>
          Fetched by a React Server Component from <code>API_URL_INTERNAL</code>.
        </p>
        <TitlesView result={result} baseUrl={INTERNAL_API_URL} />
      </section>

      <BrowserTitles />
    </main>
  );
}
