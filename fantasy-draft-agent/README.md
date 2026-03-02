# Fantasy Draft Agent

An AI-powered fantasy football draft agent that auto-picks for you on **Sleeper**, **ESPN**, and **Yahoo Fantasy** using industry-best strategies. Monitor every decision in real time through a live web interface.

---

## Features

| Feature | Details |
|---|---|
| **Value Based Drafting (VBD)** | Calculates VORP (Value Over Replacement Player) for every eligible player |
| **Expert Consensus Rankings** | Pulls live ECR from FantasyPros as the foundational signal |
| **ADP Value Detection** | Identifies players going later than experts expect — take them early |
| **Positional Scarcity Scoring** | Adjusts picks when top-tier players at a position are running out |
| **Tier-Based Selection** | Prioritises tier-1/2 players when they are still on the board |
| **Roster Construction Awareness** | Balances QB/RB/WR/TE/K/DEF slots as the roster fills |
| **Round-Phase Strategy** | Early rounds = pure VBD. Middle = VBD + needs. Late = handcuffs, upside, streaming |
| **Injury Awareness** | Automatically discounts Questionable, Doubtful, Out, and IR players |
| **Multi-Platform** | Sleeper (full API), ESPN (API + Playwright), Yahoo (OAuth + Playwright) |
| **Real-Time UI** | WebSocket-powered draft board, agent reasoning, live roster, pick log |
| **Manual Override** | Pause the agent and make your own picks any time |

---

## Draft Strategy Deep Dive

### Value Based Drafting (VBD / VORP)

The engine calculates a **replacement level** for each position — the projected points of the first player you could find on waivers after a standard draft. Every player's `VBD score = Projected Points − Replacement Level`.

- **QB replacement** ≈ 13th QB (streaming is viable, so QB replacement is high)
- **RB replacement** ≈ 37th RB (scarce position, replacement value is low)
- **WR replacement** ≈ 37th WR
- **TE replacement** ≈ 13th TE

Drafting the player with the highest VBD score maximises your edge over the field.

### Multi-Phase Strategy

| Phase | Rounds | Logic |
|---|---|---|
| **Early** | 1–3 | Pure VBD — take the highest value player regardless of position |
| **Middle** | 4–8 | VBD weighted by positional need and scarcity. Avoid stacking one position |
| **Late** | 9+ | Handcuffs behind elite RBs, high-upside WR fliers, streaming QB/DST |

### Expert Consensus Integration

Player projections and rankings come from **FantasyPros** (free public pages):
- Season-long projections (`/nfl/projections/{pos}.php?week=draft`)
- Expert Consensus Rankings (`/nfl/rankings/consensus-cheatsheets.php`)

These are merged with **Sleeper's player metadata** (bye weeks, injury status, team).

---

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium          # only needed for ESPN/Yahoo auto-pick fallback
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                          # runs on http://localhost:5173
```

Open http://localhost:5173 in your browser.

### 3. Production build (optional)

```bash
cd frontend && npm run build         # outputs to frontend/dist/
# FastAPI will serve dist/ automatically when backend runs
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Platform Setup

### Sleeper

1. Log into Sleeper in your browser
2. Open DevTools → Application → Local Storage → `https://api.sleeper.app`
3. Copy the value of `sleeper_token`
4. Find your **Draft ID** from the draft URL: `sleeper.app/draft/nfl/{DRAFT_ID}`
5. Find your **User ID**: Sleeper settings → Account → copy the numeric ID

**Auto-pick capability**: Full — Sleeper's API is used directly.

---

### ESPN

1. Log into ESPN Fantasy in your browser
2. Open DevTools → Application → Cookies → `espn.com`
3. Copy `espn_s2` (long string starting with `AE`) and `SWID` (a GUID like `{xxxxxxxx-...}`)
4. Your **League ID** is in the URL: `fantasy.espn.com/football/league?leagueId=XXXXXXXX`

**Auto-pick capability**: ESPN internal API is tried first; Playwright headless browser is the fallback.

---

### Yahoo

1. Create a Yahoo developer app at https://developer.yahoo.com/apps/create/
   - Application Name: anything
   - Redirect URI: `http://localhost:8000/auth/yahoo/callback`
   - API Permissions: Fantasy Sports → Read/Write
2. Copy `client_id` and `client_secret` to `.env`
3. Your **League Key** is in the URL: `football.fantasysports.yahoo.com/f1/{LEAGUE_ID}` → key format: `nfl.l.{LEAGUE_ID}`

**Auto-pick capability**: Yahoo API is tried first; Playwright is the fallback (may require interactive login in a visible browser window).

---

## Project Structure

```
fantasy-draft-agent/
├── backend/
│   ├── main.py            FastAPI app, WebSocket server, session management
│   ├── draft_engine.py    VBD algorithm, strategy logic, pick selection
│   ├── player_data.py     FantasyPros + Sleeper data fetching & merging
│   ├── platforms/
│   │   ├── base.py        Abstract connector interface
│   │   ├── sleeper.py     Sleeper REST + WebSocket connector
│   │   ├── espn.py        ESPN API + Playwright connector
│   │   └── yahoo.py       Yahoo OAuth2 + Playwright connector
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx         Main app + WebSocket client
│   │   ├── types.ts        Shared TypeScript types
│   │   └── components/
│   │       ├── SetupForm.tsx   Platform configuration UI
│   │       ├── AgentPanel.tsx  Real-time agent status & reasoning
│   │       ├── PlayerList.tsx  Available players ranked by VBD
│   │       ├── TeamRoster.tsx  Live roster view
│   │       └── DraftBoard.tsx  Full draft grid
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── .env.example
└── README.md
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/players` | All players ranked by VBD (query: `ppr`, `position`) |
| `POST` | `/api/session` | Create a new draft session |
| `GET` | `/api/session/{id}` | Current session state |
| `POST` | `/api/session/{id}/pause` | Pause auto-pick |
| `POST` | `/api/session/{id}/resume` | Resume auto-pick |
| `POST` | `/api/session/{id}/pick` | Manual pick override |
| `WS` | `/ws/{id}` | Real-time draft events |

---

## Disclaimers

- **Sleeper pick API** is not publicly documented; it may change without notice.
- **ESPN and Yahoo** pick APIs are internal/unofficial endpoints. Browser automation (Playwright) is the reliable fallback.
- This tool is for personal use in your own fantasy leagues. Check your platform's terms of service.
- Player data from FantasyPros is public but scraping is rate-limited — avoid running the agent multiple times in quick succession to avoid being blocked.
