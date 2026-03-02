"""
Player Data Module

Fetches and normalises player data from multiple sources:
  1. FantasyPros Expert Consensus Rankings (ECR) — free scrape
  2. FantasyPros Season Projections (by position)
  3. Sleeper player list (name/team/bye metadata)
  4. Sleeper ADP data

All sources are merged into a unified list of draft_engine.Player objects.
Data is cached in memory for the lifetime of the process.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from draft_engine import Player, ScoringSettings


# ---------------------------------------------------------------------------
# FantasyPros helpers
# ---------------------------------------------------------------------------

_FP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Referer": "https://www.fantasypros.com/",
}

_FP_PROJ_URLS = {
    "QB":  "https://www.fantasypros.com/nfl/projections/qb.php?week=draft",
    "RB":  "https://www.fantasypros.com/nfl/projections/rb.php?week=draft",
    "WR":  "https://www.fantasypros.com/nfl/projections/wr.php?week=draft",
    "TE":  "https://www.fantasypros.com/nfl/projections/te.php?week=draft",
    "K":   "https://www.fantasypros.com/nfl/projections/k.php?week=draft",
    "DST": "https://www.fantasypros.com/nfl/projections/dst.php?week=draft",
}

_FP_ECR_URL = "https://www.fantasypros.com/nfl/rankings/consensus-cheatsheets.php"

_SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"
_SLEEPER_ADP_URL     = "https://api.sleeper.app/v1/draft/nfl/pre/{year}"


# ---------------------------------------------------------------------------
# Scrape FantasyPros ECR
# ---------------------------------------------------------------------------

async def _fetch_ecr(client: httpx.AsyncClient) -> Dict[str, dict]:
    """
    Returns {player_name -> {"ecr_rank": int, "tier": int, "adp": float}}
    """
    try:
        resp = await client.get(_FP_ECR_URL, headers=_FP_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[player_data] ECR fetch failed: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "lxml")
    rows = soup.select("table#data tbody tr")
    result: Dict[str, dict] = {}

    for row in rows:
        cells = row.select("td")
        if len(cells) < 4:
            continue
        try:
            rank = int(cells[0].get_text(strip=True))
            name_cell = cells[2]
            name = name_cell.select_one("a")
            name = name.get_text(strip=True) if name else name_cell.get_text(strip=True)
            name = _normalise_name(name)

            adp_text = cells[-1].get_text(strip=True).replace("—", "9999")
            adp = float(adp_text) if adp_text else 9999.0

            tier_class = row.get("class", [])
            tier = 10
            for cls in tier_class:
                m = re.search(r"tier-(\d+)", cls)
                if m:
                    tier = int(m.group(1))
                    break

            result[name] = {"ecr_rank": rank, "tier": tier, "adp": adp}
        except (ValueError, IndexError):
            continue

    print(f"[player_data] ECR: loaded {len(result)} players")
    return result


# ---------------------------------------------------------------------------
# Scrape FantasyPros Projections
# ---------------------------------------------------------------------------

async def _fetch_projections_for_position(
    client: httpx.AsyncClient,
    position: str,
    url: str,
    scoring: ScoringSettings,
) -> List[dict]:
    """Returns list of {name, team, projected_points} for one position."""
    try:
        resp = await client.get(url, headers=_FP_HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[player_data] Projections fetch failed for {position}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    rows = soup.select("table#data tbody tr")
    results = []

    for row in rows:
        cells = row.select("td")
        if len(cells) < 3:
            continue
        try:
            name_cell = cells[0]
            player_link = name_cell.select_one("a.player-name")
            if not player_link:
                continue
            name = _normalise_name(player_link.get_text(strip=True))
            team_span = name_cell.select_one("small")
            team = team_span.get_text(strip=True) if team_span else "?"

            # Extract relevant stat columns and compute projected fantasy points
            nums = []
            for c in cells[1:]:
                txt = c.get_text(strip=True).replace(",", "")
                try:
                    nums.append(float(txt))
                except ValueError:
                    nums.append(0.0)

            pts = _calculate_projected_points(position, nums, scoring)
            results.append({"name": name, "team": team, "projected_points": pts, "position": position})
        except (ValueError, IndexError):
            continue

    print(f"[player_data] Projections {position}: {len(results)} players")
    return results


def _calculate_projected_points(
    position: str, cols: List[float], scoring: ScoringSettings
) -> float:
    """Map scraped stat columns to fantasy points per position."""
    # FantasyPros column order (season projections, week=draft):
    # QB:  PassAtt, PassCmp, PassYds, PassTD, PassInt, RushAtt, RushYds, RushTD, FL, Pts
    # RB:  RushAtt, RushYds, RushTD, Rec, RecYds, RecTD, FL, Pts
    # WR:  Rec, RecYds, RecTD, RushAtt, RushYds, RushTD, FL, Pts
    # TE:  Rec, RecYds, RecTD, FL, Pts
    # K:   FG, FGA, XPT, Pts
    # DST: Sack, Int, FR, FF, TD, Safety, PA, YdsAllowed, Pts

    # If the last column looks like total points (close to expected range) use it
    if len(cols) >= 1 and cols[-1] > 0:
        return cols[-1]   # FP already provides total points in last col

    # Fallback manual calculation
    pts = 0.0
    try:
        if position == "QB" and len(cols) >= 9:
            pts += cols[2] * scoring.pass_yd
            pts += cols[3] * scoring.pass_td
            pts += cols[4] * scoring.pass_int
            pts += cols[6] * scoring.rush_yd
            pts += cols[7] * scoring.rush_td
        elif position == "RB" and len(cols) >= 7:
            pts += cols[1] * scoring.rush_yd
            pts += cols[2] * scoring.rush_td
            pts += cols[3] * scoring.reception
            pts += cols[4] * scoring.rec_yd
            pts += cols[5] * scoring.rec_td
        elif position == "WR" and len(cols) >= 7:
            pts += cols[0] * scoring.reception
            pts += cols[1] * scoring.rec_yd
            pts += cols[2] * scoring.rec_td
        elif position == "TE" and len(cols) >= 4:
            pts += cols[0] * scoring.reception
            pts += cols[1] * scoring.rec_yd
            pts += cols[2] * scoring.rec_td
    except IndexError:
        pass
    return pts


# ---------------------------------------------------------------------------
# Sleeper player metadata (name, team, bye week, position)
# ---------------------------------------------------------------------------

async def _fetch_sleeper_players(client: httpx.AsyncClient) -> Dict[str, dict]:
    """Returns {player_id -> {name, position, team, bye}}"""
    try:
        resp = await client.get(_SLEEPER_PLAYERS_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[player_data] Sleeper players fetch failed: {e}")
        return {}

    result: Dict[str, dict] = {}
    for pid, p in data.items():
        if p.get("active") and p.get("fantasy_positions"):
            pos_list = p.get("fantasy_positions", [])
            pos = pos_list[0] if pos_list else ""
            if pos not in ("QB", "RB", "WR", "TE", "K", "DEF"):
                continue
            full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
            result[pid] = {
                "name": _normalise_name(full_name),
                "position": pos,
                "team": p.get("team", "FA") or "FA",
                "bye": p.get("bye_week", 0),
                "injury_status": p.get("injury_status", "") or "",
            }
    print(f"[player_data] Sleeper players: {len(result)} eligible")
    return result


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(r"\s+(Jr\.?|Sr\.?|II|III|IV|V)$", re.IGNORECASE)
_TEAM_RE   = re.compile(r"\s+[A-Z]{2,4}$")


def _normalise_name(name: str) -> str:
    name = name.strip()
    name = _SUFFIX_RE.sub("", name)
    name = _TEAM_RE.sub("", name)
    return name.strip()


def _names_match(a: str, b: str) -> bool:
    """Fuzzy name match: ignore case and suffix differences."""
    return _normalise_name(a).lower() == _normalise_name(b).lower()


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

_PLAYER_CACHE: Optional[List[Player]] = None


async def load_players(
    scoring: ScoringSettings,
    season: int = 2025,
    force_refresh: bool = False,
) -> List[Player]:
    """
    Fetch and merge all player data sources.  Results are cached in-process.
    Falls back to built-in seed data when external APIs are unavailable.
    """
    global _PLAYER_CACHE
    if _PLAYER_CACHE and not force_refresh:
        return _PLAYER_CACHE

    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Fetch all sources concurrently
        ecr_task   = asyncio.create_task(_fetch_ecr(client))
        sl_task    = asyncio.create_task(_fetch_sleeper_players(client))
        proj_tasks = {
            pos: asyncio.create_task(_fetch_projections_for_position(client, pos if pos != "DEF" else "DEF", url, scoring))
            for pos, url in _FP_PROJ_URLS.items()
        }

        ecr_data     = await ecr_task
        sleeper_data = await sl_task
        proj_data: Dict[str, List[dict]] = {}
        for pos, task in proj_tasks.items():
            proj_data[pos] = await task

    # Build name→projection lookup
    proj_lookup: Dict[str, dict] = {}
    for pos, rows in proj_data.items():
        real_pos = "DEF" if pos == "DST" else pos
        for row in rows:
            proj_lookup[row["name"].lower()] = {**row, "position": real_pos}

    # Build final player list from Sleeper (most comprehensive player set)
    players: List[Player] = []
    seen_names: set = set()

    for pid, meta in sleeper_data.items():
        name_lower = meta["name"].lower()
        ecr = ecr_data.get(meta["name"], {})
        proj = proj_lookup.get(name_lower, {})

        # Deduplicate by name (keep first occurrence)
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        p = Player(
            player_id        = pid,
            name             = meta["name"],
            position         = meta["position"],
            team             = meta["team"],
            projected_points = proj.get("projected_points", 0.0),
            ecr_rank         = ecr.get("ecr_rank", 9999),
            adp              = ecr.get("adp", 9999.0),
            tier             = ecr.get("tier", 10),
            bye_week         = meta.get("bye", 0),
            injury_status    = meta.get("injury_status", ""),
        )
        players.append(p)

    # Also add projection-only players not in Sleeper
    for name_lower, pdata in proj_lookup.items():
        if name_lower not in seen_names:
            ecr = ecr_data.get(pdata["name"], {})
            p = Player(
                player_id        = f"fp_{name_lower.replace(' ', '_')}",
                name             = pdata["name"],
                position         = pdata["position"],
                team             = pdata.get("team", "?"),
                projected_points = pdata.get("projected_points", 0.0),
                ecr_rank         = ecr.get("ecr_rank", 9999),
                adp              = ecr.get("adp", 9999.0),
                tier             = ecr.get("tier", 10),
            )
            players.append(p)
            seen_names.add(name_lower)

    # Filter out players with no projections AND no ECR rank (pure noise)
    players = [p for p in players if p.projected_points > 0 or p.ecr_rank < 500]

    # --- Fallback: use built-in seed data when external APIs returned nothing ---
    if not players:
        from seed_players import get_seed_players
        players = get_seed_players()
        print(f"[player_data] Using seed data fallback: {len(players)} players")
    else:
        print(f"[player_data] Total players loaded from APIs: {len(players)}")

    # Sort by ECR rank for initial ordering
    players.sort(key=lambda p: p.ecr_rank)

    _PLAYER_CACHE = players
    return players


def invalidate_cache() -> None:
    global _PLAYER_CACHE
    _PLAYER_CACHE = None
