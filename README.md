# Video Playlist Downloader

Command-line tool for archiving Bilibili playlists with resumable progress tracking, throttle controls, and rich reporting.

## Features
- End-to-end playlist downloads powered by `yt-dlp`, including manifest normalization and subtitle selection.
- Adjustable throttle profile (concurrency, rate limits, sleep intervals, ban backoff) with compliance metrics and warnings.
- Automatic disk-capacity guard that checks free space before downloads begin.
- SQLite persistence for session history, manifests, and resume checkpoints so interrupted runs can continue later.
- Reporting helpers that append quality summaries, throttle metrics, and subtitle coverage in `reports/`.
- JSON output mode for automation alongside human-friendly Rich console summaries.

## Getting Started

### Prerequisites
- Python 3.10+
- `yt-dlp`, `Typer`, `SQLAlchemy`, `Tenacity`, and `Rich` (installed automatically via `pip install -e .`)
- Optional: access to the shared conda environment `/ssd4/envs/llm_py310_torch271_cu128`

### Installation
```bash
git clone https://example.com/video-playlist-downloader.git
cd video-playlist-downloader
pip install -e .
```

### Configuration
- Configuration is pulled from environment variables and optional dotenv files (pass `--config /path/to/.env` to the CLI).
- Unless overridden, downloads and the SQLite database live under `./video-storage`.

| Variable | Default | Description |
|----------|---------|-------------|
| `VPD_STORAGE_ROOT` | `video-storage` | Root directory for downloads and the SQLite database. |
| `VPD_DATABASE_FILENAME` | `state.db` | Filename placed inside `VPD_STORAGE_ROOT` that stores session state. |
| `VPD_REPORTS_DIR` | `reports` | Location for generated quality, throttle, and subtitle reports. |
| `VPD_MAX_CONCURRENCY` | `2` | Maximum concurrent downloads. |
| `VPD_LIMIT_RATE` | unset | Optional network rate limit (e.g. `2M`, `500K`). |
| `VPD_SLEEP_INTERVAL` | `1.0` | Delay (seconds) enforced between download completions. |
| `VPD_MAX_RETRIES` | `3` | Retry attempts per video. |
| `VPD_RETRY_BACKOFF` | `1.5` | Multiplier applied between retries. |
| `VPD_BAN_BACKOFF_INITIAL` | `1.0` | Initial backoff window when a ban is detected. |
| `VPD_BAN_BACKOFF_FACTOR` | `2.0` | Growth factor for consecutive ban backoff windows. |
| `VPD_BAN_BACKOFF_MAX` | `60.0` | Maximum seconds to sleep after ban events. |
| `VPD_COMPLIANCE_THRESHOLD` | `0.95` | Minimum acceptable throttle compliance ratio before warnings are emitted. |
| `VPD_SUBTITLE_LANGUAGES` | unset | Comma-separated language codes (e.g. `en,zh`) prioritized when selecting subtitles. |
| `VPD_MIN_FREE_GB` | `1.0` | Minimum free disk space required (checked before downloads). |

Create the storage directories once:
```bash
export VPD_STORAGE_ROOT=$PWD/video-storage
mkdir -p "$VPD_STORAGE_ROOT"
```

## CLI Usage
Invoke the Typer-based CLI via the installed entry point:

```bash
video-playlist-downloader --help
```

### Download a playlist
```bash
video-playlist-downloader download \
  "https://space.bilibili.com/<creator>/lists/<playlist>" \
  --max-concurrency 3 \
  --limit-rate 2M
```
- Validates free disk space, configures SQLite state, enumerates videos, and starts downloads.
- Appends session details to `reports/quality-summary.md` and `reports/throttle-metrics.md`.
- Use `--format json` for machine-readable output.

### Check playlist status
```bash
video-playlist-downloader status --playlist-url "https://…"
```
- Reads the persisted session history and renders totals plus throttle information.
- `--format json` returns the same data for APIs or dashboards.

### Resume an interrupted session
```bash
video-playlist-downloader resume <session-id>
```
- Loads the saved checkpoint, replays pending downloads, records a new session, and refreshes reports.

### Show version
```bash
video-playlist-downloader version
```

## Persistence & Reports
- **SQLite state** lives at `video-storage/state.db` (unless overridden) and tracks session activity, checkpoints, and cached manifests.
- **Downloads** are written under `video-storage/downloads/`.
- **Reports** created automatically:
  - `reports/quality-summary.md` – consolidated test/quality runs and per-session output summaries.
  - `reports/throttle-metrics.md` – throttle compliance, ban events, and backoff durations.
  - `reports/subtitle-metrics.json` – subtitle coverage data (requires SQLAlchemy to be available).
- Subtitles are filtered according to `VPD_SUBTITLE_LANGUAGES`, with fallback to all tracks if no preference is provided.

## Development Workflow
- Run quality gates (pytest + Ruff):
  ```bash
  make quality
  ```
- Targeted suites are available through Make targets:
  ```bash
  make test-download
  make test-resume
  make test-metadata
  make test-throttle
  ```
- You can also run `pytest` or `ruff check .` directly after activating your environment.

## License
Distributed under the MIT License. See `pyproject.toml` for project metadata.
