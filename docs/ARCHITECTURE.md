# Fun World — Architecture

A private home streaming app. One laptop is the server; phones, laptops and
four televisions are the clients. Nothing is reachable from the public
internet, and nothing costs money to run.

Five views, from the house down to the database. Diagrams render on GitHub and
in VS Code's Markdown preview. The full designed plan — decisions, tradeoffs,
constraints and build order — is [`docs/build-plan.html`](build-plan.html);
open it in a browser.

| | |
|---|---|
| **API** | Django 6.0 + django-ninja, Python 3.13, uv |
| **Web** | Next.js 16 (also the LG webOS client) |
| **Phone + TV** | Expo SDK 57 — one build covers Fire TV, Google TV, Android TV |
| **Database** | PostgreSQL 17 (Docker, `:5433`) |
| **Video** | ffmpeg → HLS on disk, served by Caddy (`:8090`) |
| **Auth** | Own OAuth 2.1 (PKCE + RFC 8628 device grant), later Keycloak |
| **Contracts** | Generated from OpenAPI 3.1 by `@hey-api/openapi-ts` |
| **Board** | Self-hosted OpenProject 17 (`:8080`, loopback only) |

The rules everything obeys: [`.specify/memory/constitution.md`](../.specify/memory/constitution.md)
and [`OWNERS.yml`](../OWNERS.yml).

---

## 1. Where things run

```mermaid
flowchart LR
  subgraph HOME["Home network — nothing is publicly reachable"]
    direction LR
    subgraph LAPTOP["Laptop — the only server"]
      direction TB
      WEB["Next.js 16<br/>:3000"]
      API["Django 6 + django-ninja<br/>:8000"]
      PG[("Postgres 17<br/>:5433")]
      HLS["Caddy — HLS files<br/>:8090"]
      KC["Keycloak<br/>phase 2"]
      OP["OpenProject<br/>:8080 · loopback only"]
      API --> PG
      API -. "signs playback URLs" .-> HLS
      API -. "validates JWT" .-> KC
    end
    PHONE["Phone<br/>Expo 57"]
    TVA["Fire TV · Google TV · Android TV<br/>Expo TV build"]
    TVL["LG webOS<br/>Next.js in the TV browser"]
    DESK["Laptop browser"]
  end

  DESK --> WEB
  PHONE --> API
  PHONE --> HLS
  TVA --> API
  TVA --> HLS
  TVL --> WEB
  WEB --> API

  TS(["Tailscale — only devices you enrol,<br/>peer-to-peer, nothing exposed"])
  TS -. "when away from home" .-> API

  NET(["Public internet"])
  NET x-.-x HOME

  classDef server fill:#fdf3e0,stroke:#c08a3e,color:#3a2c14
  classDef store fill:#e3efec,stroke:#4b9184,color:#12332e
  classDef client fill:#eef1f4,stroke:#8b98a6,color:#1b2430
  classDef blocked fill:#fbe6e3,stroke:#c0655a,color:#3d1a16
  class WEB,API,HLS,KC,OP server
  class PG store
  class PHONE,TVA,TVL,DESK client
  class NET blocked
```

Three of the four televisions are Android-based, so a single Expo build covers
Fire TV, Google TV and Android TV; LG webOS runs the Next.js app in its browser
instead. OpenProject binds to loopback only — the televisions never need the
ticket system. The crossed edge is the point: no path from the public internet
reaches anything here.

## 2. How the code fits together

