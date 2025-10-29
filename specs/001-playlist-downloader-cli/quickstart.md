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

## 8. Export session report
```bash
video-playlist-downloader report --session-id <uuid> --format json > session-report.json
```
