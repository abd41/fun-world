/**
 * The one place the three outcomes are turned into words.
 *
 * Shared by the server component and the client island so that "no titles yet"
 * and "cannot reach the server" cannot drift apart between the two fetch
 * contexts. Two wordings for the same state would be a slower version of the
 * bug FR-008 is about.
 *
 * No styling, deliberately: vertical 001 is proving the wiring, and the design
 * system arrives in vertical 002. `packages/tokens` is empty, and §14 fails the
 * build on a literal colour — so there is no legitimate way to style this yet,
 * and unstyled text is the correct output rather than a shortcut.
 */
import type { TitlesResult } from "@/lib/titles";

export function TitlesView({
  result,
  baseUrl,
}: {
  result: TitlesResult;
  /** Shown only in the unreachable message, so the reader can see which
   *  address failed. It comes from the environment; §7 forbids writing one
   *  down here. */
  baseUrl: string;
}) {
  // `data-state` is a stable hook for the end-to-end tests qa-agent owns.
  // Asserting on prose would make every wording change a test failure, and
  // asserting on nothing is how "both messages are the same" ships.
  if (result.state === "unreachable") {
    return (
      <div data-state="unreachable">
        <p>
          <strong>Cannot reach the server.</strong> The catalogue is unavailable
          because the request to the API failed. This is not an empty
          catalogue — nothing came back at all, so check that the API is
          running and reachable at the address below.
        </p>
        <p>
          Tried <code>{baseUrl}/api/titles</code>
        </p>
        <p>
          <small>{result.detail}</small>
        </p>
      </div>
    );
  }

  if (result.state === "empty") {
    return (
      <div data-state="empty">
        <p>
          <strong>No titles yet.</strong> The server answered normally and the
          catalogue is empty. Nothing is broken — add a title in the Django
          admin and reload this page.
        </p>
      </div>
    );
  }

  return (
    <div data-state="ok">
      <ul>
        {result.titles.map((title) => (
          <li key={title.id}>{title.name}</li>
        ))}
      </ul>
    </div>
  );
}
