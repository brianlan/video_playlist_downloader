# Quickstart: Video Playlist CLI Downloader

## Prerequisites
- Access to the shared conda environment `/ssd4/envs/llm_py310_torch271_cu128`
- Network connectivity to Bilibili for initial playlist discovery (downloads can continue offline once cached)
- Write permissions to `video-storage/` and `video-storage/state.db`

## 1. Activate environment
```bash
conda activate /ssd4/envs/llm_py310_torch271_cu128
```

## 2. Install project in editable mode
```bash
pip install -e .
```

## 3. Configure storage location
```bash
export VPD_STORAGE_ROOT=$PWD/video-storage
mkdir -p "$VPD_STORAGE_ROOT"
```

## 4. Run the CLI against a playlist
```bash
video-playlist-downloader download \
  --playlist-url https://space.bilibili.com/28554995/upload/video \
  --max-concurrency 2 \
  --limit-rate 2M
```

> **Throttle tuning**  
> Adjust environment variables before running the command to change throttle behaviour:  
> `VPD_MAX_CONCURRENCY`, `VPD_SLEEP_INTERVAL`, `VPD_LIMIT_RATE`,  
> `VPD_BAN_BACKOFF_INITIAL`, `VPD_BAN_BACKOFF_FACTOR`, `VPD_BAN_BACKOFF_MAX`, and  
> `VPD_COMPLIANCE_THRESHOLD`. The CLI raises a warning if the measured compliance
> falls below the configured threshold.

## 5. Monitor progress
```bash
video-playlist-downloader status --playlist-url https://space.bilibili.com/28554995/upload/video
```

## 6. Resume an interrupted session
```bash
video-playlist-downloader resume --session-id <uuid-from-status>
```

## 7. Run automated quality gate
```bash
make quality
```

## 8. Run targeted test suites
```bash
make test-download   # CLI workflow, integration, console summary
make test-resume     # Resume persistence + CLI commands
make test-metadata   # Metadata, subtitle coverage, latency
make test-throttle   # Throttle policy, CLI flags, compliance metrics
```

## 9. Export session report and metrics
```bash
video-playlist-downloader report --session-id <uuid> --format json > session-report.json
cat reports/throttle-metrics.md
cat reports/subtitle-metrics.json
cat reports/quality-summary.md
```

`reports/throttle-metrics.md` captures compliance percentage, ban events, and sleep
durations for every session so you can spot trends or tune throttling safeguards.
