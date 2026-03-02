import React from "react";
import type { DraftPick, Player } from "../types";

const POS_COLORS: Record<string, string> = {
  QB:  "#ef4444",
  RB:  "#22c55e",
  WR:  "#3b82f6",
  TE:  "#f97316",
  K:   "#a855f7",
  DEF: "#6b7280",
};

function PickCell({ pick }: { pick: DraftPick }) {
  const color = POS_COLORS[pick.player.position] ?? "#6b7280";
  return (
    <div
      title={pick.reasoning || ""}
      style={{
        background: color + "22",
        border: `1px solid ${color}55`,
        borderRadius: 6,
        padding: "4px 6px",
        fontSize: 11,
        lineHeight: 1.3,
        minHeight: 44,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
      }}
    >
      <span style={{ fontWeight: 700, color, fontSize: 10 }}>
        {pick.player.position}
      </span>
      <span style={{ fontWeight: 600, color: "#e2e8f0", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        {pick.player.name}
      </span>
      <span style={{ color: "#94a3b8", fontSize: 10 }}>{pick.player.team}</span>
    </div>
  );
}

interface Props {
  picks: DraftPick[];
  numTeams: number;
  myTeamId: string;
  currentPick: number;
}

export default function DraftBoard({ picks, numTeams, myTeamId, currentPick }: Props) {
  const maxRounds = Math.max(16, Math.ceil((picks.length + 1) / numTeams) + 1);
  const rounds    = Array.from({ length: maxRounds }, (_, i) => i);

  // Build grid: grid[round][team_slot] = pick | null
  const grid: (DraftPick | null)[][] = rounds.map(() =>
    Array.from({ length: numTeams }, () => null)
  );

  for (const pick of picks) {
    const rIdx = pick.round - 1;
    const slot  = (pick.pick_number - 1) % numTeams;
    if (grid[rIdx]) grid[rIdx][slot] = pick;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      {/* Column headers */}
      <div style={{ display: "grid", gridTemplateColumns: `40px repeat(${numTeams}, minmax(88px, 1fr))`, gap: 2, marginBottom: 2 }}>
        <div />
        {Array.from({ length: numTeams }, (_, i) => (
          <div
            key={i}
            style={{
              textAlign: "center",
              fontSize: 11,
              fontWeight: 600,
              color: "#94a3b8",
              padding: "2px 0",
              background: i + 1 === parseInt(myTeamId) ? "#1e3a5f" : "transparent",
              borderRadius: 4,
            }}
          >
            Team {i + 1}
          </div>
        ))}
      </div>

      {/* Rounds */}
      {rounds.map((rIdx) => (
        <div
          key={rIdx}
          style={{
            display: "grid",
            gridTemplateColumns: `40px repeat(${numTeams}, minmax(88px, 1fr))`,
            gap: 2,
            marginBottom: 2,
          }}
        >
          {/* Round label */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, color: "#64748b", fontWeight: 600 }}>
            R{rIdx + 1}
          </div>

          {/* Cells */}
          {Array.from({ length: numTeams }, (_, col) => {
            const cell = grid[rIdx]?.[col];
            const pickNum = rIdx % 2 === 0
              ? rIdx * numTeams + col + 1
              : rIdx * numTeams + (numTeams - col);

            if (cell) {
              return (
                <div key={col}>
                  <PickCell pick={cell} />
                </div>
              );
            }

            const isCurrent = pickNum === currentPick;
            return (
              <div
                key={col}
                style={{
                  background: isCurrent ? "#1e3a5f" : "#1e293b",
                  border: isCurrent ? "1px solid #3b82f6" : "1px solid #334155",
                  borderRadius: 6,
                  minHeight: 44,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {isCurrent && (
                  <span style={{ fontSize: 10, color: "#60a5fa", fontWeight: 700 }}>
                    ON THE CLOCK
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
