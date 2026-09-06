# AGENTS.md — aust_hackathon26

This file applies to every AI coding agent working in this repository (GitHub Copilot, Claude, Cursor, Codex, etc.).

## Step 0: Load project knowledge

You do **not** have built-in knowledge of this codebase. All project knowledge lives in one file:

**`PROJECT_CONTEXT.md`** (repository root)

Before doing anything else:

1. Read `PROJECT_CONTEXT.md` in full — overview, tech stack, structure, how to run, decisions, conventions, current state, next steps, known issues.
2. Treat it as the source of truth. If the user's request conflicts with it, point out the conflict before proceeding.
3. If a section is marked `TODO`, that information is genuinely unknown — ask the user or inspect the code; do not invent it.

## Step N: Keep project knowledge current

After any task that changes the project (files, dependencies, architecture, config, run commands, decisions, bugs found), update `PROJECT_CONTEXT.md`:

- Update the affected sections (Tech Stack, Project Structure, How to Run, Conventions, Current State, Next Steps, Known Issues).
- Record non-trivial decisions in **Architecture & Key Decisions** with a new `D-NNN` ID and the reason.
- Append a row to the **Changelog**.
- Bump the `Last updated` date at the top.
- Tick completed **Next Steps** and add newly discovered work.

A task is not finished until `PROJECT_CONTEXT.md` reflects it. Replace stale content instead of appending duplicates; keep the file concise.

## Rules

- Do not create new markdown docs for changes — update `PROJECT_CONTEXT.md`.
- Prefer editing existing files over creating new ones.
- Never commit secrets. Use environment variables and list their **names only** in `PROJECT_CONTEXT.md`.
- Follow the commit and branch conventions defined in `PROJECT_CONTEXT.md`.
