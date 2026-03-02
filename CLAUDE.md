# CLAUDE.md

This file provides guidance to AI assistants (Claude and others) working with this repository.

## Repository Status

This repository contains a **Fantasy Draft Agent** — a full-stack AI-powered auto-drafter for ESPN, Sleeper, and Yahoo Fantasy Football leagues, with a real-time React web interface.

- **Remote**: `http://local_proxy@127.0.0.1:62233/git/jbob06/test`
- **Owner**: jbob06

---

## Active Project: `fantasy-draft-agent/`

### What's been built

A complete fantasy football draft agent with:

- **Backend**: Python/FastAPI with WebSocket server (`backend/main.py`)
- **Draft engine**: VBD (Value Based Drafting / VORP) algorithm, positional scarcity, ADP value, tier bonuses, injury penalties, 3-phase round strategy (`backend/draft_engine.py`)
- **Player data**: FantasyPros scraper + Sleeper API merger, with 102-player built-in seed fallback (`backend/player_data.py`, `backend/seed_players.py`)
- **Platform connectors**: Sleeper (REST + WebSocket), ESPN (internal API + Playwright), Yahoo (OAuth2 + Playwright) (`backend/platforms/`)
- **Frontend**: React + TypeScript + Vite (`frontend/src/`)
  - `SetupForm.tsx` — platform/credential config
  - `AgentPanel.tsx` — live status, strategy, pick reasoning
  - `PlayerList.tsx` — VBD-ranked available players, manual pick override
  - `TeamRoster.tsx` — live roster by position
  - `DraftBoard.tsx` — full snake draft grid

### Stack

| Layer | Tech |
|---|---|
| Backend | Python 3, FastAPI, uvicorn, WebSockets, httpx, BeautifulSoup4, Playwright |
| Frontend | React 18, TypeScript, Vite |
| Platform APIs | Sleeper REST+WS, ESPN internal API, Yahoo OAuth2 Fantasy API |
| Player data | FantasyPros (scraped), Sleeper players API, built-in seed fallback |

### How to run

```bash
# Terminal 1 — Backend (FastAPI on :8000)
cd fantasy-draft-agent/backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend (Vite dev server on :5173)
cd fantasy-draft-agent/frontend
npm run dev
```

Open **http://localhost:5173** in the browser.

### Current state / known issues

- External APIs (FantasyPros, Sleeper) return 403 in this environment — seed player data loads automatically (102 players, 2025 projections)
- VBD scoring confirmed working: McCaffrey #1 RB, Ja'Marr Chase #1 WR by value
- Platform connectors are implemented but need a live draft + real credentials to test end-to-end
- ESPN/Yahoo Playwright fallback requires `playwright install chromium` (already in `requirements.txt`)

### Possible next steps

- Test with a real Sleeper mock draft (easiest platform to start with)
- Add a simulation/mock draft mode so the agent can be demoed without a live league
- Add a Yahoo OAuth2 callback route (`/auth/yahoo/callback`) to the FastAPI app
- Add draft session persistence (SQLite) so sessions survive server restarts
- Expand the seed player dataset (more depth players, weekly updates from a free source)
- Frontend polish: pick timer countdown, sound alerts when it's your turn

---

## Development Branch Convention

When working on issues or features via Claude Code:

- Feature branches follow the pattern: `claude/<task-slug>-<session-id>`
- Always develop on the designated branch and push there — never to `main` or `master` without explicit permission
- Use `git push -u origin <branch-name>` when pushing

---

## General Conventions

### Commit Messages

- Use clear, imperative-mood subject lines (e.g., `Add user authentication`, `Fix null pointer in parser`)
- Keep subject lines under 72 characters
- Reference issue numbers where applicable (e.g., `Fix login bug (#42)`)

### Code Style

- **Python**: follow PEP 8; use type hints; async/await throughout the backend
- **TypeScript**: strict mode enabled; functional React components; no `any` types

### Testing

- Write tests alongside new features
- All tests must pass before merging

### File Organization

```
fantasy-draft-agent/
├── backend/
│   ├── main.py              FastAPI app, WebSocket, session management
│   ├── draft_engine.py      VBD algorithm, strategy, pick selection
│   ├── player_data.py       Data fetching (FantasyPros + Sleeper + seed fallback)
│   ├── seed_players.py      Built-in 102-player dataset (2025 projections)
│   ├── platforms/
│   │   ├── base.py          Abstract connector interface
│   │   ├── sleeper.py       Sleeper REST + WebSocket
│   │   ├── espn.py          ESPN API + Playwright fallback
│   │   └── yahoo.py         Yahoo OAuth2 + Playwright fallback
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.tsx           Main app + WebSocket client
    │   ├── types.ts          Shared TypeScript types
    │   └── components/       SetupForm, AgentPanel, PlayerList, TeamRoster, DraftBoard
    ├── package.json
    ├── tsconfig.json
    └── vite.config.ts        Proxies /api and /ws to backend :8000
```

---

## Workflow for AI Assistants

1. **Read this file first** before making any changes
2. **Read relevant source files** before proposing or making edits — do not modify code you haven't read
3. **Keep changes minimal** — only change what is directly required by the task
4. **Do not push to `main`** — always use the designated feature branch
5. **Update this file** whenever significant architectural decisions are made, new tooling is added, or conventions change
