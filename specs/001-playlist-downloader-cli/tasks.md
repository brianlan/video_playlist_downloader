---

description: "Task list for Video Playlist CLI Downloader implementation"
---

# Tasks: Video Playlist CLI Downloader

**Input**: Design documents from `/specs/001-playlist-downloader-cli/`  
**Prerequisites**: plan.md (required), spec.md (user stories), research.md, data-model.md, contracts/

**Tests**: Author the failing automated tests for each user story before implementation and document how to run them locally and in CI.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, tooling, and shared environment

- [X] T001 Create project manifest with CLI entry point and dependencies in `pyproject.toml`
- [X] T002 Scaffold package directories and placeholder modules in `src/video_playlist_downloader/`
- [X] T003 Add `Makefile` with `quality` target invoking conda activation and script in `Makefile`
- [X] T004 Create automation wrapper `scripts/run_quality.sh` to run `pytest` and `ruff check`
- [X] T005 Add `make test-download` target invoking `pytest tests/cli/test_playlist_download.py tests/integration/test_cli_download.py tests/cli/test_console_summary.py` in `Makefile`
- [X] T006 Add `make test-resume` target invoking `pytest tests/persistence/test_resume_progress.py tests/cli/test_resume_command.py` in `Makefile`
- [X] T007 Add `make test-metadata` target invoking `pytest tests/db/test_video_recording.py tests/unit/test_subtitles.py tests/perf/test_metadata_latency.py tests/reporting/test_subtitle_coverage.py` in `Makefile`
- [X] T008 Add `make test-throttle` target invoking `pytest tests/rate_limit/test_throttle_controls.py tests/unit/test_throttle_cli.py tests/rate_limit/test_throttle_metrics.py` in `Makefile`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before user stories start

**⚠️ CRITICAL**: All tasks in this phase must complete before any user story work.

- [X] T009 Implement configuration loader and defaults in `src/video_playlist_downloader/config.py`
- [X] T010 Initialize SQLite engine, session factory, and Base metadata in `src/video_playlist_downloader/persistence.py`
- [X] T011 Bootstrap Typer application shell with shared Rich console helpers in `src/video_playlist_downloader/cli.py`
- [X] T012 Create shared test fixtures (temp storage, fake yt-dlp client) in `tests/conftest.py`
- [X] T013 Provision runtime storage root and state database directory in `scripts/setup_storage.py`
- [X] T061 Implement storage capacity guard utility in `src/video_playlist_downloader/storage_guard.py`
- [X] T062 Wrap persistence session factories with Tenacity retry scaffolding in `src/video_playlist_downloader/persistence.py`

**Checkpoint**: Foundation ready – CLI skeleton, configuration, persistence, and shared fixtures in place.

---

## Phase 3: User Story 1 - Download entire playlist from CLI (Priority: P1) 🎯 MVP

**Goal**: Trigger playlist download from a single CLI command, capturing all permitted videos.

**Independent Test**: `make test-download` executes `pytest tests/cli/test_playlist_download.py tests/integration/test_cli_download.py tests/cli/test_console_summary.py` using recorded fixtures and mocked yt-dlp calls.

### Tests for User Story 1 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T014 [P] [US1] Author CLI workflow test covering download and skip logging in `tests/cli/test_playlist_download.py`
- [ ] T015 [P] [US1] Author integration test for playlist run with fixture storage in `tests/integration/test_cli_download.py`
- [ ] T016 [P] [US1] Author console summary snapshot test to verify Rich output includes totals, pending count, throttle state, elapsed time, and ETA table in `tests/cli/test_console_summary.py`
- [ ] T057 [P] [US1] Author status latency benchmark for 500-item playlists in `tests/perf/test_status_latency.py`
- [ ] T058 [P] [US1] Author low disk capacity failure test in `tests/integration/test_low_disk_abort.py`

### Implementation for User Story 1

- [ ] T017 [P] [US1] Implement playlist enumeration and download orchestration in `src/video_playlist_downloader/downloader.py`
- [ ] T018 [US1] Wire `download` command with configuration and downloader in `src/video_playlist_downloader/cli.py`
- [ ] T019 [US1] Persist session activity and skip reasons to database log in `src/video_playlist_downloader/persistence.py`
- [ ] T020 [US1] Align CLI contract with OpenAPI expectations in `tests/contract/test_contract_alignment.py`
- [ ] T021 [US1] Emit Rich progress and summary table covering totals, pending items, elapsed time, throttle status, and ETA in `src/video_playlist_downloader/cli.py`
- [ ] T059 [US1] Instrument session summary timing and publish latency metrics in `src/video_playlist_downloader/cli.py` and `reports/quality-summary.md`
- [ ] T060 [US1] Integrate storage capacity guard into download flow with Rich warnings in `src/video_playlist_downloader/cli.py`

