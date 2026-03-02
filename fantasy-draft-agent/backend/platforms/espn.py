"""
ESPN Fantasy Platform Connector

ESPN has an unofficial API accessible via the `espn_api` Python library.
For auto-picking, we use ESPN's internal draft pick endpoint with cookie auth.

Auth: ESPN uses two cookies — espn_s2 and SWID — for authentication.
      Users can get these from browser DevTools → Application → Cookies → espn.com

ESPN Draft Pick endpoint (internal):
  POST https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league_id}/transactions/
  Requires espn_s2 and SWID cookies.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

import httpx

from draft_engine import DraftState, Pick, Player
from .base import BasePlatformConnector

ESPN_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"


class ESPNConnector(BasePlatformConnector):
    """
    ESPN Fantasy connector.
    - Reads live draft state via ESPN's API
    - Submits picks using ESPN's internal transaction endpoint
    - Falls back to browser automation (Playwright) if API pick fails
    """

    def __init__(
        self,
        draft_id: str,
        user_id: str,
        espn_s2: str,
        swid: str,
        session: Any,
        year: int = 2025,
    ):
        self.league_id = draft_id      # For ESPN, draft_id = league_id
        self.user_id   = user_id
        self.espn_s2   = espn_s2
        self.swid      = swid
        self.session   = session
        self.year      = year
        self._team_id: Optional[int] = None
        self._draft_pick_order: list = []

    @property
    def _cookies(self) -> Dict[str, str]:
        return {"espn_s2": self.espn_s2, "SWID": self.swid}

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (compatible; FantasyDraftAgent/1.0)",
            "Accept": "application/json",
            "X-Fantasy-Platform": "kona-PROD-4e75c-2abb7",
        }

    # ------------------------------------------------------------------
    # connect
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        async with httpx.AsyncClient() as client:
            try:
                await self._fetch_league_meta(client)
            except Exception as e:
                self.session.add_log("warn", f"[espn] connect failed: {e}")
        print(f"[espn] Connected to league {self.league_id}")

    # ------------------------------------------------------------------
    # sync_state
    # ------------------------------------------------------------------

    async def sync_state(self, state: DraftState) -> None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{ESPN_BASE}/seasons/{self.year}/segments/0/leagues/{self.league_id}",
                    params  = {"view": "mDraftDetail"},
                    cookies = self._cookies,
                    headers = self._headers,
                    timeout = 10,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.session.add_log("warn", f"[espn] sync failed: {e}")
                return

        draft_detail = data.get("draftDetail", {})
        picks        = draft_detail.get("picks", [])
        num_teams    = data.get("size", state.num_teams)

        state.num_teams = num_teams

        drafted_ids = set()
        for pk in picks:
            pid = str(pk.get("playerId", ""))
            if pid and pid != "0":
                drafted_ids.add(pid)

        for player in state.available_players:
            # ESPN uses numeric player IDs; try to match
            if player.player_id in drafted_ids:
                player.is_available = False

        total        = len(picks)
        round_idx    = total // num_teams
        pick_in_rnd  = total % num_teams
        state.current_pick_number = total + 1
        state.current_round       = round_idx + 1

        # Determine my draft slot (1-based)
        if state.draft_position == 0:
            state.draft_position = await self._get_draft_position(num_teams)

        if round_idx % 2 == 0:
            my_pick_in_round = state.draft_position - 1
        else:
            my_pick_in_round = num_teams - state.draft_position

        state.is_my_pick = (pick_in_rnd == my_pick_in_round)

    # ------------------------------------------------------------------
    # make_pick
    # ------------------------------------------------------------------

    async def make_pick(self, player: Player, state: DraftState) -> None:
        if not self.espn_s2 or not self.swid:
            raise RuntimeError(
                "ESPN credentials not provided. "
                "Supply espn_s2 cookie and SWID cookie from browser DevTools → "
                "Application → Cookies → espn.com"
            )

        # ESPN expects numeric player IDs
        espn_player_id = self._resolve_espn_player_id(player)

        payload = {
            "actions": [{
                "executionType": "EXECUTED",
                "id":            state.current_pick_number,
                "memberId":      f"{{{self.user_id}}}",
                "playerId":      espn_player_id,
                "scoringPeriodId": state.current_round,
                "teamId":        self._team_id,
                "type":          "DRAFT",
            }]
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{ESPN_BASE}/seasons/{self.year}/segments/0/leagues/{self.league_id}/transactions/",
                    json    = payload,
                    cookies = self._cookies,
                    headers = {**self._headers, "Content-Type": "application/json"},
                    timeout = 10,
                )
                if resp.status_code not in (200, 201):
                    raise RuntimeError(f"ESPN pick API {resp.status_code}: {resp.text[:200]}")
            except httpx.HTTPError as e:
                # If API fails, fall back to Playwright browser automation
                self.session.add_log("warn", f"[espn] API pick failed, trying browser: {e}")
                await self._playwright_pick(player, state)

        print(f"[espn] Pick submitted: {player.name}")

    # ------------------------------------------------------------------
    # Playwright fallback
    # ------------------------------------------------------------------

    async def _playwright_pick(self, player: Player, state: DraftState) -> None:
        """Use headless browser to make pick on ESPN's draft UI."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx     = await browser.new_context()

            # Set ESPN auth cookies
            await ctx.add_cookies([
                {"name": "espn_s2", "value": self.espn_s2, "domain": ".espn.com", "path": "/"},
                {"name": "SWID",    "value": self.swid,    "domain": ".espn.com", "path": "/"},
            ])

            page = await ctx.new_page()
            await page.goto(
                f"https://fantasy.espn.com/football/league/draftclient?leagueId={self.league_id}",
                wait_until="networkidle",
                timeout=30000,
            )

            # Wait for draft board and search for the player
            await page.wait_for_selector(".pick-player-btn, .draft-player", timeout=15000)

            # Try searching for the player by name
            search = page.locator("input[placeholder*='search'], input[placeholder*='Search']").first
            if await search.count() > 0:
                await search.fill(player.name)
                await asyncio.sleep(1)

            # Click the draft/pick button next to the player
            pick_btn = page.locator(f"text={player.name}").locator("..").locator("button").first
            if await pick_btn.count() > 0:
                await pick_btn.click()
                self.session.add_log("info", f"[espn] Browser pick submitted: {player.name}")
            else:
                raise RuntimeError(f"Could not find pick button for {player.name} in ESPN draft UI")

            await asyncio.sleep(1)
            await browser.close()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _fetch_league_meta(self, client: httpx.AsyncClient) -> None:
        resp = await client.get(
            f"{ESPN_BASE}/seasons/{self.year}/segments/0/leagues/{self.league_id}",
            params  = {"view": "mSettings"},
            cookies = self._cookies,
            headers = self._headers,
            timeout = 10,
        )
        resp.raise_for_status()
        data = resp.json()

        for team in data.get("teams", []):
            for member in team.get("owners", []):
                if member.strip("{}") == self.user_id.strip("{}"):
                    self._team_id = team.get("id")
                    break

        num = data.get("size", 12)
        self.session.state.num_teams = num

    async def _get_draft_position(self, num_teams: int) -> int:
        """Attempt to resolve draft slot from league data."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{ESPN_BASE}/seasons/{self.year}/segments/0/leagues/{self.league_id}",
                    params  = {"view": "mDraftDetail"},
                    cookies = self._cookies,
                    headers = self._headers,
                    timeout = 10,
                )
                resp.raise_for_status()
                data = resp.json()
                picks = data.get("draftDetail", {}).get("picks", [])
                for pk in picks:
                    if str(pk.get("teamId")) == str(self._team_id):
                        return int(pk.get("overallPickNumber", 1)) % num_teams or num_teams
            except Exception:
                pass
        return 1   # Default to first pick

    def _resolve_espn_player_id(self, player: Player) -> int:
        """ESPN uses numeric player IDs. Try to extract from our player_id."""
        try:
            return int(player.player_id)
        except (ValueError, TypeError):
            # player_id might be a Sleeper-format ID; ESPN match would need
            # a separate ID mapping table. Log a warning.
            self.session.add_log(
                "warn",
                f"[espn] Cannot resolve ESPN ID for {player.name} (id={player.player_id}). "
                "Ensure players were loaded from ESPN source."
            )
            return 0
