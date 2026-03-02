"""
Seed player data — top ~120 NFL fantasy-relevant players with
realistic 2025-season projections (half-PPR).

Used as fallback when external APIs (FantasyPros, Sleeper) are unavailable.
VBD scores are calculated by the engine at runtime; only the raw stats
needed to derive projected_points are stored here.
"""

from draft_engine import Player

# Each tuple: (id, name, position, team, projected_pts_halfPPR, ecr_rank, adp, tier, bye)
_SEED = [
    # QBs
    ("4035004", "Lamar Jackson",       "QB", "BAL",  420.0,  1,  1.5, 1,  14),
    ("4362628", "Josh Allen",          "QB", "BUF",  415.0,  2,  2.0, 1,   7),
    ("3918298", "Jalen Hurts",         "QB", "PHI",  395.0,  3,  3.2, 1,  14),
    ("3916387", "Patrick Mahomes",     "QB", "KC",   380.0,  4,  4.5, 1,  12),
    ("4040715", "C.J. Stroud",         "QB", "HOU",  350.0,  5,  6.0, 2,  14),
    ("3139477", "Dak Prescott",        "QB", "DAL",  330.0,  6,  8.5, 2,   7),
    ("3054211", "Jordan Love",         "QB", "GB",   325.0,  7,  9.0, 2,  12),
    ("4361741", "Sam LaPorta",         "QB", "DEN",  310.0,  8, 11.0, 2,  14),
    ("3912547", "Kirk Cousins",        "QB", "ATL",  295.0,  9, 14.0, 3,  12),
    ("3054220", "Tua Tagovailoa",      "QB", "MIA",  285.0, 10, 16.0, 3,  10),
    ("4259545", "Brock Purdy",         "QB", "SF",   335.0, 11, 12.0, 2,  12),
    ("4430028", "Jayden Daniels",      "QB", "WAS",  340.0, 12, 10.0, 2,   6),

    # RBs
    ("4046462", "Christian McCaffrey", "RB", "SF",   340.0,  1,  1.2, 1,  12),
    ("4362066", "Breece Hall",         "RB", "NYJ",  295.0,  2,  3.8, 1,   7),
    ("4429013", "Bijan Robinson",      "RB", "ATL",  290.0,  3,  4.2, 1,  12),
    ("3054220", "De'Von Achane",       "RB", "MIA",  280.0,  4,  5.5, 1,  10),
    ("4034148", "Jahmyr Gibbs",        "RB", "DET",  275.0,  5,  6.3, 1,  14),
    ("4369927", "Jonathan Taylor",     "RB", "IND",  265.0,  6,  7.0, 1,  14),
    ("4036133", "Kyren Williams",      "RB", "LAR",  255.0,  7,  8.5, 1,  11),
    ("4034149", "David Montgomery",    "RB", "DET",  220.0,  8, 12.0, 2,  14),
    ("4040571", "Saquon Barkley",      "RB", "PHI",  245.0,  9, 10.0, 1,  14),
    ("4362887", "Josh Jacobs",         "RB", "GB",   230.0, 10, 13.5, 2,  12),
    ("4035538", "Tony Pollard",        "RB", "TEN",  210.0, 11, 17.0, 2,   6),
    ("4361396", "Rachaad White",       "RB", "TB",   205.0, 12, 19.0, 2,  11),
    ("4039364", "Aaron Jones",         "RB", "MIN",  200.0, 13, 21.0, 2,  12),
    ("4039356", "Brian Robinson Jr.",  "RB", "WAS",  195.0, 14, 22.0, 2,   6),
    ("4047646", "Zack Moss",           "RB", "IND",  190.0, 15, 25.0, 2,  14),
    ("4035004", "Austin Ekeler",       "RB", "WAS",  175.0, 16, 30.0, 3,   6),
    ("3054218", "James Conner",        "RB", "ARI",  185.0, 17, 27.0, 3,  11),
    ("4040023", "Derrick Henry",       "RB", "BAL",  215.0, 18, 16.0, 2,  14),
    ("4035538", "Rhamondre Stevenson", "RB", "NE",   175.0, 19, 31.0, 3,  14),
    ("4361741", "Joe Mixon",           "RB", "HOU",  200.0, 20, 20.0, 2,  14),
    ("4039364", "Najee Harris",        "RB", "PIT",  185.0, 21, 26.0, 3,  14),
    ("4046519", "Isiah Pacheco",       "RB", "KC",   180.0, 22, 28.0, 3,  12),
    ("4035660", "Miles Sanders",       "RB", "CAR",  160.0, 23, 38.0, 3,  11),
    ("4040725", "Travis Etienne",      "RB", "JAX",  190.0, 24, 24.0, 3,   7),
    ("4039361", "Alvin Kamara",        "RB", "NO",   195.0, 25, 23.0, 3,  14),

    # WRs
    ("4362628", "Ja'Marr Chase",       "WR", "CIN",  310.0,  1,  2.5, 1,  12),
    ("4040715", "CeeDee Lamb",         "WR", "DAL",  305.0,  2,  3.0, 1,   7),
    ("4034748", "Tyreek Hill",         "WR", "MIA",  285.0,  3,  5.0, 1,  10),
    ("4259545", "Amon-Ra St. Brown",   "WR", "DET",  275.0,  4,  6.5, 1,  14),
    ("4035007", "Justin Jefferson",    "WR", "MIN",  270.0,  5,  7.0, 1,  12),
    ("3054228", "Davante Adams",       "WR", "NYJ",  245.0,  6, 10.0, 2,   7),
    ("4041093", "Stefon Diggs",        "WR", "HOU",  230.0,  7, 13.0, 2,  14),
    ("3916387", "Drake London",        "WR", "ATL",  235.0,  8, 11.5, 2,  12),
    ("4035538", "DeVonta Smith",       "WR", "PHI",  225.0,  9, 14.5, 2,  14),
    ("4040571", "Puka Nacua",          "WR", "LAR",  220.0, 10, 16.0, 2,  11),
    ("4034148", "Chris Olave",         "WR", "NO",   215.0, 11, 17.5, 2,  14),
    ("4362887", "Jaylen Waddle",       "WR", "MIA",  210.0, 12, 19.0, 2,  10),
    ("4046462", "Garrett Wilson",      "WR", "NYJ",  230.0, 13, 12.5, 2,   7),
    ("3054219", "DK Metcalf",          "WR", "SEA",  220.0, 14, 15.5, 2,  10),
    ("4035660", "A.J. Brown",          "WR", "PHI",  225.0, 15, 14.0, 2,  14),
    ("4046519", "Keenan Allen",        "WR", "CHI",  200.0, 16, 22.0, 3,   7),
    ("4039364", "Tee Higgins",         "WR", "CIN",  205.0, 17, 21.0, 2,  12),
    ("4362066", "Calvin Ridley",       "WR", "TEN",  195.0, 18, 25.0, 3,   6),
    ("4035007", "Michael Pittman Jr.", "WR", "IND",  200.0, 19, 23.0, 3,  14),
    ("4040023", "Zay Flowers",         "WR", "BAL",  190.0, 20, 27.0, 3,  14),
    ("3912547", "Rashee Rice",         "WR", "KC",   185.0, 21, 30.0, 3,  12),
    ("4430028", "Jordan Addison",      "WR", "MIN",  185.0, 22, 31.0, 3,  12),
    ("4034149", "Christian Kirk",      "WR", "JAX",  180.0, 23, 34.0, 3,   7),
    ("3054211", "Courtland Sutton",    "WR", "DEN",  178.0, 24, 36.0, 3,  14),
    ("4047646", "Josh Reynolds",       "WR", "DET",  170.0, 25, 40.0, 3,  14),
    ("4429013", "Quentin Johnston",    "WR", "LAC",  165.0, 26, 44.0, 4,  11),
    ("4036133", "Jerry Jeudy",         "WR", "CLE",  162.0, 27, 46.0, 4,  14),
    ("4361396", "Diontae Johnson",     "WR", "CAR",  160.0, 28, 48.0, 4,  11),
    ("4369927", "Brandin Cooks",       "WR", "DAL",  155.0, 29, 52.0, 4,   7),
    ("4035538", "Odell Beckham Jr.",   "WR", "MIA",  150.0, 30, 57.0, 4,  10),

    # TEs
    ("4361741", "Sam LaPorta",         "TE", "DET",  195.0,  1,  8.0, 1,  14),
    ("3054220", "Travis Kelce",        "TE", "KC",   210.0,  2,  6.5, 1,  12),
    ("4035007", "Mark Andrews",        "TE", "BAL",  185.0,  3, 10.0, 1,  14),
    ("4040715", "Trey McBride",        "TE", "ARI",  180.0,  4, 12.5, 1,  11),
    ("3912547", "Evan Engram",         "TE", "JAX",  165.0,  5, 18.0, 2,   7),
    ("4034148", "Dallas Goedert",      "TE", "PHI",  155.0,  6, 22.0, 2,  14),
    ("4259545", "T.J. Hockenson",      "TE", "MIN",  150.0,  7, 26.0, 2,  12),
    ("4429013", "Tucker Kraft",         "TE", "GB",   140.0,  8, 33.0, 3,  12),
    ("4046462", "Pat Freiermuth",      "TE", "PIT",  135.0,  9, 38.0, 3,  14),
    ("4039364", "Kyle Pitts",          "TE", "ATL",  145.0, 10, 30.0, 3,  12),
    ("4362628", "Cole Kmet",           "TE", "CHI",  130.0, 11, 42.0, 3,   7),
    ("4035538", "Jake Ferguson",       "TE", "DAL",  128.0, 12, 45.0, 3,   7),
    ("3916387", "David Njoku",         "TE", "CLE",  125.0, 13, 48.0, 4,  14),
    ("4040571", "Dalton Schultz",      "TE", "HOU",  120.0, 14, 52.0, 4,  14),
    ("4036133", "Chig Okonkwo",        "TE", "TEN",  115.0, 15, 58.0, 4,   6),

    # Ks (projected FG points for season)
    ("4035004", "Justin Tucker",       "K",  "BAL",  165.0,  1, 110.0, 1,  14),
    ("4046519", "Evan McPherson",      "K",  "CIN",  160.0,  2, 115.0, 1,  12),
    ("4034748", "Harrison Butker",     "K",  "KC",   158.0,  3, 118.0, 1,  12),
    ("4040023", "Tyler Bass",          "K",  "BUF",  155.0,  4, 122.0, 2,   7),
    ("3054228", "Brandon Aubrey",      "K",  "DAL",  152.0,  5, 125.0, 2,   7),
    ("4047646", "Jake Moody",          "K",  "SF",   150.0,  6, 128.0, 2,  12),
    ("4039356", "Cameron Dicker",      "K",  "LAC",  148.0,  7, 131.0, 2,  11),
    ("4035660", "Chase McLaughlin",    "K",  "IND",  145.0,  8, 135.0, 2,  14),

    # DEF/ST
    ("DEF_SF",  "San Francisco 49ers", "DEF","SF",   150.0,  1, 105.0, 1,  12),
    ("DEF_DAL", "Dallas Cowboys",      "DEF","DAL",  140.0,  2, 112.0, 1,   7),
    ("DEF_BUF", "Buffalo Bills",       "DEF","BUF",  138.0,  3, 115.0, 2,   7),
    ("DEF_KC",  "Kansas City Chiefs",  "DEF","KC",   135.0,  4, 118.0, 2,  12),
    ("DEF_BAL", "Baltimore Ravens",    "DEF","BAL",  133.0,  5, 122.0, 2,  14),
    ("DEF_PHI", "Philadelphia Eagles", "DEF","PHI",  130.0,  6, 125.0, 2,  14),
    ("DEF_CLE", "Cleveland Browns",    "DEF","CLE",  125.0,  7, 130.0, 3,  14),
    ("DEF_PIT", "Pittsburgh Steelers", "DEF","PIT",  122.0,  8, 134.0, 3,  14),
    ("DEF_MIA", "Miami Dolphins",      "DEF","MIA",  118.0,  9, 140.0, 3,  10),
    ("DEF_HOU", "Houston Texans",      "DEF","HOU",  115.0, 10, 145.0, 3,  14),
    ("DEF_GB",  "Green Bay Packers",   "DEF","GB",   112.0, 11, 150.0, 3,  12),
    ("DEF_DET", "Detroit Lions",       "DEF","DET",  110.0, 12, 155.0, 4,  14),
]


def get_seed_players() -> list[Player]:
    """Return seed Player objects. Player IDs are made unique per position."""
    seen: set[str] = set()
    players: list[Player] = []
    for i, row in enumerate(_SEED):
        pid_base, name, pos, team, proj, ecr_pos, adp, tier, bye = row
        # Make IDs unique by appending index to avoid collisions across positions
        pid = f"{pos}_{i}_{pid_base}"
        if pid in seen:
            continue
        seen.add(pid)
        players.append(Player(
            player_id        = pid,
            name             = name,
            position         = pos,
            team             = team,
            projected_points = proj,
            ecr_rank         = ecr_pos + ({"QB":0,"RB":20,"WR":50,"TE":90,"K":120,"DEF":130}[pos]),
            adp              = adp,
            tier             = tier,
            bye_week         = bye,
        ))
    return players
