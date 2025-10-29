<!--
Sync Impact Report
Version: 0.0.0 → 1.0.0
Modified Principles:
- Template Principle 1 → Clarity Over Cleverness
- Template Principle 2 → TDD Leads Delivery
- Template Principle 3 → Automation Everywhere
- Template Principle 4 → Lean Design Discipline
- Template Principle 5 → Explain the Why
Added Sections:
- Development Workflow Standards
- Collaboration Practices
Removed Sections:
- None
Templates:
- ✅ .specify/templates/plan-template.md
- ✅ .specify/templates/spec-template.md
- ✅ .specify/templates/tasks-template.md
- ⚠ .specify/templates/commands (directory currently absent; review once command templates exist)
Follow-up TODOs:
- None
-->

# Video Playlist Downloader Constitution

## Core Principles

### Clarity Over Cleverness
Code MUST optimize for readability and explicit intent, even when that requires additional lines over terse constructs.
- Interfaces and modules MUST expose descriptive names and predictable behavior with no hidden "magic" or implicit coupling.
- Control flow and data transformations MUST remain explicit; avoid meta-programming or side effects that obscure intent.
- Document assumptions and invariants through tests or lightweight notes so future contributors immediately grasp expectations.
Rationale: Clarity keeps the team fast, confident, and happy by removing ambiguity and surprise.

### TDD Leads Delivery
Every change MUST begin with a failing automated test before production code is written.
- Follow a strict Red → Green → Refactor loop for all features and fixes; do not shortcut the cycle.
- Prefer mocks and stubs for external integrations so test suites remain fast, deterministic, and offline-friendly.
- Tests MUST document desired behavior and edge cases, serving as executable specifications for reviewers.
Rationale: Test-first development guarantees coverage, supports safe refactoring, and communicates requirements unambiguously.

### Automation Everywhere
Automation MUST cover linting, formatting, testing, and repeatable workflows that guard quality.
- Provide scripts or documented commands so contributors can run the full automated suite locally with a single step.
- Continuous Integration MUST enforce the same automation gates on every change before merge.
- Healthy automation SHOULD alert the team on regressions and keep manual toil to an absolute minimum.
Rationale: Automated guardrails protect quality at scale and free contributors to focus on solving user problems.

### Lean Design Discipline
Design decisions MUST follow KISS, DRY, SOLID, and YAGNI principles to keep the system simple and adaptable.
- Start with the simplest viable solution; only introduce abstractions when duplication or rigidity proves they are necessary.
- Keep responsibilities focused and interfaces stable, enabling future evolution without breaking users.
- Eliminate accidental complexity quickly through refactoring guided by tests.
Rationale: Lean design avoids over-engineering, enabling sustainable velocity and maintainability.

### Explain the Why
Comments and documentation MUST capture intent, trade-offs, and rationale instead of narrating obvious code.
- Reference design decisions, user requirements, or constraints that influenced the chosen approach.
- Remove outdated commentary swiftly to prevent knowledge rot and confusion.
- Prefer short, purposeful comments situated where critical context lives (functions, modules, or ADRs).
Rationale: Understanding why a choice exists empowers maintainers to evolve it confidently.

## Development Workflow Standards

- Each feature or fix MUST start by enumerating the behaviors as automated tests that initially fail.
- External services MUST be replaced with mocks, stubs, or fakes in test and local workflows to keep the loop rapid.
- Automated linting, formatting, and testing MUST run locally before opening a pull request and again in CI.
- Shared scripts in `package.json`, Makefiles, or shell tooling SHOULD encapsulate these commands for repeatability.

These standards ensure our TDD discipline, automation coverage, and clarity-first principles remain enforceable in daily work.

## Collaboration Practices

- Pull requests MUST highlight the motivating user problem and reference the tests that prove success.
- Reviewers MUST block changes that sacrifice readability, break automation gates, or skip test-first delivery.
- Inline comments MUST explain why a change is necessary when the code alone is insufficient.
- The team SHOULD schedule regular knowledge-sharing touchpoints to surface lessons learned from TDD cycles and automation tuning.

## Governance

- This constitution is authoritative over all engineering practices; every plan, spec, and task list MUST comply.
- Amendments require a written proposal, agreement from maintainers, and updates to affected templates or automation.
- Version numbers follow Semantic Versioning: MAJOR for breaking governance changes, MINOR for new principles or sections, PATCH for clarifications.
- Compliance reviews occur at plan creation, during code review, and in post-release retrospectives to confirm adherence.

**Version**: 1.0.0 | **Ratified**: 2025-10-29 | **Last Amended**: 2025-10-29
