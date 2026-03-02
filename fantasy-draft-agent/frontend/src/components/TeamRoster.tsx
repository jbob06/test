import React from "react";
import type { Player } from "../types";

const POS_COLORS: Record<string, string> = {
  QB:  "#ef4444",
  RB:  "#22c55e",
  WR:  "#3b82f6",
  TE:  "#f97316",
  K:   "#a855f7",
  DEF: "#6b7280",
};

interface Props {
  roster: Player[];
  teamId: string;
}

const POSITION_ORDER = ["QB", "RB", "WR", "TE", "K", "DEF"];

export default function TeamRoster({ roster, teamId }: Props) {
  const byPos: Record<string, Player[]> = {};
  for (const p of roster) {
    if (!byPos[p.position]) byPos[p.position] = [];
    byPos[p.position].push(p);
  }

  const totalProj = roster.reduce((sum, p) => sum + p.projected_points, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {/* Summary */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "#64748b" }}>
          {roster.length} players drafted
        </span>
        <span style={{ fontSize: 12, color: "#22c55e", fontWeight: 700 }}>
          {totalProj.toFixed(0)} proj pts total
        </span>
      </div>

      {/* Positional groups */}
      {POSITION_ORDER.map((pos) => {
        const players = byPos[pos] ?? [];
        const color   = POS_COLORS[pos] ?? "#6b7280";
        return (
          <div key={pos}>
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                color,
                letterSpacing: 1,
                marginBottom: 3,
                textTransform: "uppercase",
              }}
            >
              {pos} ({players.length})
            </div>
            {players.length === 0 ? (
              <div
                style={{
                  background: "#1e293b",
                  border: "1px dashed #334155",
                  borderRadius: 6,
                  height: 32,
                  display: "flex",
                  alignItems: "center",
                  paddingLeft: 10,
                  fontSize: 11,
                  color: "#475569",
                }}
              >
                Empty
              </div>
            ) : (
              players.map((p) => (
                <div
                  key={p.player_id}
                  style={{
                    background: color + "15",
                    border: `1px solid ${color}30`,
                    borderRadius: 6,
                    padding: "5px 10px",
                    marginBottom: 3,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>
                      {p.name}
                    </span>
                    <span style={{ fontSize: 11, color: "#64748b", marginLeft: 6 }}>
                      {p.team}
                    </span>
                    {p.injury_status && (
                      <span
                        style={{
                          marginLeft: 6,
                          fontSize: 9,
                          fontWeight: 700,
                          color: "#ef4444",
                          background: "#ef444420",
                          borderRadius: 3,
                          padding: "1px 4px",
                        }}
                      >
                        {p.injury_status}
                      </span>
                    )}
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 12, color: "#22c55e", fontWeight: 700 }}>
                      {p.projected_points.toFixed(1)}
                    </div>
                    <div style={{ fontSize: 10, color: "#64748b" }}>
                      Bye {p.bye_week}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        );
      })}

      {roster.length === 0 && (
        <div style={{ textAlign: "center", color: "#475569", padding: 24, fontSize: 13 }}>
          No picks yet. The agent will draft here.
        </div>
      )}
    </div>
  );
}
