# ADR: Download Architecture – Throttle & Persistence

- **Date**: 2025-10-29
- **Status**: Accepted

## Context

The playlist downloader must run large archival jobs without re-downloading completed
videos, while avoiding provider bans triggered by aggressive concurrency. Early
scaffolding provided only placeholder throttling and did not coordinate persistence
with retry/backoff behaviour, making it difficult to guarantee safe resumable runs.

## Decision

1. Introduce an application-level `ThrottleController` that wraps each download slot
   with a bounded semaphore, configurable sleep interval, and exponential backoff
   whenever simulated ban signals occur. The controller exposes structured
   `ThrottleMetrics` so CLI and reporting flows can show compliance ratios.
2. Extend configuration (`ThrottleSettings`) with ban backoff parameters,
   compliance thresholds, and keep defaults conservative (2 concurrent downloads,
   1 s sleep, 1 s initial backoff).
3. Persist per-session throttle outcomes by appending to
   `reports/throttle-metrics.md`, flagging operators when compliance falls below
   the configured threshold. Quality summaries continue to append to
   `reports/quality-summary.md`.

## Consequences

- Operators now have a single place (`docs/decisions/`) to trace how throttling and
  persistence interact.
- Adding the controller allows tests to simulate concurrency and ban resilience
  deterministically, ensuring regressions surface quickly.
- The CLI can surface compliance warnings and historical metrics, giving early
  indicators of configuration drift or provider changes.