**Checkpoint**: Playlist downloads execute end-to-end with skipped videos logged, progress visible, and contract validated.

---

## Phase 4: User Story 2 - Resume long-running downloads (Priority: P2)

**Goal**: Allow operators to resume or recover interrupted playlist downloads without repeating completed work.

**Independent Test**: `make test-resume` runs `pytest tests/persistence/test_resume_progress.py tests/cli/test_resume_command.py` ensuring checkpointing and resume CLI work.

### Tests for User Story 2 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T022 [P] [US2] Author persistence checkpoint test for resume flow in `tests/persistence/test_resume_progress.py`
- [ ] T023 [P] [US2] Author CLI resume command test validating restart behavior in `tests/cli/test_resume_command.py`
- [ ] T051 [P] [US2] Author offline continuity test verifying cached manifest supports downloads without network in `tests/integration/test_offline_resume.py`
- [ ] T063 [P] [US2] Author transient database retry test in `tests/persistence/test_db_retry.py`

### Implementation for User Story 2

- [ ] T024 [US2] Extend session persistence with checkpoint snapshots and hashes in `src/video_playlist_downloader/persistence.py`
- [ ] T025 [US2] Update downloader to rebuild queues from checkpoints in `src/video_playlist_downloader/downloader.py`
- [ ] T026 [US2] Implement `resume` CLI command wiring session lookup in `src/video_playlist_downloader/cli.py`
- [ ] T027 [US2] Add session status reporting command in `src/video_playlist_downloader/cli.py`
- [ ] T052 [US2] Persist and load cached playlist manifests for offline operation in `src/video_playlist_downloader/persistence.py`
- [ ] T053 [US2] Consume manifest cache and continue downloads when network calls fail in `src/video_playlist_downloader/downloader.py`
- [ ] T064 [US2] Apply Tenacity retry wrappers to persistence writes and expose retry metrics in `src/video_playlist_downloader/persistence.py`

**Checkpoint**: Interrupted downloads resume seamlessly with accurate status reporting.

---

## Phase 5: User Story 3 - Persist metadata and subtitles (Priority: P3)

**Goal**: Record video metadata and optional subtitles in the database for cataloging.

**Independent Test**: `make test-metadata` runs `pytest tests/db/test_video_recording.py tests/unit/test_subtitles.py tests/perf/test_metadata_latency.py tests/reporting/test_subtitle_coverage.py` verifying storage correctness, coverage, and latency.

### Tests for User Story 3 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T028 [P] [US3] Author metadata persistence test validating schema writes in `tests/db/test_video_recording.py`
- [ ] T029 [P] [US3] Author subtitle harvesting test with language fallbacks in `tests/unit/test_subtitles.py`
- [ ] T030 [P] [US3] Author metadata latency performance test asserting ≤5s inserts in `tests/perf/test_metadata_latency.py`
- [ ] T031 [P] [US3] Author subtitle coverage analytics test enforcing 90% threshold in `tests/reporting/test_subtitle_coverage.py`

### Implementation for User Story 3

- [ ] T032 [US3] Define SQLAlchemy models for Playlist, VideoRecord, SubtitleAsset in `src/video_playlist_downloader/metadata.py`
- [ ] T033 [US3] Implement metadata write helpers and subtitle associations in `src/video_playlist_downloader/persistence.py`
- [ ] T034 [US3] Implement subtitle extraction helper integrating yt-dlp metadata in `src/video_playlist_downloader/subtitles.py`
- [ ] T035 [US3] Update downloader pipeline to persist metadata and optional subtitles in `src/video_playlist_downloader/downloader.py`
- [ ] T036 [US3] Surface metadata summaries alongside the Rich totals/throttle table in `src/video_playlist_downloader/cli.py`
- [ ] T037 [US3] Generate subtitle coverage report and store metrics in `reports/subtitle-metrics.json`

**Checkpoint**: Metadata and subtitles stored for all downloads with CLI visibility, coverage metrics, and latency guarantees met.

---

## Phase 6: User Story 4 - Configure throttling safeguards (Priority: P3)

**Goal**: Enforce configurable download throttles to avoid IP bans and highlight throttle state.

**Independent Test**: `make test-throttle` runs `pytest tests/rate_limit/test_throttle_controls.py tests/unit/test_throttle_cli.py tests/rate_limit/test_throttle_metrics.py` validating rate limits and success ratios.

