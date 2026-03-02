"""
Fantasy Draft Agent — FastAPI Backend

Endpoints:
  GET  /api/players           → ranked player list
  POST /api/session           → create/join a draft session
  GET  /api/session/{id}      → session state
  POST /api/session/{id}/pause
  POST /api/session/{id}/resume
  POST /api/session/{id}/pick  → manual pick override
  WS   /ws/{session_id}       → real-time draft events

The agent loop runs as a background asyncio task per session.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from draft_engine import (
    DraftState,
    Player,
    RosterSettings,
    ScoringSettings,
    compute_vbd,
    draft_strategy_summary,
    pick_player,
)
from player_data import load_players
from platforms.sleeper import SleeperConnector
from platforms.espn import ESPNConnector
from platforms.yahoo import YahooConnector

load_dotenv()

# ---------------------------------------------------------------------------
# Session store (in-memory)
# ---------------------------------------------------------------------------

class DraftSession:
    def __init__(self, session_id: str, platform: str, config: dict):
        self.session_id    = session_id
        self.platform      = platform
        self.config        = config
        self.state         = DraftState()
        self.connector     = None
        self.agent_task    = None
        self.paused        = False
        self.clients: List[WebSocket] = []
        self.log: List[dict] = []

    async def broadcast(self, msg: dict) -> None:
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(msg))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.remove(ws)

    def add_log(self, level: str, message: str, data: Any = None) -> None:
        entry = {"ts": time.time(), "level": level, "message": message, "data": data}
        self.log.append(entry)


SESSIONS: Dict[str, DraftSession] = {}

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm player data in background
    asyncio.create_task(_prewarm_players())
    yield
    # Cancel all agent tasks on shutdown
    for session in SESSIONS.values():
        if session.agent_task:
            session.agent_task.cancel()

app = FastAPI(title="Fantasy Draft Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve built frontend if dist/ exists
_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")


async def _prewarm_players():
    try:
        scoring = ScoringSettings()
        await load_players(scoring)
        print("[main] Player data pre-warm complete.")
    except Exception as e:
        print(f"[main] Player data pre-warm failed: {e}")

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    platform: str              # "sleeper" | "espn" | "yahoo"
    draft_id: str
    user_id: str
    auth_token: Optional[str] = None  # Sleeper token / ESPN S2+swid / Yahoo OAuth
    swid: Optional[str] = None        # ESPN SWID cookie
    team_id: Optional[str] = None
    num_teams: int = 12
    ppr: float = 0.5                  # 0=std, 0.5=half, 1.0=full PPR
    scoring_override: Optional[dict] = None

class ManualPickRequest(BaseModel):
    player_id: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_scoring(ppr: float, override: Optional[dict]) -> ScoringSettings:
    s = ScoringSettings(reception=ppr)
    if override:
        for k, v in override.items():
            if hasattr(s, k):
                setattr(s, k, float(v))
    return s


def _player_to_dict(p: Player) -> dict:
    return {
        "player_id":       p.player_id,
        "name":            p.name,
        "position":        p.position,
        "team":            p.team,
        "projected_points": round(p.projected_points, 1),
        "ecr_rank":        p.ecr_rank,
        "adp":             round(p.adp, 1),
        "tier":            p.tier,
        "bye_week":        p.bye_week,
        "injury_status":   p.injury_status,
        "vbd_score":       round(p.vbd_score, 2),
        "adp_value":       round(p.adp_value, 1),
        "positional_rank": p.positional_rank,
        "is_available":    p.is_available,
    }


def _state_payload(session: DraftSession) -> dict:
    s = session.state
    return {
        "current_pick":   s.current_pick_number,
        "current_round":  s.current_round,
        "is_my_pick":     s.is_my_pick,
        "draft_position": s.draft_position,
        "num_teams":      s.num_teams,
        "my_roster":      [_player_to_dict(p) for p in s.my_roster],
        "all_picks":      [
            {
                "pick_number": pk.pick_number,
                "round":       pk.round,
                "team_id":     pk.team_id,
                "player":      _player_to_dict(pk.player),
                "reasoning":   pk.reasoning,
            }
            for pk in s.picks
        ],
        "available_top50": [
            _player_to_dict(p)
            for p in s.available_players
            if p.is_available
        ][:50],
        "strategy":       draft_strategy_summary(s),
        "paused":         session.paused,
    }

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/players")
async def get_players(ppr: float = 0.5, position: Optional[str] = None):
    scoring = ScoringSettings(reception=ppr)
    players = await load_players(scoring)
    players = compute_vbd(players, RosterSettings())
    if position:
        players = [p for p in players if p.position.upper() == position.upper()]
    return [_player_to_dict(p) for p in players[:200]]


@app.post("/api/session")
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())[:8]
    session    = DraftSession(session_id, req.platform, req.dict())
    SESSIONS[session_id] = session

    scoring  = _build_scoring(req.ppr, req.scoring_override)
    r_config = RosterSettings(num_teams=req.num_teams)

    session.state.scoring_settings  = scoring
    session.state.roster_settings   = r_config
    session.state.num_teams         = req.num_teams
    session.state.my_team_id        = req.team_id or req.user_id

    # Load and rank players
    players = await load_players(scoring)
    players = compute_vbd(players, r_config)
    session.state.available_players = players

    # Initialise platform connector
    connector = _make_connector(req.platform, req, session)
    session.connector = connector

    # Connect to platform and start agent loop
    try:
        await connector.connect()
    except Exception as e:
        session.add_log("error", f"Platform connection failed: {e}")

    session.agent_task = asyncio.create_task(_agent_loop(session))
    return {"session_id": session_id}


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    session = _get_session(session_id)
    return {**_state_payload(session), "log": session.log[-50:]}


@app.post("/api/session/{session_id}/pause")
async def pause_session(session_id: str):
    session = _get_session(session_id)
    session.paused = True
    session.add_log("info", "Agent paused by user.")
    await session.broadcast({"type": "paused"})
    return {"status": "paused"}


@app.post("/api/session/{session_id}/resume")
async def resume_session(session_id: str):
    session = _get_session(session_id)
    session.paused = False
    session.add_log("info", "Agent resumed by user.")
    await session.broadcast({"type": "resumed"})
    return {"status": "resumed"}


@app.post("/api/session/{session_id}/pick")
async def manual_pick(session_id: str, req: ManualPickRequest):
    """Override: user manually selects a player."""
    session = _get_session(session_id)
    player  = next(
        (p for p in session.state.available_players if p.player_id == req.player_id and p.is_available),
        None,
    )
    if not player:
        raise HTTPException(404, "Player not found or already drafted.")

    await _execute_pick(session, player, reasoning="Manual pick by user.")
    return {"status": "pick submitted"}


def _get_session(session_id: str) -> DraftSession:
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found.")
    return SESSIONS[session_id]


def _make_connector(platform: str, req: CreateSessionRequest, session: DraftSession):
    if platform == "sleeper":
        return SleeperConnector(
            draft_id    = req.draft_id,
            user_id     = req.user_id,
            auth_token  = req.auth_token or "",
            session     = session,
        )
    elif platform == "espn":
        return ESPNConnector(
            draft_id   = req.draft_id,
            user_id    = req.user_id,
            espn_s2    = req.auth_token or "",
            swid       = req.swid or "",
            session    = session,
        )
    elif platform == "yahoo":
        return YahooConnector(
            draft_id   = req.draft_id,
            user_id    = req.user_id,
            auth_token = req.auth_token or "",
            session    = session,
        )
    else:
        raise HTTPException(400, f"Unknown platform: {platform}")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    if session_id not in SESSIONS:
        await websocket.close(code=1008)
        return

    session = SESSIONS[session_id]
    await websocket.accept()
    session.clients.append(websocket)

    # Send current state immediately
    await websocket.send_text(json.dumps({
        "type": "state",
        "data": _state_payload(session),
    }))

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            await _handle_ws_message(session, msg)
    except WebSocketDisconnect:
        session.clients.remove(websocket)
    except Exception as e:
        print(f"[ws] Error: {e}")
        if websocket in session.clients:
            session.clients.remove(websocket)


async def _handle_ws_message(session: DraftSession, msg: dict) -> None:
    t = msg.get("type")
    if t == "pause":
        session.paused = True
        await session.broadcast({"type": "paused"})
    elif t == "resume":
        session.paused = False
        await session.broadcast({"type": "resumed"})
    elif t == "manual_pick":
        pid = msg.get("player_id")
        player = next(
            (p for p in session.state.available_players if p.player_id == pid and p.is_available),
            None,
        )
        if player:
            await _execute_pick(session, player, "Manual override via UI.")

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

async def _agent_loop(session: DraftSession) -> None:
    """Main agent loop: poll for draft state and make picks when it's our turn."""
    while True:
        try:
            if session.paused:
                await asyncio.sleep(2)
                continue

            # Pull latest draft state from platform
            if session.connector:
                await session.connector.sync_state(session.state)

            state = session.state

            # Broadcast updated state
            await session.broadcast({
                "type": "state",
                "data": _state_payload(session),
            })

            if state.is_my_pick:
                # Thinking notification
                await session.broadcast({
                    "type": "agent_thinking",
                    "data": {"message": f"Analysing pick #{state.current_pick_number}…"},
                })

                # Select best player
                best, reasoning = pick_player(state)

                # Notify UI of pending pick
                await session.broadcast({
                    "type": "agent_picking",
                    "data": {
                        "player": _player_to_dict(best),
                        "reasoning": reasoning,
                    },
                })

                # Small pause so user can see the reasoning before auto-pick fires
                await asyncio.sleep(1.5)

                if not session.paused:
                    await _execute_pick(session, best, reasoning)

            await asyncio.sleep(3)   # poll interval

        except asyncio.CancelledError:
            break
        except Exception as e:
            session.add_log("error", f"Agent loop error: {e}")
            await session.broadcast({"type": "error", "data": {"message": str(e)}})
            await asyncio.sleep(5)


async def _execute_pick(session: DraftSession, player: Player, reasoning: str) -> None:
    """Submit pick to platform, update local state, broadcast result."""
    state = session.state

    # Submit to platform
    if session.connector:
        try:
            await session.connector.make_pick(player, state)
        except Exception as e:
            session.add_log("error", f"Pick submission failed: {e}")
            await session.broadcast({"type": "error", "data": {"message": f"Pick failed: {e}"}})
            return

    # Mark player as drafted
    player.is_available = False
    state.my_roster.append(player)

    from draft_engine import Pick
    pick = Pick(
        pick_number = state.current_pick_number,
        round       = state.current_round,
        team_id     = state.my_team_id,
        player      = player,
        reasoning   = reasoning,
    )
    state.picks.append(pick)
    state.current_pick_number += 1
    state.is_my_pick = False

    session.add_log("pick", f"Picked {player.name} ({player.position})", {"reasoning": reasoning})

    await session.broadcast({
        "type": "pick_confirmed",
        "data": {
            "player":    _player_to_dict(player),
            "reasoning": reasoning,
            "roster":    [_player_to_dict(p) for p in state.my_roster],
        },
    })
