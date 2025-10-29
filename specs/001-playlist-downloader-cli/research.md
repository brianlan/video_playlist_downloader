# Research: Video Playlist CLI Downloader

## Playlist enumeration on Bilibili
- **Decision**: Use yt-dlp’s playlist extraction APIs with fallback HTML parsing for pagination anomalies.
- **Rationale**: yt-dlp already supports Bilibili playlist traversal and handles authentication tokens, reducing custom scraping work while remaining scriptable from Python.
- **Alternatives considered**: Custom Selenium/WebDriver crawl (slower, harder to maintain); direct Bilibili open API (limited access and rate caps).

## Download throttling strategy
- **Decision**: Combine yt-dlp rate flags (`--limit-rate`, `--sleep-interval`, `--concurrent-fragments`) with an application-level semaphore governing concurrent jobs.
- **Rationale**: Native flags enforce per-request pacing while an outer semaphore gives deterministic concurrency control for resume/retry logic.
- **Alternatives considered**: OS-level traffic shaping (tc) (complex to ship cross-platform); naive sleep between downloads (insufficient for fragment bursts).

## Resume and checkpointing
- **Decision**: Persist session state (playlist cursor, completed video hashes, throttle configuration) in SQLite and rely on yt-dlp’s partial file resume for individual downloads.
- **Rationale**: Database checkpoints let the CLI skip already-downloaded files confidently and quickly rebuild queues after interruption.
- **Alternatives considered**: Flat JSON state files (fragile under concurrent runs); re-querying filesystem each time (slower and error-prone when filenames change).

## Metadata and subtitle persistence
- **Decision**: Store normalized video metadata plus optional subtitle language records in dedicated tables linked by video ID.
- **Rationale**: Structured tables enable fast lookup for cataloging, deduplication, and auditing subtitle coverage.
- **Alternatives considered**: Embedding metadata in filename sidecars (difficult to query); keeping subtitles only on disk (no visibility into missing assets).

## Quality gate automation
- **Decision**: Provide a `make quality` command that activates the conda env, runs pytest with coverage, and executes ruff lint.
- **Rationale**: A single entry point satisfies the constitution mandate for automated gates and simplifies contributor onboarding.
- **Alternatives considered**: Separate shell scripts for each tool (more commands to remember); ad-hoc manual testing (risks regressions).