```mermaid
flowchart TB
  subgraph PY["apps/api — Python"]
    direction LR
    CORE["core<br/>models · admin"]
    CAT["catalog"]
    PRO["profiles"]
    PRG["progress"]
    SRCH["search"]
    OAUTH["oauth<br/>PKCE · device grant"]
  end

  OPENAPI[/"openapi.json<br/>3.1, auto-derived"/]
  PY --> OPENAPI

  subgraph SHARED["packages — shared, one writer each"]
    direction LR
    CONTRACTS["contracts<br/>GENERATED"]
    TOKENS["tokens<br/>one source of colour"]
    UISPEC["ui-spec<br/>component contracts"]
    PLAYER["player-core<br/>progress · resume"]
  end

  OPENAPI -- "hey-api codegen" --> CONTRACTS

  subgraph TS["apps — TypeScript"]
    direction LR
    NEXT["web · Next.js 16"]
    EXPO["mobile · Expo 57"]
    TVUI["mobile/src/tv<br/>D-pad, 10-foot"]
  end

  CONTRACTS --> NEXT
  CONTRACTS --> EXPO
  TOKENS --> NEXT
  TOKENS --> EXPO
  UISPEC --> NEXT
  UISPEC --> EXPO
  PLAYER --> NEXT
  PLAYER --> EXPO
  EXPO --- TVUI

  GATE{{"CI gate: regenerate,<br/>git diff must be empty"}}
  CONTRACTS -.-> GATE

  classDef py fill:#e3efec,stroke:#4b9184,color:#12332e
  classDef shared fill:#fdf3e0,stroke:#c08a3e,color:#3a2c14
  classDef ts fill:#eef1f4,stroke:#8b98a6,color:#1b2430
  classDef gate fill:#fbe6e3,stroke:#c0655a,color:#3d1a16
  class CORE,CAT,PRO,PRG,SRCH,OAUTH py
  class CONTRACTS,TOKENS,UISPEC,PLAYER shared
  class NEXT,EXPO,TVUI ts
  class GATE gate
```

The seam between Python and TypeScript is **generated, not written**. Because
the API is Python and both clients are TypeScript, shared types come out of the
OpenAPI document rather than being hand-maintained — and the CI gate turns
drift into a build failure rather than a code-review comment.

## 3. Watching something on the television

```mermaid
sequenceDiagram
  autonumber
  participant TV as Android TV
  participant Ph as Your phone
  participant Auth as Django /oauth
  participant API as Django API
  participant CDN as Caddy (HLS)

  Note over TV,Ph: No keyboard on the TV — RFC 8628 device grant
  TV->>Auth: POST /device/code
  Auth-->>TV: user_code WXYZ-1234 + verification_uri + interval
  TV->>TV: displays the code
  Ph->>Auth: opens the URI, enters the code, approves
  loop every `interval` seconds
    TV->>Auth: POST /token (device_code)
    Auth-->>TV: authorization_pending
  end
  Auth-->>TV: access JWT (10 min) + rotating refresh

  TV->>API: GET /titles/42  (Bearer)
  API-->>TV: metadata + episode list
  TV->>API: POST /playback/42/authorize
  API-->>TV: HMAC-signed master.m3u8 URL, short expiry
  TV->>CDN: GET master.m3u8  (signature checked)
  CDN-->>TV: variant playlists — 1080/720/480/360
  loop every 10s while playing
    TV->>API: PUT /progress {title, position}
  end
  Note over API: continue-watching now resolves on<br/>the phone and the laptop too
```

The television never handles a credential. It holds a device code, then tokens.
The secret is typed on a device that has a keyboard — which is why every real
streaming service works this way (RFC 8628), and why implementing it is the
most directly useful auth exercise in this project.

Note the polling interval is **server-dictated**. Ignoring it earns `slow_down`;
the correct response is to back off, not to tighten the loop.

## 4. How work reaches an agent

