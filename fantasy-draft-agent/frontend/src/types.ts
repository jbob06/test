// ---------------------------------------------------------------------------
// Shared TypeScript types
// ---------------------------------------------------------------------------

export type Platform = "sleeper" | "espn" | "yahoo";
export type Position = "QB" | "RB" | "WR" | "TE" | "K" | "DEF" | "FLEX";

export interface Player {
  player_id: string;
  name: string;
  position: Position;
  team: string;
  projected_points: number;
  ecr_rank: number;
  adp: number;
  tier: number;
  bye_week: number;
  injury_status: string;
  vbd_score: number;
  adp_value: number;
  positional_rank: number;
  is_available: boolean;
}

export interface DraftPick {
  pick_number: number;
  round: number;
  team_id: string;
  player: Player;
  reasoning: string;
}

export interface DraftState {
  current_pick: number;
  current_round: number;
  is_my_pick: boolean;
  draft_position: number;
  num_teams: number;
  my_roster: Player[];
  all_picks: DraftPick[];
  available_top50: Player[];
  strategy: string;
  paused: boolean;
}

export interface LogEntry {
  ts: number;
  level: "info" | "warn" | "error" | "pick";
  message: string;
  data?: unknown;
}

export interface SessionConfig {
  platform: Platform;
  draft_id: string;
  user_id: string;
  auth_token?: string;
  swid?: string;
  team_id?: string;
  num_teams: number;
  ppr: number;
}

// WebSocket message types
export type WsMessage =
  | { type: "state";         data: DraftState }
  | { type: "agent_thinking"; data: { message: string } }
  | { type: "agent_picking";  data: { player: Player; reasoning: string } }
  | { type: "pick_confirmed"; data: { player: Player; reasoning: string; roster: Player[] } }
  | { type: "external_pick";  data: { player_id: string; player_name: string } }
  | { type: "paused" }
  | { type: "resumed" }
  | { type: "error";          data: { message: string } };
