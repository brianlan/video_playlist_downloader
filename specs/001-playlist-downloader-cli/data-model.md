# Data Model: Video Playlist CLI Downloader

## Playlist
- **Fields**
  - `id` (UUID) – internal identifier for persisted playlists
  - `source_url` (string, unique) – canonical playlist URL
  - `title` (string) – playlist name snapshot at crawl time
  - `item_count` (integer) – total videos advertised by source
  - `last_crawled_at` (timestamp) – last successful enumeration
  - `cursor` (string, nullable) – token for pagination/resume
- **Relationships**
  - One-to-many with `DownloadSession`
  - One-to-many with `VideoRecord`
- **Validation Rules**
  - `source_url` must be HTTPS and host `bilibili.com`
  - `item_count` must be non-negative

## VideoRecord
- **Fields**
  - `id` (UUID)
  - `playlist_id` (UUID, FK Playlist)
  - `video_url` (string, unique within playlist)
  - `bvid` (string) – source video identifier when available
  - `title` (string)
  - `description` (text, nullable)
  - `publish_time` (timestamp, nullable)
  - `duration_seconds` (integer, nullable)
  - `local_path` (string, nullable until downloaded)
  - `download_status` (enum: pending, completed, skipped, failed)
  - `skip_reason` (string, nullable)
  - `last_attempted_at` (timestamp, nullable)
- **Relationships**
  - Many-to-one with `Playlist`
  - One-to-one with `SubtitleAsset` (optional)
  - Many-to-one with `DownloadSession` (current session reference)
- **Validation Rules**
  - `download_status` transitions: pending → completed|skipped|failed; failed can return to pending on retry
  - `local_path` required when status is completed

## DownloadSession
- **Fields**
  - `id` (UUID)
  - `playlist_id` (UUID, FK Playlist)
  - `started_at` (timestamp)
  - `completed_at` (timestamp, nullable)
  - `resumed_from_session_id` (UUID, nullable)
  - `throttle_profile` (json) – snapshot of concurrency and rate settings
  - `videos_total` (integer)
  - `videos_completed` (integer)
  - `videos_skipped` (integer)
  - `videos_failed` (integer)
- **Relationships**
  - Many-to-one with `Playlist`
  - One-to-many with `VideoRecord`
- **Validation Rules**
  - `videos_completed + videos_skipped + videos_failed` <= `videos_total`
  - `completed_at` present only when totals reconcile

## SubtitleAsset
- **Fields**
  - `id` (UUID)
  - `video_id` (UUID, FK VideoRecord, unique)
  - `language_code` (string, ISO 639-1)
  - `format` (string, e.g., srt, ass)
  - `local_path` (string)
  - `source_url` (string, nullable)
- **Relationships**
  - One-to-one with `VideoRecord`
- **Validation Rules**
  - `language_code` must conform to ISO 639-1
  - `local_path` must exist on disk when record is created
