# Copilot Instructions — aust_hackathon26

## Project context is mandatory

`PROJECT_CONTEXT.md` at the repository root is the single source of truth for this project.

**Before starting any task:**
1. Read `PROJECT_CONTEXT.md` in full.
2. Follow the stack, structure, and conventions it describes. If the task conflicts with it, say so before proceeding.

**After completing any task that changes the project** (new files, dependencies, architecture, config, run commands, decisions, bugs found), you MUST update `PROJECT_CONTEXT.md`:
- Update the relevant section(s) — Tech Stack, Project Structure, How to Run, Conventions, Current State, Next Steps, Known Issues.
- Record any non-trivial decision in **Architecture & Key Decisions** with a new `D-NNN` ID and the reason.
- Append a row to the **Changelog** table (date, who, one-line summary).
- Bump the `Last updated` date at the top.
- Tick off completed items in **Next Steps** and add any newly discovered work.

Do not finish a task without doing this. Keep the file concise — replace stale content rather than appending duplicates.

## General rules

- Do not create new markdown docs for changes; update `PROJECT_CONTEXT.md` instead.
- Prefer editing existing files over creating new ones.
- Never commit secrets; use environment variables and document them in `PROJECT_CONTEXT.md` (names only, never values).
