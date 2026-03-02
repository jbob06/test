import React, { useCallback, useEffect, useRef, useState } from "react";
import SetupForm from "./components/SetupForm";
import AgentPanel from "./components/AgentPanel";
import PlayerList from "./components/PlayerList";
import TeamRoster from "./components/TeamRoster";
import DraftBoard from "./components/DraftBoard";
import type { DraftState, LogEntry, Player, SessionConfig, WsMessage } from "./types";

// ---------------------------------------------------------------------------
// Main App
// ---------------------------------------------------------------------------

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(
    window.location.hash ? window.location.hash.slice(1) : null
  );

  const handleStart = useCallback((config: SessionConfig) => {
    // session_id is set via window.location.hash in SetupForm
    const hash = window.location.hash.slice(1);
    if (hash) setSessionId(hash);
  }, []);

  useEffect(() => {
    const onHash = () => {
      const h = window.location.hash.slice(1);
      if (h) setSessionId(h);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (!sessionId) {
    return (
      <div style={{ minHeight: "100vh", background: "#020817", color: "#e2e8f0" }}>
        <SetupForm onStart={handleStart} />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#020817", color: "#e2e8f0" }}>
      <DraftView sessionId={sessionId} onReset={() => { setSessionId(null); window.location.hash = ""; }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Draft View — connected to WebSocket
// ---------------------------------------------------------------------------

type Tab = "board" | "players" | "roster" | "log";

function DraftView({ sessionId, onReset }: { sessionId: string; onReset: () => void }) {
  const [state,       setState]       = useState<DraftState | null>(null);
  const [log,         setLog]         = useState<LogEntry[]>([]);
  const [thinking,    setThinking]    = useState(false);
  const [pendingPick, setPendingPick] = useState<{ player: Player; reasoning: string } | null>(null);
  const [activeTab,   setActiveTab]   = useState<Tab>("players");
  const [wsStatus,    setWsStatus]    = useState<"connecting" | "open" | "closed">("connecting");
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket connection
  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host  = window.location.host;
    const url   = `${proto}://${host}/ws/${sessionId}`;
    const ws    = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen  = () => setWsStatus("open");
    ws.onclose = () => setWsStatus("closed");

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data) as WsMessage;
        handleMessage(msg);
      } catch {
        // ignore
      }
    };

    return () => ws.close();
  }, [sessionId]);

  const handleMessage = (msg: WsMessage) => {
    switch (msg.type) {
      case "state":
        setState(msg.data);
        setThinking(false);
        break;
      case "agent_thinking":
        setThinking(true);
        addLog("info", msg.data.message);
        break;
      case "agent_picking":
        setThinking(false);
        setPendingPick({ player: msg.data.player, reasoning: msg.data.reasoning });
        break;
      case "pick_confirmed":
        setPendingPick(null);
        setThinking(false);
        addLog("pick", `Drafted: ${msg.data.player.name} (${msg.data.player.position})`);
        break;
      case "external_pick":
        addLog("info", `Pick made: ${msg.data.player_name}`);
        break;
      case "paused":
        addLog("info", "Agent paused.");
        break;
      case "resumed":
        addLog("info", "Agent resumed.");
        break;
      case "error":
        addLog("error", msg.data.message);
        break;
    }
  };

  const addLog = (level: LogEntry["level"], message: string) => {
    setLog((prev) => [{ ts: Date.now() / 1000, level, message }, ...prev].slice(0, 200));
  };

  const sendWs = (data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  const handlePause  = () => sendWs({ type: "pause" });
  const handleResume = () => sendWs({ type: "resume" });

  const handleManualPick = async (player: Player) => {
    await fetch(`/api/session/${sessionId}/pick`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ player_id: player.player_id }),
    });
  };

  const TABS: { id: Tab; label: string }[] = [
    { id: "players", label: "Available Players" },
    { id: "roster",  label: "My Roster" },
    { id: "board",   label: "Draft Board" },
    { id: "log",     label: `Log (${log.length})` },
  ];

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", padding: "12px 16px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: "#e2e8f0" }}>
          Fantasy Draft Agent
        </h1>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            background: wsStatus === "open" ? "#15803d" : wsStatus === "connecting" ? "#92400e" : "#7f1d1d",
            color: "#fff",
            borderRadius: 4,
            padding: "2px 8px",
          }}
        >
          {wsStatus === "open" ? "LIVE" : wsStatus.toUpperCase()}
        </span>
        <button
          onClick={onReset}
          style={{ marginLeft: "auto", background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#94a3b8", padding: "4px 12px", cursor: "pointer", fontSize: 12 }}
        >
          ← New Session
        </button>
      </div>

      {/* Agent panel (always visible) */}
      {state ? (
        <AgentPanel
          isMyPick     = {state.is_my_pick}
          paused       = {state.paused}
          thinking     = {thinking}
          pendingPick  = {pendingPick}
          strategy     = {state.strategy}
          currentPick  = {state.current_pick}
          currentRound = {state.current_round}
          onPause      = {handlePause}
          onResume     = {handleResume}
        />
      ) : (
        <div style={{ textAlign: "center", padding: 40, color: "#64748b" }}>
          {wsStatus === "connecting" ? "Connecting to draft…" : "Waiting for draft data…"}
        </div>
      )}

      {/* Tabs */}
      {state && (
        <div style={{ marginTop: 16 }}>
          <div style={{ display: "flex", gap: 4, borderBottom: "1px solid #1e293b", marginBottom: 12 }}>
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: "none",
                  border: "none",
                  borderBottom: activeTab === tab.id ? "2px solid #3b82f6" : "2px solid transparent",
                  color: activeTab === tab.id ? "#60a5fa" : "#64748b",
                  padding: "8px 16px",
                  fontSize: 13,
                  fontWeight: activeTab === tab.id ? 700 : 500,
                  cursor: "pointer",
                  transition: "color 0.15s",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div
            style={{
              background: "#0f172a",
              border: "1px solid #1e293b",
              borderRadius: 10,
              padding: 16,
            }}
          >
            {activeTab === "players" && (
              <PlayerList
                players        = {state.available_top50}
                onManualPick   = {handleManualPick}
                isMyPick       = {state.is_my_pick}
              />
            )}

            {activeTab === "roster" && (
              <TeamRoster roster={state.my_roster} teamId={state.my_team_id ?? ""} />
            )}

            {activeTab === "board" && (
              <DraftBoard
                picks       = {state.all_picks}
                numTeams    = {state.num_teams}
                myTeamId    = {state.my_team_id ?? ""}
                currentPick = {state.current_pick}
              />
            )}

            {activeTab === "log" && (
              <LogPanel entries={log} />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Log panel
// ---------------------------------------------------------------------------

function LogPanel({ entries }: { entries: LogEntry[] }) {
  const levelColor: Record<string, string> = {
    info:  "#60a5fa",
    warn:  "#f59e0b",
    error: "#ef4444",
    pick:  "#22c55e",
  };

  return (
    <div style={{ maxHeight: 500, overflowY: "auto", display: "flex", flexDirection: "column", gap: 2 }}>
      {entries.map((e, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            gap: 10,
            padding: "4px 8px",
            borderRadius: 4,
            background: i % 2 === 0 ? "#0f172a" : "transparent",
          }}
        >
          <span style={{ fontSize: 10, color: "#475569", whiteSpace: "nowrap", paddingTop: 1 }}>
            {new Date(e.ts * 1000).toLocaleTimeString()}
          </span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: levelColor[e.level] ?? "#94a3b8",
              whiteSpace: "nowrap",
              paddingTop: 1,
              width: 36,
            }}
          >
            {e.level.toUpperCase()}
          </span>
          <span style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5 }}>{e.message}</span>
        </div>
      ))}
      {entries.length === 0 && (
        <div style={{ textAlign: "center", color: "#475569", padding: 24 }}>
          No log entries yet.
        </div>
      )}
    </div>
  );
}
