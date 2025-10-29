# Feature Specification: Video Playlist CLI Downloader

**Feature Branch**: `001-playlist-downloader-cli`  
**Created**: 2025-10-29  
**Status**: Draft  
**Input**: User description: "Create a cli tool that takes as input a playlist web link, and download the videos using yt-dlp. We may need to develop a way to iterate through each page of the playlist to get the individual video url, so this may require a investigation on the web page analysis beforehand. Manage and control the download speed to prevent the video site banning our IP. For some video due to limited permission (e.g. 充电计划), we can skip downloading it. All the downloaded video should be saved into a video-storage directory. We also need to have a database to store each video's information, like the video publish time and title, etc. The downloading process may take quite a long time, so we also need to develop a mechanism to track the progress so we can resume in the middle. If we can get the subtitle along with the video downloading we also download and store this information to the DB. But if no subtitle for a video, we just skip this part and download the video only. We can take this playlist (https://space.bilibili.com/28554995/upload/video) as an example to develop our tool. IMPORTANT: Use conda environment during the development (conda activate /ssd4/envs/llm_py310_torch271_cu128) Use codex as AI agent which relies on AGENTS.md instead of CLAUDE.md."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

_Constitution alignment: Each story MUST name the automated tests that will be authored first, how they run in CI, and which collaborators will be mocked or stubbed._

### User Story 1 - Download entire playlist from CLI (Priority: P1)

As a content archivist I want to trigger a playlist download from a single CLI command so that all public videos are captured into our storage directory with minimal manual work.

**Why this priority**: Establishes the core value of the tool—extracting playlist items and downloading permitted videos on demand.

**Independent Test**: Automated CLI workflow test authored first (`tests/cli/test_playlist_download.py`) using recorded playlist fixtures and stubbed network responses, executed locally via `make test-download` and in CI, verifies that a supplied playlist link schedules and downloads all eligible videos.

**Acceptance Scenarios**:

1. **Given** a reachable playlist URL and configured storage path, **When** the operator runs the CLI command, **Then** all accessible videos download into `video-storage/` using the enforced throttle settings.
2. **Given** a playlist containing region-locked or permission-restricted entries, **When** the CLI evaluates the list, **Then** skipped entries are logged with reasons without blocking the remaining downloads.

---

### User Story 2 - Resume long-running downloads (Priority: P2)

As an operations engineer I want to pause or recover a download session so that long playlists or flaky connections do not force me to start over.

**Why this priority**: Protects time and bandwidth investments by maintaining progress across interruptions.

**Independent Test**: Automated persistence test (`tests/persistence/test_resume_progress.py`) run first with database and filesystem stubs, executed via `make test-resume` locally and in CI, confirms that partial progress is recorded and reloaded before resuming.

**Acceptance Scenarios**:

1. **Given** an in-flight download that is interrupted, **When** the operator restarts the CLI with the same playlist link, **Then** the tool resumes from the last successfully downloaded video without re-fetching completed files.
2. **Given** a paused session recorded in the database, **When** the CLI queries session metadata, **Then** it reports the remaining videos and estimated remaining time before continuing.

---

### User Story 3 - Persist metadata and subtitles (Priority: P3)

As a catalog manager I want each downloaded video’s metadata (publish time, title, subtitles where available) captured in our database so that archives remain searchable and complete.

**Why this priority**: Enables downstream cataloging, duplicate detection, and compliance reporting.

**Independent Test**: Automated metadata ingestion test (`tests/db/test_video_recording.py`) authored before implementation, using database fixtures and subtitle mocks, executed through `make test-metadata` locally and in CI, asserts that metadata and optional subtitles are persisted per video.

**Acceptance Scenarios**:

1. **Given** a downloaded video with subtitles available, **When** the CLI completes the download, **Then** the video’s metadata and subtitle asset are saved in the database and linked to the file in storage.
2. **Given** a video without subtitles, **When** the download finishes, **Then** the record is stored without subtitle data and the absence is noted for auditing.

