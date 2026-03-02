"""
Yahoo Fantasy Platform Connector

Yahoo has an official Fantasy Sports API (OAuth2).
Pick endpoint requires OAuth access token.

Setup:
  1. Create a Yahoo developer app at https://developer.yahoo.com/apps/create/
  2. Set Redirect URI to http://localhost:8000/auth/yahoo/callback
  3. Copy client ID and secret to .env
  4. The backend will generate an auth URL for the user to visit

Yahoo Draft Pick API:
  PUT https://fantasysports.yahooapis.com/fantasy/v2/league/{league_id}/team/{team_id}/roster
  (queue a player) then confirm pick via their draft endpoint
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from draft_engine import DraftState, Pick, Player
from .base import BasePlatformConnector

YAHOO_API_BASE  = "https://fantasysports.yahooapis.com/fantasy/v2"
YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
YAHOO_AUTH_URL  = "https://api.login.yahoo.com/oauth2/request_auth"


class YahooConnector(BasePlatformConnector):
    """
    Yahoo Fantasy connector.
    - OAuth2 authentication
    - REST API for reading draft state
    - API or Playwright automation for submitting picks
    """

    def __init__(
        self,
        draft_id: str,
        user_id: str,
        auth_token: str,       # Yahoo OAuth2 access token
        session: Any,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        token_expiry: Optional[float] = None,
    ):
        self.league_key    = draft_id     # Yahoo format: "nfl.l.{league_id}"
        self.user_id       = user_id
        self.access_token  = auth_token
        self.refresh_token = refresh_token
        self.client_id     = client_id
        self.client_secret = client_secret
        self.token_expiry  = token_expiry or 0
        self.session       = session
        self._team_key: Optional[str] = None
        self._game_key: str = "nfl"

    @property
    def _auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept":        "application/json",
        }

    # ------------------------------------------------------------------
    # connect
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        await self._ensure_token_valid()
        async with httpx.AsyncClient() as client:
            await self._fetch_team_key(client)
        print(f"[yahoo] Connected to league {self.league_key}")

    # ------------------------------------------------------------------
    # sync_state
    # ------------------------------------------------------------------

    async def sync_state(self, state: DraftState) -> None:
        await self._ensure_token_valid()

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{YAHOO_API_BASE}/league/{self.league_key}/draftresults",
                    params  = {"format": "json"},
                    headers = self._auth_headers,
                    timeout = 10,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.session.add_log("warn", f"[yahoo] sync failed: {e}")
                return

        try:
            picks = (
                data.get("fantasy_content", {})
                    .get("league", [{}])[1]
                    .get("draft_results", {})
                    .get("draft_result", [])
            )
        except (KeyError, IndexError, TypeError):
            picks = []

        num_teams = state.num_teams
        drafted_names = set()

        for pk in picks:
            if isinstance(pk, dict):
                name = pk.get("pick", {}).get("player_key", "")
                drafted_names.add(name)

        total       = len(picks)
        round_idx   = total // num_teams
        pick_in_rnd = total % num_teams

        state.current_pick_number = total + 1
        state.current_round       = round_idx + 1

        if state.draft_position == 0:
            state.draft_position = await self._get_draft_position()

        if round_idx % 2 == 0:
            my_pick_in_round = state.draft_position - 1
        else:
            my_pick_in_round = num_teams - state.draft_position

        state.is_my_pick = (pick_in_rnd == my_pick_in_round)

    # ------------------------------------------------------------------
    # make_pick
    # ------------------------------------------------------------------

    async def make_pick(self, player: Player, state: DraftState) -> None:
        await self._ensure_token_valid()

        if not self.access_token:
            raise RuntimeError(
                "Yahoo OAuth2 token not provided. "
                "Complete OAuth flow first (visit /auth/yahoo in the web UI)."
            )

        # Yahoo draft pick — add player to team roster via the transactions endpoint
        yahoo_player_key = self._resolve_yahoo_player_key(player)

        payload = {
            "fantasy_content": {
                "transaction": {
                    "type":       "draft",
                    "player":     {"player_key": yahoo_player_key, "transaction_data": {"type": "add", "destination_team_key": self._team_key}},
                    "pick_order": state.current_pick_number,
                }
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{YAHOO_API_BASE}/league/{self.league_key}/transactions",
                    json    = payload,
                    headers = {**self._auth_headers, "Content-Type": "application/json"},
                    timeout = 10,
                )
                if resp.status_code not in (200, 201):
                    raise RuntimeError(
                        f"Yahoo pick API returned {resp.status_code}: {resp.text[:300]}"
                    )
            except Exception as e:
                self.session.add_log("warn", f"[yahoo] API pick failed: {e}, trying browser")
                await self._playwright_pick(player, state)

        print(f"[yahoo] Pick submitted: {player.name}")

    # ------------------------------------------------------------------
    # Playwright fallback
    # ------------------------------------------------------------------

    async def _playwright_pick(self, player: Player, state: DraftState) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=False)  # visible for Yahoo auth
            ctx     = await browser.new_context()
            page    = await ctx.new_page()

            # Yahoo requires interactive login; open the draft room URL
            league_id = self.league_key.split(".")[-1]
            draft_url = f"https://football.fantasysports.yahoo.com/f1/{league_id}/draftclient"
            await page.goto(draft_url, wait_until="networkidle", timeout=30000)

            # If redirected to login, wait for user
            if "login" in page.url:
                self.session.add_log(
                    "warn",
                    "[yahoo] Browser requires manual Yahoo login. "
                    "Please log in to Yahoo Fantasy in the browser window."
                )
                await page.wait_for_url("**/draftclient*", timeout=120000)

            # Find and click the player row
            await page.wait_for_selector(".player-draft-btn, .draft-button", timeout=15000)
            player_row = page.locator(f"text={player.name}").first
            if await player_row.count() > 0:
                draft_btn = player_row.locator("..").locator("button").first
                await draft_btn.click()
                self.session.add_log("info", f"[yahoo] Browser pick submitted: {player.name}")
            else:
                raise RuntimeError(f"Could not find {player.name} in Yahoo draft room")

            await asyncio.sleep(1)
            await browser.close()

    # ------------------------------------------------------------------
    # OAuth token refresh
    # ------------------------------------------------------------------

    async def _ensure_token_valid(self) -> None:
        if not self.refresh_token or not self.client_id or not self.client_secret:
            return  # No refresh capability; token may expire
        if time.time() < self.token_expiry - 60:
            return  # Token still valid

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    YAHOO_TOKEN_URL,
                    data={
                        "grant_type":    "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                    auth=(self.client_id, self.client_secret),
                    timeout=10,
                )
                resp.raise_for_status()
                tokens = resp.json()
                self.access_token  = tokens["access_token"]
                self.refresh_token = tokens.get("refresh_token", self.refresh_token)
                self.token_expiry  = time.time() + int(tokens.get("expires_in", 3600))
                print("[yahoo] OAuth token refreshed.")
            except Exception as e:
                self.session.add_log("warn", f"[yahoo] Token refresh failed: {e}")

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _fetch_team_key(self, client: httpx.AsyncClient) -> None:
        try:
            resp = await client.get(
                f"{YAHOO_API_BASE}/league/{self.league_key}/teams",
                params  = {"format": "json"},
                headers = self._auth_headers,
                timeout = 10,
            )
            resp.raise_for_status()
            data = resp.json()
            teams = (
                data.get("fantasy_content", {})
                    .get("league", [{}])[1]
                    .get("teams", {})
            )
            count = teams.get("count", 0)
            for i in range(count):
                team_data = teams.get(str(i), {}).get("team", [[]])[0]
                for item in team_data:
                    if isinstance(item, dict):
                        managers = item.get("managers", [])
                        for m in managers:
                            if isinstance(m, dict) and m.get("manager", {}).get("guid") == self.user_id:
                                # Get team key from earlier in team_data
                                for d in team_data:
                                    if isinstance(d, dict) and "team_key" in d:
                                        self._team_key = d["team_key"]
                                        break
        except Exception as e:
            self.session.add_log("warn", f"[yahoo] team key fetch failed: {e}")

    async def _get_draft_position(self) -> int:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{YAHOO_API_BASE}/league/{self.league_key}/draftresults",
                    params  = {"format": "json"},
                    headers = self._auth_headers,
                    timeout = 10,
                )
                resp.raise_for_status()
                # Parse first pick by this team to determine draft slot
            except Exception:
                pass
        return 1

    def _resolve_yahoo_player_key(self, player: Player) -> str:
        """Yahoo player keys look like 'nfl.p.12345'. Try to build from player_id."""
        if player.player_id.startswith("nfl.p."):
            return player.player_id
        try:
            return f"nfl.p.{int(player.player_id)}"
        except (ValueError, TypeError):
            return f"nfl.p.{player.player_id}"
