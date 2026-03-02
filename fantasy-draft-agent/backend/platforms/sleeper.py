"""
Sleeper Platform Connector

Sleeper has an excellent public REST API and a WebSocket for live drafts.

API docs: https://docs.sleeper.app

Auth: Sleeper uses a user auth token stored in the browser's localStorage
      under the key 'sleeper_token'. Users can retrieve it from DevTools.
      Without it, the agent can monitor picks but cannot auto-pick.

Pick endpoint (internal, not officially documented):
  POST https://api.sleeper.app/v1/draft/{draft_id}/pick
  Headers: Authorization: {token}
  Body: {"player_id": "...", "metadata": {"slot_position": "RB", "years_exp": "3"}}
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import httpx
import websockets

from draft_engine import DraftState, Pick, Player
from .base import BasePlatformConnector

if TYPE_CHECKING:
    pass


SLEEPER_BASE   = "https://api.sleeper.app/v1"
SLEEPER_WS_URL = "wss://api.sleeper.app/v1/draft/{draft_id}/ws"


class SleeperConnector(BasePlatformConnector):
    """
    Full integration with Sleeper draft API.
    - Monitors live draft via WebSocket
    - Auto-picks using the internal pick endpoint (requires auth token)
    """

    def __init__(self, draft_id: str, user_id: str, auth_token: str, session: Any):
        self.draft_id   = draft_id
        self.user_id    = user_id
        self.auth_token = auth_token
        self.session    = session
        self._draft_meta: Dict = {}
        self._roster_id: Optional[int] = None
        self._ws_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # connect
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        async with httpx.AsyncClient() as client:
            await self._fetch_draft_meta(client)
            await self._resolve_roster_id(client)

        # Start WebSocket listener in background
        self._ws_task = asyncio.create_task(self._ws_listener())
        print(f"[sleeper] Connected to draft {self.draft_id}")

    # ------------------------------------------------------------------
    # sync_state
    # ------------------------------------------------------------------

    async def sync_state(self, state: DraftState) -> None:
        """Pull current picks from REST API and update draft state."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{SLEEPER_BASE}/draft/{self.draft_id}/picks",
                    timeout=10,
                )
                resp.raise_for_status()
                picks_data = resp.json()
            except Exception as e:
                self.session.add_log("warn", f"[sleeper] sync picks failed: {e}")
                return

        # Build set of drafted player IDs
        drafted_ids = {str(pk.get("player_id")) for pk in picks_data}

        # Mark unavailable
        for player in state.available_players:
            if player.player_id in drafted_ids:
                player.is_available = False

        total_picks     = len(picks_data)
        state.current_pick_number = total_picks + 1
        state.current_round       = (total_picks // state.num_teams) + 1

        # Determine if it's my turn
        # Snake draft: even rounds go in reverse
        round_idx       = total_picks // state.num_teams   # 0-based round
        pick_in_round   = total_picks % state.num_teams    # 0-based pick within round

        if round_idx % 2 == 0:
            my_pick_in_round = state.draft_position - 1
        else:
            my_pick_in_round = state.num_teams - state.draft_position

        state.is_my_pick = (pick_in_round == my_pick_in_round)

        # Update picks log from API
        known_picks = {pk.pick_number for pk in state.picks}
        for pk_data in picks_data:
            pick_num = pk_data.get("pick_no", 0)
            if pick_num in known_picks:
                continue
            pid = str(pk_data.get("player_id", ""))
            player_obj = next(
                (p for p in state.available_players if p.player_id == pid),
                None,
            )
            if player_obj:
                rnd = pk_data.get("round", 1)
                team = str(pk_data.get("picked_by", ""))
                state.picks.append(Pick(
                    pick_number = pick_num,
                    round       = rnd,
                    team_id     = team,
                    player      = player_obj,
                ))
                if team == self.user_id:
                    state.my_roster.append(player_obj)

    # ------------------------------------------------------------------
    # make_pick
    # ------------------------------------------------------------------

    async def make_pick(self, player: Player, state: DraftState) -> None:
        if not self.auth_token:
            raise RuntimeError(
                "No Sleeper auth token provided. "
                "Get it from browser DevTools → Application → Local Storage → 'sleeper_token'."
            )

        payload = {
            "player_id": player.player_id,
            "metadata": {
                "slot_position": player.position,
                "years_exp": "0",
            },
        }
        if self._roster_id is not None:
            payload["roster_id"] = self._roster_id
        payload["picked_by"] = self.user_id
        payload["round"]     = state.current_round
        payload["pick_no"]   = state.current_pick_number

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SLEEPER_BASE}/draft/{self.draft_id}/pick",
                json    = payload,
                headers = {"Authorization": self.auth_token},
                timeout = 10,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Sleeper pick API returned {resp.status_code}: {resp.text[:200]}"
                )

        print(f"[sleeper] Pick submitted: {player.name}")

    # ------------------------------------------------------------------
    # WebSocket listener (receives real-time pick events)
    # ------------------------------------------------------------------

    async def _ws_listener(self) -> None:
        url = SLEEPER_WS_URL.format(draft_id=self.draft_id)
        retry_delay = 2

        while True:
            try:
                async with websockets.connect(url, ping_interval=30) as ws:
                    self.session.add_log("info", "[sleeper] WebSocket connected")
                    retry_delay = 2
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            await self._handle_ws_event(msg)
                        except Exception as e:
                            print(f"[sleeper] WS parse error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.session.add_log("warn", f"[sleeper] WS disconnected: {e}, retrying in {retry_delay}s")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)

    async def _handle_ws_event(self, msg: dict) -> None:
        event_type = msg.get("type")
        payload    = msg.get("payload", {})

        if event_type == "pick_made":
            pid  = str(payload.get("player_id", ""))
            name = payload.get("metadata", {}).get("first_name", "") + " " + payload.get("metadata", {}).get("last_name", "")
            self.session.add_log("info", f"[sleeper] Pick: {name.strip()} (id={pid})")

            # Mark player unavailable in state
            state = self.session.state
            for p in state.available_players:
                if p.player_id == pid:
                    p.is_available = False
                    break

            await self.session.broadcast({
                "type": "external_pick",
                "data": {"player_id": pid, "player_name": name.strip()},
            })

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _fetch_draft_meta(self, client: httpx.AsyncClient) -> None:
        try:
            resp = await client.get(f"{SLEEPER_BASE}/draft/{self.draft_id}", timeout=10)
            resp.raise_for_status()
            self._draft_meta = resp.json()

            # Extract draft position
            slot_to_roster = self._draft_meta.get("slot_to_roster_id", {})
            for slot, roster_id in slot_to_roster.items():
                if str(roster_id) == str(self._roster_id):
                    self.session.state.draft_position = int(slot)
                    break

            settings = self._draft_meta.get("settings", {})
            self.session.state.num_teams = settings.get("teams", 12)
        except Exception as e:
            self.session.add_log("warn", f"[sleeper] draft meta fetch failed: {e}")

    async def _resolve_roster_id(self, client: httpx.AsyncClient) -> None:
        """Find the user's roster_id within the draft."""
        try:
            resp = await client.get(
                f"{SLEEPER_BASE}/draft/{self.draft_id}/picks",
                timeout=10,
            )
            resp.raise_for_status()
            # Check if we have a pick from this user already
            for pk in resp.json():
                if str(pk.get("picked_by")) == self.user_id:
                    self._roster_id = pk.get("roster_id")
                    break

            if self._roster_id is None:
                # Try league rosters
                league_id = self._draft_meta.get("league_id")
                if league_id:
                    r = await client.get(f"{SLEEPER_BASE}/league/{league_id}/rosters", timeout=10)
                    r.raise_for_status()
                    for roster in r.json():
                        if str(roster.get("owner_id")) == self.user_id:
                            self._roster_id = roster.get("roster_id")
                            break
        except Exception as e:
            self.session.add_log("warn", f"[sleeper] roster_id resolution failed: {e}")

    async def disconnect(self) -> None:
        if self._ws_task:
            self._ws_task.cancel()
