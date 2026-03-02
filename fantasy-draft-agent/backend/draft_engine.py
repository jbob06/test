"""
Fantasy Draft Engine — Core VBD + Strategy Logic

Implements:
  - Value Based Drafting (VBD / VORP)
  - Positional scarcity scoring
  - ADP value detection
  - Tier-based drafting
  - Roster construction awareness
  - Round-by-round strategy adjustment
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ScoringSettings:
    pass_td: float = 4.0
    pass_yd: float = 0.04
    pass_int: float = -2.0
    rush_td: float = 6.0
    rush_yd: float = 0.1
    rec_td: float = 6.0
    rec_yd: float = 0.1
    reception: float = 0.5       # 0 = standard, 0.5 = half-PPR, 1.0 = PPR
    fumble_lost: float = -2.0
    two_pt: float = 2.0


@dataclass
class RosterSettings:
    QB: int = 1
    RB: int = 2
    WR: int = 2
    TE: int = 1
    FLEX: int = 1          # RB/WR/TE flex
    K: int = 1
    DEF: int = 1
    bench: int = 6
    num_teams: int = 12


@dataclass
class Player:
    player_id: str
    name: str
    position: str              # QB / RB / WR / TE / K / DEF
    team: str
    projected_points: float = 0.0
    ecr_rank: int = 9999       # Expert Consensus Rank (overall)
    adp: float = 9999.0        # Average Draft Position
    tier: int = 10
    bye_week: int = 0
    injury_status: str = ""    # "", "Q", "D", "O", "IR"
    notes: str = ""

    # Computed during engine init
    vbd_score: float = 0.0
    adp_value: float = 0.0     # ECR rank minus ADP  (positive = value)
    positional_rank: int = 9999
    is_available: bool = True


@dataclass
class Pick:
    pick_number: int
    round: int
    team_id: str
    player: Player
    reasoning: str = ""


@dataclass
class DraftState:
    picks: List[Pick] = field(default_factory=list)
    available_players: List[Player] = field(default_factory=list)
    my_roster: List[Player] = field(default_factory=list)
    my_team_id: str = ""
    draft_position: int = 0    # 1-based snake position
    num_teams: int = 12
    current_pick_number: int = 1
    current_round: int = 1
    is_my_pick: bool = False
    roster_settings: RosterSettings = field(default_factory=RosterSettings)
    scoring_settings: ScoringSettings = field(default_factory=ScoringSettings)


# ---------------------------------------------------------------------------
# Replacement level calculation
# ---------------------------------------------------------------------------

FLEX_POSITIONS = {"RB", "WR", "TE"}

def _compute_replacement_levels(
    players: List[Player],
    settings: RosterSettings,
) -> Dict[str, float]:
    """
    Replacement level = projected points of the player who would be the first
    "free agent" at each position after the draft is complete.

    For a 12-team league: replacement RB ≈ the 37th-ish RB
    (2 starters × 12 teams + flex contribution + small waiver buffer).
    """
    by_pos: Dict[str, List[float]] = {}
    for p in players:
        by_pos.setdefault(p.position, []).append(p.projected_points)
    for pos in by_pos:
        by_pos[pos].sort(reverse=True)

    n = settings.num_teams

    # Starters drafted per position
    starters: Dict[str, int] = {
        "QB":  settings.QB  * n,
        "RB":  settings.RB  * n + int(settings.FLEX * n * 0.4),  # ~40% of flex = RB
        "WR":  settings.WR  * n + int(settings.FLEX * n * 0.5),  # ~50% flex = WR
        "TE":  settings.TE  * n + int(settings.FLEX * n * 0.1),  # ~10% flex = TE
        "K":   settings.K   * n,
        "DEF": settings.DEF * n,
    }

    levels: Dict[str, float] = {}
    for pos, threshold in starters.items():
        pts_list = by_pos.get(pos, [])
        # Replacement = first undraftable player (index = threshold)
        # Add +1 buffer for typical waiver availability
        idx = min(threshold, len(pts_list) - 1)
        levels[pos] = pts_list[idx] if pts_list else 0.0

    return levels


# ---------------------------------------------------------------------------
# VBD calculation
# ---------------------------------------------------------------------------

def compute_vbd(players: List[Player], settings: RosterSettings) -> List[Player]:
    """Assign .vbd_score to every player in-place; return sorted list."""
    levels = _compute_replacement_levels(players, settings)

    by_pos: Dict[str, List[Player]] = {}
    for p in players:
        by_pos.setdefault(p.position, []).append(p)
    for pos in by_pos:
        by_pos[pos].sort(key=lambda x: x.projected_points, reverse=True)
        for rank, pl in enumerate(by_pos[pos], 1):
            pl.positional_rank = rank

    for p in players:
        repl = levels.get(p.position, 0.0)
        p.vbd_score = max(0.0, p.projected_points - repl)
        p.adp_value = p.adp - p.ecr_rank  # positive = going later than experts expect

    players.sort(key=lambda x: x.vbd_score, reverse=True)
    return players


# ---------------------------------------------------------------------------
# Positional scarcity scorer
# ---------------------------------------------------------------------------

def positional_scarcity_factor(
    position: str,
    available: List[Player],
    round_num: int,
) -> float:
    """
    Returns a scarcity multiplier (1.0 = neutral, >1 = scarce, <1 = plentiful).
    Measures how quickly value drops off at this position among available players.
    """
    pos_players = [p for p in available if p.position == position]
    if len(pos_players) < 2:
        return 2.0  # Extremely scarce

    # Dropoff = difference between top player and Nth player
    pos_players.sort(key=lambda x: x.vbd_score, reverse=True)
    top_vbd = pos_players[0].vbd_score
    # Compare top vs player at the ~1-team-worth index
    compare_idx = min(len(pos_players) - 1, max(1, round_num - 1))
    mid_vbd = pos_players[compare_idx].vbd_score

    if top_vbd == 0:
        return 1.0

    dropoff_pct = (top_vbd - mid_vbd) / top_vbd
    return 1.0 + dropoff_pct  # steeper dropoff → higher scarcity factor


# ---------------------------------------------------------------------------
# Roster needs analysis
# ---------------------------------------------------------------------------

def analyze_roster_needs(
    roster: List[Player],
    settings: RosterSettings,
    round_num: int,
) -> Dict[str, int]:
    """
    Returns how many more of each position are needed to fill the roster.
    Negative = over-filled. Positive = still needed.
    """
    counts: Dict[str, int] = {}
    for p in roster:
        counts[p.position] = counts.get(p.position, 0) + 1

    targets = {
        "QB":  settings.QB  + 1,          # 1 starter + 1 backup
        "RB":  settings.RB  + settings.FLEX + 2,  # starters + flex share + bench
        "WR":  settings.WR  + settings.FLEX + 2,
        "TE":  settings.TE  + 1,
        "K":   settings.K,
        "DEF": settings.DEF,
    }

    needs: Dict[str, int] = {}
    for pos, target in targets.items():
        have = counts.get(pos, 0)
        needs[pos] = target - have

    return needs


# ---------------------------------------------------------------------------
# Main pick decision
# ---------------------------------------------------------------------------

ROUND_STRATEGY_PHASES = {
    "early":  range(1, 4),    # rounds 1-3: pure VBD
    "middle": range(4, 9),    # rounds 4-8: VBD + roster awareness
    "late":   range(9, 25),   # rounds 9+:  handcuffs, upside, streaming
}


def pick_player(state: DraftState) -> tuple[Player, str]:
    """
    Select the best available player for the current pick.

    Returns (player, reasoning_string).
    """
    available = [p for p in state.available_players if p.is_available]
    roster = state.my_roster
    rnd = state.current_round
    settings = state.roster_settings

    if not available:
        raise ValueError("No available players to pick from.")

    needs = analyze_roster_needs(roster, settings, rnd)
    reasoning_parts: List[str] = []

    # Score each available player
    scored: List[tuple[float, Player, List[str]]] = []

    for player in available:
        score = player.vbd_score
        reasons: List[str] = [
            f"VBD={player.vbd_score:.1f}",
            f"Proj={player.projected_points:.1f}pts",
        ]

        # --- Phase adjustment ---
        if rnd <= 3:
            # Pure VBD: no adjustment
            pass

        elif rnd <= 8:
            # Boost players we need, penalize positions we're loaded at
            pos_need = needs.get(player.position, 0)
            if pos_need > 0:
                need_boost = min(pos_need * 3.0, 12.0)
                score += need_boost
                reasons.append(f"+{need_boost:.1f} need")
            elif pos_need <= 0:
                redundancy_penalty = abs(pos_need) * 2.0
                score -= redundancy_penalty
                reasons.append(f"-{redundancy_penalty:.1f} excess")

            # Scarcity factor
            scarcity = positional_scarcity_factor(player.position, available, rnd)
            if scarcity > 1.3:
                boost = (scarcity - 1.0) * player.vbd_score * 0.2
                score += boost
                reasons.append(f"+{boost:.1f} scarcity({scarcity:.2f}x)")

        else:
            # Late rounds: value handcuffs, high upside, streaming options
            # Penalise K/DEF until truly necessary
            if player.position in ("K", "DEF"):
                if needs.get(player.position, 0) <= 0:
                    score -= 50
                    reasons.append("-50 K/DEF not needed yet")

            # ADP value: picking a player later than expected = value
            if player.adp_value > 10:
                adp_boost = min(player.adp_value * 0.3, 8.0)
                score += adp_boost
                reasons.append(f"+{adp_boost:.1f} ADP value")

        # Injury penalty
        if player.injury_status == "D":
            score -= 15
            reasons.append("-15 doubtful")
        elif player.injury_status == "O":
            score -= 30
            reasons.append("-30 out")
        elif player.injury_status == "IR":
            score -= 100
            reasons.append("-100 IR")

        # Tier bonus: reward top-tier players within their position
        if player.tier == 1:
            tier_boost = 8.0
            score += tier_boost
            reasons.append(f"+{tier_boost:.1f} tier-1")
        elif player.tier == 2:
            score += 4.0
            reasons.append("+4.0 tier-2")

        scored.append((score, player, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_player, best_reasons = scored[0]

    # Build human-readable reasoning
    reasoning = (
        f"Round {rnd}: Selected {best_player.name} ({best_player.position}, "
        f"{best_player.team}). "
        f"Score: {best_score:.1f}. "
        f"Factors: {', '.join(best_reasons)}. "
        f"ECR #{best_player.ecr_rank}, ADP {best_player.adp:.1f}, "
        f"Positional rank #{best_player.positional_rank}."
    )

    # Show top 3 alternatives
    alts = []
    for s, p, _ in scored[1:4]:
        alts.append(f"{p.name} ({p.position}, score={s:.1f})")
    if alts:
        reasoning += f" Considered: {'; '.join(alts)}."

    return best_player, reasoning


# ---------------------------------------------------------------------------
# Roster fill check
# ---------------------------------------------------------------------------

def roster_is_complete(roster: List[Player], settings: RosterSettings) -> bool:
    total_slots = (
        settings.QB + settings.RB + settings.WR + settings.TE
        + settings.FLEX + settings.K + settings.DEF + settings.bench
    )
    return len(roster) >= total_slots


# ---------------------------------------------------------------------------
# Strategy summary (for display in UI)
# ---------------------------------------------------------------------------

def draft_strategy_summary(state: DraftState) -> str:
    rnd = state.current_round
    if rnd <= 3:
        phase = "Early Rounds — Pure VBD: take the highest value player available regardless of position."
    elif rnd <= 8:
        phase = "Middle Rounds — VBD + Roster Construction: balance value with positional needs and scarcity."
    else:
        phase = "Late Rounds — Handcuffs, Upside & Streaming: target backup RBs behind stars, high-ceiling WRs, streaming QBs/DSTs."

    needs = analyze_roster_needs(state.my_roster, state.roster_settings, rnd)
    top_needs = [pos for pos, n in sorted(needs.items(), key=lambda x: -x[1]) if n > 0]

    return f"{phase} Current needs: {', '.join(top_needs) if top_needs else 'Roster balanced — grabbing best value.'}."