---

### User Story 4 - Configure throttling safeguards (Priority: P3)

As a site reliability engineer I want to cap download concurrency and speed so that the hosting platform does not flag or ban our IP address.

**Why this priority**: Compliance with platform limits avoids service disruption.

**Independent Test**: Automated throttle policy test (`tests/rate_limit/test_throttle_controls.py`) written first with mocked timing controls, executed via `make test-throttle` locally and in CI, verifies that configured limits are honored across the download lifecycle.

**Acceptance Scenarios**:

1. **Given** global throttle settings, **When** multiple videos are queued, **Then** the tool enforces the maximum concurrent downloads and inter-request delay defined in configuration.
2. **Given** throttle metrics exceed safe thresholds, **When** the CLI processes the queue, **Then** it slows or pauses downloads and surfaces guidance in the session report.

### Edge Cases

- Playlist contains a mix of accessible, geo-restricted, and paywalled videos.
- Playlist pagination structure changes mid-run or returns duplicate entries.
- Disk space runs low in `video-storage/` during download.
- Network outages or proxy resets occur while writing files.
- Subtitles exist in multiple languages or contain unsupported characters.
- Database connection is temporarily unavailable when persisting progress.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST accept a playlist URL as input and discover every constituent video, including across paginated listings.
- **FR-002**: The system MUST download each accessible video using yt-dlp (or compatible extractor) and write files to the configured `video-storage/` directory.
- **FR-003**: Restricted or unavailable videos MUST be skipped gracefully with reason codes recorded in the session log.
- **FR-004**: A configurable throttling policy MUST cap concurrent downloads and transfer rates to stay within provider tolerances.
- **FR-005**: The system MUST persist video metadata (title, description, publish time, duration, URL, file path) and session details in a project database.
- **FR-006**: Download progress MUST be checkpointed such that interrupted runs can resume without re-downloading completed items.
- **FR-007**: Available subtitles MUST be downloaded alongside the video and linked to the corresponding database record; absence MUST be noted without failing the job.
- **FR-008**: Operators MUST receive clear console output and session summaries covering totals downloaded, skipped, remaining time, and throttle status.
- **FR-009**: The solution MUST provide a single documented command that prepares the conda environment (`conda activate /ssd4/envs/llm_py310_torch271_cu128`) and runs the full automated test gate.
- **FR-010**: Configuration (storage path, throttle values, database connection, subtitle preference) MUST be adjustable via CLI flags and/or config file without code changes.

### Key Entities *(include if feature involves data)*

- **Playlist**: Represents the source collection (input URL, name, total items, crawl timestamp, pagination tokens).
- **VideoRecord**: Captures each video’s identifiers, publish metadata, download status, file location, subtitle availability, skip reason (if any).
- **DownloadSession**: Tracks individual CLI runs (playlist reference, start/end times, throttle settings, checkpoints, progress state).
- **SubtitleAsset**: Optional entity linked to VideoRecord storing language, format, and storage path when subtitles are retrieved.

## Assumptions

- Team members will develop and execute work inside the shared conda environment `/ssd4/envs/llm_py310_torch271_cu128`.
- The referenced playlist (https://space.bilibili.com/28554995/upload/video) is representative of production playlists for discovery and testing.
- Database technology and schema evolution tooling will be defined during planning but are expected to support transactional writes for progress checkpoints.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators complete a full download of a 100-video playlist without manual retries and with zero IP bans in 95% of runs.
- **SC-002**: Resume functionality restores interrupted sessions and avoids re-downloading completed videos in 99% of tested interruptions.
- **SC-003**: Metadata for 100% of downloaded videos is present in the database within 5 seconds of each file completion.
- **SC-004**: Optional subtitle assets are captured for at least 90% of videos where the source provides subtitles, with accurate linkage in the database.
