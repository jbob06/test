import React from "react";
import type { Player } from "../types";

interface AgentPanelProps {
  isMyPick: boolean;
  paused: boolean;
  thinking: boolean;
  pendingPick: { player: Player; reasoning: string } | null;
  strategy: string;
  currentPick: number;
  currentRound: number;
  onPause: () => void;
  onResume: () => void;
}

export default function AgentPanel({
  isMyPick,
  paused,
  thinking,
  pendingPick,
  strategy,
  currentPick,
  currentRound,
  onPause,
  onResume,
}: AgentPanelProps) {
  const statusColor = paused ? "#f59e0b" : thinking ? "#60a5fa" : isMyPick ? "#22c55e" : "#64748b";
  const statusText  = paused
    ? "PAUSED"
    : thinking
    ? "ANALYSING..."
    : isMyPick
    ? "ON THE CLOCK"
    : "WAITING";

  return (
    <div
      style={{
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: 10,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}
    >
      {/* Status bar */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: statusColor,
            boxShadow: `0 0 6px ${statusColor}`,
            animation: (thinking || isMyPick) && !paused ? "pulse 1.5s infinite" : "none",
          }}
        />
        <span style={{ fontSize: 13, fontWeight: 700, color: statusColor, letterSpacing: 1 }}>
          {statusText}
        </span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "#64748b" }}>
          Round {currentRound} · Pick #{currentPick}
        </span>

        {/* Pause / Resume */}
        <button
          onClick={paused ? onResume : onPause}
          style={{
            background: paused ? "#22c55e" : "#f59e0b",
            color: "#000",
            border: "none",
            borderRadius: 6,
            padding: "4px 12px",
            fontWeight: 700,
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          {paused ? "Resume" : "Pause"}
        </button>
      </div>

      {/* Strategy summary */}
      <div
        style={{
          background: "#1e293b",
          borderRadius: 8,
          padding: "8px 12px",
          fontSize: 12,
          color: "#94a3b8",
          lineHeight: 1.5,
        }}
      >
        <span style={{ fontWeight: 700, color: "#60a5fa" }}>Strategy: </span>
        {strategy}
      </div>

      {/* Pending pick analysis */}
      {pendingPick && (
        <div
          style={{
            background: "#0d2040",
            border: "1px solid #1d4ed8",
            borderRadius: 8,
            padding: 12,
            animation: "fadeIn 0.3s ease",
          }}
        >
          <div style={{ fontSize: 11, color: "#60a5fa", fontWeight: 700, marginBottom: 6 }}>
            AGENT SELECTION
          </div>
          <div style={{ fontSize: 16, fontWeight: 800, color: "#e2e8f0", marginBottom: 4 }}>
            {pendingPick.player.name}
            <span
              style={{
                marginLeft: 8,
                fontSize: 12,
                fontWeight: 600,
                background: "#1d4ed8",
                borderRadius: 4,
                padding: "1px 6px",
                color: "#bfdbfe",
              }}
            >
              {pendingPick.player.position} · {pendingPick.player.team}
            </span>
          </div>
          <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.6 }}>
            {pendingPick.reasoning}
          </div>
          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            <StatChip label="Proj Pts" value={pendingPick.player.projected_points.toFixed(1)} />
            <StatChip label="VBD"      value={pendingPick.player.vbd_score.toFixed(1)} />
            <StatChip label="ECR"      value={`#${pendingPick.player.ecr_rank}`} />
            <StatChip label="ADP"      value={pendingPick.player.adp.toFixed(1)} />
            <StatChip label="Bye"      value={String(pendingPick.player.bye_week)} />
          </div>
        </div>
      )}
    </div>
  );
}

function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: "#1e3a5f",
        borderRadius: 6,
        padding: "3px 8px",
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 9, color: "#64748b", fontWeight: 600, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 700 }}>{value}</div>
    </div>
  );
}