```mermaid
flowchart TB
  SPEC["/speckit.specify<br/>spec.md"] --> PLAN["/speckit.plan<br/>plan.md"]
  PLAN --> TASKS["/speckit.tasks<br/>tasks.md"]
  TASKS -- "op-cli sync" --> WP[("OpenProject<br/>work packages")]

  WP --> ROUTE{{"route by Paths<br/>OWNERS.yml lookup"}}
  ROUTE -- "one owner" --> CLAIM["op-cli claim<br/>→ In progress"]
  ROUTE -- "two or more" --> SPLIT["op-cli split<br/>one child per owner"]
  SPLIT --> ROUTE

  CLAIM --> WORK["agent works<br/>inside its allowlist"]
  WORK --> GUARD{{"pre-commit guard<br/>FW_AGENT vs OWNERS.yml"}}
  GUARD -- "outside boundary" --> REJECT["rejected"]
  GUARD -- "ok" --> PR["pull request<br/>OP#id in the body"]
  PR --> DONE["op-cli done<br/>→ In testing"]

  DONE --> QA["qa-agent<br/>browser-test-agent run"]
  QA -- "passes" --> HUMAN{{"you review<br/>and merge"}}
  HUMAN --> CLOSED(["Closed"])
  QA -- "fails" --> BUG["op-cli bug<br/>routed by failing path"]
  BUG --> WP

  ESC([">3 handoffs → On hold,<br/>assigned to you"])
  BUG -.-> ESC

  classDef spec fill:#eef1f4,stroke:#8b98a6,color:#1b2430
  classDef gate fill:#fbe6e3,stroke:#c0655a,color:#3d1a16
  classDef act fill:#fdf3e0,stroke:#c08a3e,color:#3a2c14
  classDef store fill:#e3efec,stroke:#4b9184,color:#12332e
  class SPEC,PLAN,TASKS spec
  class ROUTE,GUARD,HUMAN gate
  class CLAIM,SPLIT,WORK,PR,DONE,QA,BUG act
  class WP,CLOSED,REJECT,ESC store
```

**No agent ever picks a recipient.** The only way work reaches a second agent is
a path lookup in `OWNERS.yml`, which is a pure function — the same paths always
resolve to the same owner, so a hand-off loop has nowhere to form. The one case
that *can* cycle (fix → retest → still red) is caught by the handoff counter,
which escalates to a human at 3.

An agent that cannot finish a ticket does not pass it on. It **splits** it, and
each child routes independently.

## 5. The content model

```mermaid
erDiagram
  ACCOUNT ||--o{ PROFILE : "up to 5"
  PROFILE ||--o{ PROGRESS : "resume points"
  PROFILE ||--o{ MYLIST : "saved"
  PROFILE ||--o{ DOWNLOAD : "offline, mobile only"

  TITLE ||--o{ SEASON : "series only"
  SEASON ||--o{ EPISODE : has
  TITLE }o--o{ GENRE : "tagged"
  TITLE ||--o{ ARTWORK : "billboard · poster · still"

  TITLE ||--o| RENDITION : "film"
  EPISODE ||--o| RENDITION : "episode"
  RENDITION ||--o{ VARIANT : "1080 · 720 · 480 · 360"
  RENDITION ||--o{ SUBTITLE : "vtt tracks"

  PROGRESS }o--|| RENDITION : "position in"
  MYLIST }o--|| TITLE : references

  PROFILE {
    uuid id
    string name
    bool kids_mode
    string pin_hash
  }
  TITLE {
    uuid id
    string name
    string kind "film or series"
    int year
    string licence "CC-BY"
    string attribution
  }
  RENDITION {
    uuid id
    int duration_s
    string hls_path
  }
  PROGRESS {
    uuid profile_id
    uuid rendition_id
    int position_s
    datetime updated_at
  }
```

Progress is keyed on the **rendition**, not the title — so an episode resumes
where you left that episode, rather than where you left the series. `licence`
and `attribution` are columns rather than documentation, because CC-BY requires
the credit to actually be shown to the viewer.

---

## Constraints worth knowing before you touch anything

**Your phone cannot reach `localhost`.** The Expo app on a physical device is a
different machine. Bind services to `0.0.0.0`, put the LAN IP (or the Tailscale
MagicDNS name) in env, and open the Windows Firewall ports. The HLS base URL
needs the same treatment, or video plays on the laptop and fails on the TV.

**RSC and a separate API need a deliberate token handoff.** Next.js server
components cannot see a browser-held token. Get this wrong and pages render on
client navigation but 401 on hard refresh. The httpOnly cookie in the auth
design is what solves it.

**Television is a third interaction model, not a re-skin.** D-pad focus, 10-foot
type, overscan-safe margins, no hover. The "same UI, colours change" guarantee
stops at the TV — deliberately.

**NativeWind v5 is a preview track.** It is what gives Tailwind v4 syntax on
native. The token package can emit both formats, so reversing this is a config
change rather than a rewrite.
