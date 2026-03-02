# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working with this repository.

## Repository Status

This is a **newly initialized repository** with no source code yet. This CLAUDE.md serves as a foundational guide and should be updated as the project evolves.

- **Remote**: `http://local_proxy@127.0.0.1:62233/git/jbob06/test`
- **Owner**: jbob06

---

## Development Branch Convention

When working on issues or features via Claude Code:

- Feature branches follow the pattern: `claude/<task-slug>-<session-id>`
- Always develop on the designated branch and push there — never to `main` or `master` without explicit permission
- Use `git push -u origin <branch-name>` when pushing

---

## General Conventions (update as project grows)

### Commit Messages

- Use clear, imperative-mood subject lines (e.g., `Add user authentication`, `Fix null pointer in parser`)
- Keep subject lines under 72 characters
- Reference issue numbers where applicable (e.g., `Fix login bug (#42)`)

### Code Style

- Follow the style and formatting conventions of the language/framework adopted for this project
- Add linter and formatter configuration files (e.g., `.eslintrc`, `.prettierrc`, `pyproject.toml`) as the stack is chosen, and document them here

### Testing

- Write tests alongside new features
- All tests must pass before merging
- Document test commands here once a framework is in place

### File Organization

- Document the directory structure here once source code is added
- Keep configuration files at the root level
- Place source code in a clearly named top-level directory (`src/`, `app/`, `lib/`, etc.)

---

## Workflow for AI Assistants

1. **Read this file first** before making any changes
2. **Read relevant source files** before proposing or making edits — do not modify code you haven't read
3. **Keep changes minimal** — only change what is directly required by the task
4. **Do not push to `main`** — always use the designated feature branch
5. **Update this file** whenever significant architectural decisions are made, new tooling is added, or conventions change

---

## Updating This File

This CLAUDE.md should be updated whenever:

- A technology stack or framework is chosen
- New tooling (linters, formatters, test runners, CI/CD) is added
- Architectural patterns or directory conventions are established
- New development workflows are adopted

Keep this file accurate and concise — it is the primary reference for AI assistants onboarding to this codebase.
