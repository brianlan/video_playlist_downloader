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

- [ ] T001 Create project manifest with CLI entry point and dependencies in `pyproject.toml`
- [ ] T002 Scaffold package directories and placeholder modules in `src/video_playlist_downloader/`
- [ ] T003 Add `Makefile` with `quality` target invoking conda activation and script in `Makefile`
- [ ] T004 Create automation wrapper `scripts/run_quality.sh` to run `pytest` and `ruff check`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure required before user stories start

**⚠️ CRITICAL**: All tasks in this phase must complete before any user story work.

- [ ] T005 Implement configuration loader and defaults in `src/video_playlist_downloader/config.py`
- [ ] T006 Initialize SQLite engine, session factory, and Base metadata in `src/video_playlist_downloader/persistence.py`
- [ ] T007 Bootstrap Typer application shell with shared Rich console helpers in `src/video_playlist_downloader/cli.py`
- [ ] T008 Create shared test fixtures (temp storage, fake yt-dlp client) in `tests/conftest.py`
- [ ] T009 Provision runtime storage root and state database directory in `scripts/setup_storage.py`

**Checkpoint**: Foundation ready – CLI skeleton, configuration, persistence, and shared fixtures in place.

---

## Phase 3: User Story 1 - Download entire playlist from CLI (Priority: P1) 🎯 MVP

**Goal**: Trigger playlist download from a single CLI command, capturing all permitted videos.

**Independent Test**: `make test-download` executes `pytest tests/cli/test_playlist_download.py tests/integration/test_cli_download.py` using recorded fixtures and mocked yt-dlp calls.

### Tests for User Story 1 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T010 [P] [US1] Author CLI workflow test covering download and skip logging in `tests/cli/test_playlist_download.py`
- [ ] T011 [P] [US1] Author integration test for playlist run with fixture storage in `tests/integration/test_cli_download.py`

### Implementation for User Story 1

- [ ] T012 [P] [US1] Implement playlist enumeration and download orchestration in `src/video_playlist_downloader/downloader.py`
- [ ] T013 [US1] Wire `download` command with configuration and downloader in `src/video_playlist_downloader/cli.py`
- [ ] T014 [US1] Persist session activity and skip reasons to database log in `src/video_playlist_downloader/persistence.py`
- [ ] T015 [US1] Align CLI contract with OpenAPI expectations in `tests/contract/test_contract_alignment.py`
- [ ] T016 [US1] Emit Rich progress and summary output for downloads in `src/video_playlist_downloader/cli.py`

**Checkpoint**: Playlist downloads execute end-to-end with skipped videos logged, progress visible, and contract validated.

---

## Phase 4: User Story 2 - Resume long-running downloads (Priority: P2)

**Goal**: Allow operators to resume or recover interrupted playlist downloads without repeating completed work.

**Independent Test**: `make test-resume` runs `pytest tests/persistence/test_resume_progress.py tests/cli/test_resume_command.py` ensuring checkpointing and resume CLI work.

### Tests for User Story 2 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T017 [P] [US2] Author persistence checkpoint test for resume flow in `tests/persistence/test_resume_progress.py`
- [ ] T018 [P] [US2] Author CLI resume command test validating restart behavior in `tests/cli/test_resume_command.py`

### Implementation for User Story 2

- [ ] T019 [US2] Extend session persistence with checkpoint snapshots and hashes in `src/video_playlist_downloader/persistence.py`
- [ ] T020 [US2] Update downloader to rebuild queues from checkpoints in `src/video_playlist_downloader/downloader.py`
- [ ] T021 [US2] Implement `resume` CLI command wiring session lookup in `src/video_playlist_downloader/cli.py`
- [ ] T022 [US2] Add session status reporting command in `src/video_playlist_downloader/cli.py`

**Checkpoint**: Interrupted downloads resume seamlessly with accurate status reporting.

---

## Phase 5: User Story 3 - Persist metadata and subtitles (Priority: P3)

**Goal**: Record video metadata and optional subtitles in the database for cataloging.

