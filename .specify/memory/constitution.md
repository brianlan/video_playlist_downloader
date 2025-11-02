<!--
Sync Impact Report
Version change: 0.0.0 -> 1.0.0
Modified principles:
- Clarity Over Cleverness
- TDD-First Delivery
- Automate Quality Gates
- Simplicity With Intent
- Explain the Why
Added sections:
- Engineering Workflow Standards
- Review & Maintenance Expectations
Removed sections:
- None
Templates requiring updates:
- ✅ .specify/templates/plan-template.md (Constitution Check gating aligned with principles)
- ✅ .specify/templates/spec-template.md (Specification guidance reinforces TDD and readability)
- ✅ .specify/templates/tasks-template.md (Task sequencing enforces tests-first and automation)
Follow-up TODOs:
- None
-->

# Video Playlist Downloader Constitution

## Core Principles

### Clarity Over Cleverness
- Code MUST prefer explicit control flow and data transformations over implicit "magic" or hidden side effects.
- Implementation choices MUST optimize for readability even when a more concise alternative exists.
- Reviews MUST demand descriptive naming and require inline rationale when deviating from established patterns.
Rationale: Explicit code keeps the downloader reliable and approachable for rapid contribution.

### TDD-First Delivery
- Every new behavior MUST begin with a failing automated test that documents the desired outcome.
- Tests MUST isolate external dependencies with mocks, stubs, or fixtures so CI never relies on live services.
- Contributors MUST follow the Red -> Green -> Refactor loop before merging to the main branch.
Rationale: TDD locks in expected playlist behavior and provides fast, repeatable feedback.

### Automate Quality Gates
- Linting, formatting, and test suites MUST run automatically for every branch and pull request.
- Repetitive validation steps MUST be captured as reusable scripts or documented commands before manual execution.
- Developers MUST provide a single documented command that executes the full local quality gate.
Rationale: Automated gates prevent regressions and keep delivery predictable.

### Simplicity With Intent
- Solutions MUST implement the simplest design that satisfies current requirements; defer speculative abstractions.
- Shared logic MUST live in a single, well-named module unless duplication is justified in the plan or review.
- Interfaces and modules MUST honor SOLID boundaries so behavior stays replaceable and testable.
Rationale: Disciplined simplicity keeps the codebase lean while preserving extensibility.

### Explain the Why
- Comments and docs MUST capture intent, trade-offs, or context not obvious from the code.
- Inline comments that merely restate behavior MUST be removed as part of refactors.
- Decision records MUST reference the issue, spec, or data that motivated the change.
Rationale: Capturing "why" builds shared understanding and accelerates reviews.

## Engineering Workflow Standards

- Feature work MUST start with an approved spec and implementation plan that articulate the failing tests to be written first.
- Specs and plans MUST document how automation scripts, linting, and tests will be invoked locally and in CI.
- Task breakdowns MUST order test creation before implementation and call out any required tooling changes.
- Plans MUST note readability trade-offs and how they will be explained in code comments or supporting docs.

## Review & Maintenance Expectations

- Reviews MUST confirm that new tests existed and failed before implementation and now pass in automation.
- Pull requests MUST include evidence of executed quality gates and highlight any new scripts or commands.
- Reviewers MUST reject changes that add complexity without documented rationale tying back to the plan or spec.
- Maintenance work MUST preserve or improve explanations of intent, updating comments and docs alongside code.

## Governance

- This constitution supersedes conflicting guidance; deviations require explicit approval documented in the pull request.
- Amendments require consensus from project maintainers, an accompanying changelog summary, and an updated version line.
- Versions follow Semantic Versioning: MAJOR for breaking governance shifts, MINOR for new principles or sections, PATCH for clarifications.
- Compliance reviews occur at least once per quarter and before major releases to verify adherence to principles and automation.

**Version**: 1.0.0 | **Ratified**: 2025-10-29 | **Last Amended**: 2025-10-29