### Tests for User Story 4 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T038 [P] [US4] Author throttle policy test covering semaphore and delay logic in `tests/rate_limit/test_throttle_controls.py`
- [ ] T039 [P] [US4] Author CLI configuration test for throttle flags in `tests/unit/test_throttle_cli.py`
- [ ] T040 [P] [US4] Author throttle metrics analysis test ensuring ≥95% compliant runs in `tests/rate_limit/test_throttle_metrics.py`
- [ ] T054 [P] [US4] Author ban-avoidance simulation test injecting provider 429/ban responses in `tests/rate_limit/test_ban_resilience.py`

### Implementation for User Story 4

- [ ] T041 [US4] Implement throttle policy manager with concurrency semaphore in `src/video_playlist_downloader/throttle.py`
- [ ] T042 [US4] Integrate throttle controls into downloader execution loop in `src/video_playlist_downloader/downloader.py`
- [ ] T043 [US4] Extend configuration schema with throttle settings and validation in `src/video_playlist_downloader/config.py`
- [ ] T044 [US4] Log throttle outcomes, ban-resilience metrics, and display them in the Rich session reporting table in `src/video_playlist_downloader/cli.py`
- [ ] T045 [US4] Persist throttle compliance summary to `reports/throttle-metrics.md` and raise alerts on failures
- [ ] T055 [US4] React to simulated ban signals with exponential backoff and recovery in `src/video_playlist_downloader/throttle.py`
- [ ] T056 [US4] Capture ban-resilience metrics in reporting artifacts (`reports/throttle-metrics.md`) and CLI summaries

**Checkpoint**: Download rate adheres to configured ceilings with clear operator feedback and compliance tracking.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Repository hygiene, documentation, and release readiness

- [ ] T046 [P] Capture throttling and persistence decisions in `docs/decisions/2025-10-29-download-architecture.md`
- [ ] T047 Refresh quickstart with resume and throttle examples in `specs/001-playlist-downloader-cli/quickstart.md`
- [ ] T048 [P] Export quality gate results to `reports/quality-summary.md` after `make quality`
- [ ] T049 Harden logging configuration and redact sensitive data in `src/video_playlist_downloader/cli.py`
- [ ] T050 [P] Final review and update of OpenAPI alignment notes in `contracts/openapi.yaml`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No prerequisites – complete first.
- **Foundational (Phase 2)**: Depends on Setup completion – blocks all user stories.
- **User Stories (Phases 3-6)**: Begin after Foundational; prioritize US1 (MVP) before US2–US4.
- **Polish (Phase N)**: Execute after desired user stories reach completion.

### User Story Dependencies

- **US1**: Independent once foundational tasks complete.
- **US2**: Depends on US1 data structures (`downloader`, persistence) but resumes independently afterward.
- **US3**: Depends on US1 download flow and foundational persistence scaffolding.
- **US4**: Depends on US1 downloader loop; can run in parallel with US3 once downloader hooks exist.

### Within Each User Story

- Tests MUST be written first and observed failing before implementation.
- Implement models/helpers before CLI wiring.
- CLI updates precede contract alignment and reporting tweaks.
- Validate each story independently before advancing.

### Parallel Opportunities

- Setup tasks T002–T008 can run in parallel after T001.
- Foundational tasks T009–T012 can execute concurrently; T013 follows configuration decisions from T009.
- For US1, T014–T016 run in parallel; after tests, T017 and T020 can proceed concurrently while T018 waits on T017.
- For US2–US4, marked `[P]` tasks (tests and helper modules) can execute concurrently once prerequisite modules exist.

---

## Parallel Example: User Story 2

```bash
# Parallel test authoring once foundational fixtures exist:
pytest tests/persistence/test_resume_progress.py  # T022
pytest tests/cli/test_resume_command.py          # T023

# After tests fail, implement supporting modules concurrently:
code src/video_playlist_downloader/persistence.py  # T024
code src/video_playlist_downloader/downloader.py   # T025
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Deliver Phase 3 (US1) with passing tests.
4. **STOP and VALIDATE**: Run `make test-download` and `make quality`.
5. Ship MVP CLI for playlist downloads.

### Incremental Delivery

1. Add Phase 4 (US2) to support resumable sessions.
2. Layer Phase 5 (US3) for metadata and subtitles.
3. Deliver Phase 6 (US4) for throttle safeguards.
4. Polish across docs, contracts, and logging.

### Parallel Team Strategy

1. Team pairs complete Setup + Foundational.
2. Assign US1 to Developer A, US2 to Developer B (after US1 downloader hooks), US3 to Developer C, and US4 to Developer D.
3. Use shared fixtures and documented commands to avoid blocking.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story MUST be independently completable and testable.
- Verify new tests fail before implementation and pass after the change.
- Capture intent or trade-offs in inline comments or ADRs when tasks introduce non-obvious decisions.
- Commit after each task or logical group.
- Stop at checkpoints to validate each story independently.
- Avoid: vague tasks, file conflicts, cross-story dependencies that break independence.