**Independent Test**: `make test-metadata` runs `pytest tests/db/test_video_recording.py tests/unit/test_subtitles.py` verifying storage correctness.

### Tests for User Story 3 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T023 [P] [US3] Author metadata persistence test validating schema writes in `tests/db/test_video_recording.py`
- [ ] T024 [P] [US3] Author subtitle harvesting test with language fallbacks in `tests/unit/test_subtitles.py`

### Implementation for User Story 3

- [ ] T025 [US3] Define SQLAlchemy models for Playlist, VideoRecord, SubtitleAsset in `src/video_playlist_downloader/metadata.py`
- [ ] T026 [US3] Implement metadata write helpers and subtitle associations in `src/video_playlist_downloader/persistence.py`
- [ ] T027 [US3] Implement subtitle extraction helper integrating yt-dlp metadata in `src/video_playlist_downloader/subtitles.py`
- [ ] T028 [US3] Update downloader pipeline to persist metadata and optional subtitles in `src/video_playlist_downloader/downloader.py`
- [ ] T029 [US3] Surface metadata summaries in CLI status output in `src/video_playlist_downloader/cli.py`

**Checkpoint**: Metadata and subtitles stored for all downloads with CLI visibility.

---

## Phase 6: User Story 4 - Configure throttling safeguards (Priority: P3)

**Goal**: Enforce configurable download throttles to avoid IP bans and highlight throttle state.

**Independent Test**: `make test-throttle` runs `pytest tests/rate_limit/test_throttle_controls.py tests/unit/test_throttle_cli.py` validating rate limits.

### Tests for User Story 4 (author first) ⚠️

> **MANDATE: Write these tests FIRST, ensure they FAIL before implementation, and document the command that executes them.**

- [ ] T030 [P] [US4] Author throttle policy test covering semaphore and delay logic in `tests/rate_limit/test_throttle_controls.py`
- [ ] T031 [P] [US4] Author CLI configuration test for throttle flags in `tests/unit/test_throttle_cli.py`

### Implementation for User Story 4

- [ ] T032 [US4] Implement throttle policy manager with concurrency semaphore in `src/video_playlist_downloader/throttle.py`
- [ ] T033 [US4] Integrate throttle controls into downloader execution loop in `src/video_playlist_downloader/downloader.py`
- [ ] T034 [US4] Extend configuration schema with throttle settings and validation in `src/video_playlist_downloader/config.py`
- [ ] T035 [US4] Display throttle metrics in session reporting in `src/video_playlist_downloader/cli.py`

**Checkpoint**: Download rate adheres to configured ceilings with clear operator feedback.

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Repository hygiene, documentation, and release readiness

- [ ] T036 [P] Capture throttling and persistence decisions in `docs/decisions/2025-10-29-download-architecture.md`
- [ ] T037 Refresh quickstart with resume and throttle examples in `specs/001-playlist-downloader-cli/quickstart.md`
- [ ] T038 [P] Export quality gate results to `reports/quality-summary.md` after `make quality`
- [ ] T039 Harden logging configuration and redact sensitive data in `src/video_playlist_downloader/cli.py`
- [ ] T040 [P] Final review and update of OpenAPI alignment notes in `contracts/openapi.yaml`

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

- Setup tasks T002–T004 can run in parallel after T001.
- Foundational tasks T005–T008 can execute concurrently; T009 follows storage decisions from T005.
- For US1, T010 and T011 run in parallel; after tests, T012 and T015 can proceed concurrently while T013 waits on T012.
- For US2–US4, marked `[P]` tasks (tests and helper modules) can execute concurrently once prerequisite modules exist.

---

## Parallel Example: User Story 2

```bash
# Parallel test authoring once foundational fixtures exist:
pytest tests/persistence/test_resume_progress.py  # T017
pytest tests/cli/test_resume_command.py          # T018

# After tests fail, implement supporting modules concurrently:
code src/video_playlist_downloader/persistence.py  # T019
code src/video_playlist_downloader/downloader.py   # T020
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
