import React, { useState } from "react";
import type { Player, Position } from "../types";

const POS_COLORS: Record<string, string> = {
  QB:  "#ef4444",
  RB:  "#22c55e",
  WR:  "#3b82f6",
  TE:  "#f97316",
  K:   "#a855f7",
  DEF: "#6b7280",
};

const INJURY_BADGE: Record<string, { label: string; color: string }> = {
  Q:  { label: "Q",  color: "#f59e0b" },
  D:  { label: "D",  color: "#ef4444" },
  O:  { label: "OUT",color: "#ef4444" },
  IR: { label: "IR", color: "#7f1d1d" },
};

interface Props {
  players: Player[];
  onManualPick?: (player: Player) => void;
  isMyPick: boolean;
}

const POSITIONS: (Position | "ALL")[] = ["ALL", "QB", "RB", "WR", "TE", "K", "DEF"];

export default function PlayerList({ players, onManualPick, isMyPick }: Props) {
  const [posFilter, setPosFilter] = useState<Position | "ALL">("ALL");
  const [search, setSearch]       = useState("");
  const [sortKey, setSortKey]     = useState<"vbd_score" | "ecr_rank" | "adp" | "projected_points">("vbd_score");

  const filtered = players
    .filter((p) => p.is_available)
    .filter((p) => posFilter === "ALL" || p.position === posFilter)
    .filter((p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.team.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortKey === "ecr_rank" || sortKey === "adp") return a[sortKey] - b[sortKey];
      return b[sortKey] - a[sortKey];
    })
    .slice(0, 100);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Filters */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          placeholder="Search players…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            flex: 1,
            minWidth: 140,
            background: "#1e293b",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "5px 10px",
            color: "#e2e8f0",
            fontSize: 13,
          }}
        />
        {POSITIONS.map((pos) => (
          <button
            key={pos}
            onClick={() => setPosFilter(pos)}
            style={{
              background: posFilter === pos ? (POS_COLORS[pos] ?? "#3b82f6") : "#1e293b",
              border: "1px solid " + (POS_COLORS[pos] ?? "#334155"),
              borderRadius: 6,
              padding: "4px 10px",
              color: posFilter === pos ? "#fff" : "#94a3b8",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {pos}
          </button>
        ))}
      </div>

      {/* Sort header */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "28px 1fr 52px 60px 60px 60px 60px 70px",
          gap: 4,
          padding: "4px 8px",
          color: "#64748b",
          fontSize: 11,
          fontWeight: 600,
        }}
      >
        <span>#</span>
        <span>Player</span>
        <span>Pos</span>
        <SortButton label="VBD"   current={sortKey} value="vbd_score"       onClick={setSortKey} />
        <SortButton label="Proj"  current={sortKey} value="projected_points" onClick={setSortKey} />
        <SortButton label="ECR"   current={sortKey} value="ecr_rank"        onClick={setSortKey} />
        <SortButton label="ADP"   current={sortKey} value="adp"             onClick={setSortKey} />
        <span>Action</span>
      </div>

      {/* Rows */}
      <div style={{ maxHeight: 480, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
        {filtered.map((player, idx) => {
          const color  = POS_COLORS[player.position] ?? "#6b7280";
          const injury = INJURY_BADGE[player.injury_status];

          return (
            <div
              key={player.player_id}
              style={{
                display: "grid",
                gridTemplateColumns: "28px 1fr 52px 60px 60px 60px 60px 70px",
                gap: 4,
                padding: "5px 8px",
                background: idx % 2 === 0 ? "#0f172a" : "#111827",
                borderRadius: 6,
                alignItems: "center",
                borderLeft: `3px solid ${player.tier <= 2 ? color : "transparent"}`,
              }}
            >
              <span style={{ fontSize: 11, color: "#475569" }}>{idx + 1}</span>

              {/* Name + team */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#e2e8f0" }}>
                  {player.name}
                  {injury && (
                    <span
                      style={{
                        marginLeft: 5,
                        fontSize: 9,
                        fontWeight: 700,
                        background: injury.color + "33",
                        color: injury.color,
                        borderRadius: 3,
                        padding: "1px 4px",
                      }}
                    >
                      {injury.label}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>
                  {player.team} · Bye {player.bye_week}
                </div>
              </div>

              {/* Position */}
              <span
                style={{
                  background: color + "22",
                  color,
                  borderRadius: 4,
                  padding: "2px 6px",
                  fontSize: 11,
                  fontWeight: 700,
                  textAlign: "center",
                }}
              >
                {player.position}
              </span>

              <span style={{ fontSize: 12, color: "#22c55e", fontWeight: 700, textAlign: "right" }}>
                {player.vbd_score.toFixed(1)}
              </span>
              <span style={{ fontSize: 12, color: "#e2e8f0", textAlign: "right" }}>
                {player.projected_points.toFixed(1)}
              </span>
              <span style={{ fontSize: 12, color: "#94a3b8", textAlign: "right" }}>
                {player.ecr_rank < 9999 ? `#${player.ecr_rank}` : "—"}
              </span>
              <span style={{ fontSize: 12, color: "#94a3b8", textAlign: "right" }}>
                {player.adp < 9999 ? player.adp.toFixed(1) : "—"}
              </span>

              {/* Manual pick button */}
              {isMyPick && onManualPick ? (
                <button
                  onClick={() => onManualPick(player)}
                  style={{
                    background: "#1d4ed8",
                    color: "#fff",
                    border: "none",
                    borderRadius: 5,
                    padding: "3px 8px",
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Draft
                </button>
              ) : (
                <span />
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div style={{ textAlign: "center", color: "#475569", padding: 24, fontSize: 13 }}>
            No players match your filter.
          </div>
        )}
      </div>
    </div>
  );
}

function SortButton({
  label,
  current,
  value,
  onClick,
}: {
  label: string;
  current: string;
  value: string;
  onClick: (v: any) => void;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => onClick(value)}
      style={{
        background: "none",
        border: "none",
        cursor: "pointer",
        color: active ? "#60a5fa" : "#64748b",
        fontWeight: active ? 700 : 600,
        fontSize: 11,
        padding: 0,
        textAlign: "right",
      }}
    >
      {label} {active ? "▼" : ""}
    </button>
  );
}
