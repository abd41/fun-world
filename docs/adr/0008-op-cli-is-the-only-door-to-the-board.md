# 0008. op-cli is the only door to the board

- **Status:** Accepted
- **Date:** 2026-08-27

## Context

Agents need to read and update work packages. The obvious options are giving
each agent the REST API, or running an MCP server in front of it.

An MCP server mirrors the API, and a mirror **cannot refuse an invalid
transition**. Every rule in `OWNERS.yml` and the constitution would degrade
into a suggestion an agent is asked to respect.

## Decision

Build **`op-cli`**, a thin Python CLI owning the integration. Agents never
touch the API directly.

It enforces what the constitution declares: `claim` refuses paths the agent
does not own and refuses a ticket with no paths at all; `split` derives
children from `OWNERS.yml`; `bug` demands two reproductions and a cited
acceptance criterion, and reopens rather than re-files; `block` escalates
past the handoff limit.

This mirrors the existing `browser-test-agent` pattern: a standalone tool,
outside every repo, knowing nothing about business logic, driven via Bash.

## Consequences

- Rules sit in front of the API, where they can actually refuse.
- One API key, one place to change behaviour.
- Written in Python, serving the learning goal.
- **Cost:** a tool to maintain; agents cannot do board things it has not
  been taught.
- **Cost:** its error messages *are* the agent's user interface, so they
  must be instructive rather than merely correct.
