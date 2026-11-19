# Project-Specific Agent Instructions (Template)

> Adapt this template into the target project's root `AGENTS.md`. It is not the same file as this starter repository's root `AGENTS.md`. Keep project-specific agent instructions concise and point to detailed docs that actually exist.

## Project overview

- **Project:** [Name and purpose]
- **Primary stack:** [Verified language/runtime/frameworks]
- **Key entry points:** [Paths]
- **Documentation home:** [Paths e.g., docs/engineering/ or root]

## Priority ladder

When engineering trade-offs arise during implementation, prioritize in this order:

1. **Correctness** — The solution must accurately satisfy requirements without regressions.
2. **Security** — Protect data, enforce authorization server-side, and never expose secrets.
3. **Usability & UX** — Keep flows intuitive, provide clear feedback, and preserve user input.
4. **Accessibility** — Semantic markup, keyboard navigation, and screen-reader friendliness.
5. **Consistency** — Follow existing repository conventions, patterns, and design tokens.
6. **Maintainability** — Clear modularity, readable code, and appropriate test coverage.
7. **Performance** — Bounded queries, efficient asset loading, and no premature micro-optimizations.
8. **Visual polish** — Cohesive visual alignment with existing design tokens and layouts.

## When to read each document

Before starting a task, consult the specialized document that governs the domain. These are conditional triggers, not a requirement to create every document: skip a row when its file does not exist or the task does not touch that domain. After selecting the project's docs directory, update the links to their final locations.

| Task or area touched | Primary document to read |
|---|---|
| System boundaries, new modules, external services | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Formatting, naming, error handling, adding dependencies | [CONVENTIONS.md](CONVENTIONS.md) |
| Authentication, authorization, secrets, input validation | [SECURITY.md](SECURITY.md) |
| Writing tests, running test commands, verification | [TESTING.md](TESTING.md) |
| Visual tokens, typography, colors, anti-slop rules | [DESIGN.md](DESIGN.md) |
| Framework rendering, styling, view state management | [UI.md](UI.md) |
| Creating or modifying UI components, reuse rules | [COMPONENTS.md](COMPONENTS.md) |
| User journeys, UX heuristics, state handling, errors | [UX.md](UX.md) |
| API endpoints, contracts, webhooks, integrations | [API.md](API.md) |
| Database schema, migrations, data integrity, queries | [DATABASE.md](DATABASE.md) |
| CI/CD, environments, release, operations, rollbacks | [DEPLOYMENT.md](DEPLOYMENT.md) |

## Product thinking before implementing

Before implementing a substantial feature, workflow, integration, or data-model change, answer the applicable questions. For a narrow bug fix or maintenance task, answer only what is relevant rather than completing this as a ceremony.

1. **Who is the user or actor?** What role, permissions, and context apply?
2. **What goal or problem is being addressed?** What observable outcome should improve?
3. **What is the scope boundary?** What is explicitly included and excluded?
4. **What happens on failure?** How can the user or calling system recover from validation, network, provider, or persistence failures?
5. **Which states matter?** For UI flows, consider the states in `UX.md` that apply; for APIs, jobs, or CLIs, consider pending, partial, failed, retried, and completed outcomes as relevant.
6. **Can existing building blocks be reused?** Inspect current components, helpers, endpoints, schemas, and conventions before adding new ones.
7. **What are the security and privacy implications?** Consider authorization, ownership, tenant boundaries, sensitive data, abuse, and retention.
8. **What does acceptance look like?** Define observable acceptance criteria and how they can be verified.
9. **What compatibility or data-integrity risks exist?** Consider existing consumers, migrations, backward compatibility, duplicate operations, and concurrent changes.
10. **How will the outcome be observed?** Identify useful logs, metrics, user feedback, or operational signals where appropriate.

## Rules of work

- Inspect relevant code and existing documentation before editing.
- Follow the actual package manager, formatting, testing, and build conventions in this repository.
- Prefer the smallest coherent change that solves the requested problem.
- Do not add dependencies, rewrite architecture, or perform unrelated refactors without justification.
- Do not expose secrets, personal data, or private infrastructure details.
- Preserve documented API, data, and compatibility contracts unless the task explicitly authorizes a change.
- Update tests and relevant docs when behavior changes.
- Never claim checks passed unless they were run and observed.

## Useful commands

| Purpose | Command | Verified? |
|---|---|---|
| Install dependencies | [Command] | [Yes / No] |
| Run locally | [Command] | [Yes / No] |
| Test (unit / all) | [Command] | [Yes / No] |
| Lint / format check | [Command] | [Yes / No] |
| Type-check | [Command] | [Yes / No] |
| Build | [Command] | [Yes / No] |

## Anti-patterns

- **Speculative rewriting:** Replacing working code with an entirely new library or pattern without task mandate.
- **Silent failure assumptions:** Assuming tests passed without executing them or reading the exit status.
- **Scope creep:** "Fixing" or reformatting unrelated files in the same pull request or commit.
- **Client-only security:** Hiding a button or page in the UI and assuming backend access is protected.
- **Dependency bloat:** Adding a third-party package for a task achievable with 5 lines of standard code.

## Documentation map

This is a reference map, not a mandate to create every file. Remove rows for documents not present in the target project and update the links to match their final location. Keep conditional links in individual docs' "See also" sections aligned with the same actual inventory.

- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Conventions: [CONVENTIONS.md](CONVENTIONS.md)
- Security: [SECURITY.md](SECURITY.md)
- Testing: [TESTING.md](TESTING.md)
- Design: [DESIGN.md](DESIGN.md)
- UI: [UI.md](UI.md)
- Components: [COMPONENTS.md](COMPONENTS.md)
- UX: [UX.md](UX.md)
- API: [API.md](API.md)
- Database: [DATABASE.md](DATABASE.md)
- Deployment: [DEPLOYMENT.md](DEPLOYMENT.md)

## Completion report

When finishing a task, provide a structured completion report:

- **Summary of changes:** What was added, modified, or removed.
- **Files touched:** Explicit list of modified file paths.
- **Commands executed & results:** Exact commands run with pass/fail outcomes.
- **Residual risks & follow-up:** Any edge cases, unverified areas, or pending decisions.
