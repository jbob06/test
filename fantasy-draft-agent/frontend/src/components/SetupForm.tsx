import React, { useState } from "react";
import type { SessionConfig, Platform } from "../types";

interface Props {
  onStart: (config: SessionConfig) => void;
}

const PLATFORM_INFO: Record<Platform, { name: string; description: string; authHelp: string }> = {
  sleeper: {
    name: "Sleeper",
    description: "Best API support — full auto-draft with auth token",
    authHelp:
      "Get your Sleeper auth token from: Browser DevTools → Application → Local Storage → api.sleeper.app → 'sleeper_token'",
  },
  espn: {
    name: "ESPN",
    description: "Auto-draft using ESPN internal API or browser automation",
    authHelp:
      "Get ESPN cookies from: DevTools → Application → Cookies → espn.com\n• espn_s2: long cookie starting with AE...\n• SWID: formatted as {GUID}",
  },
  yahoo: {
    name: "Yahoo",
    description: "Auto-draft using Yahoo Fantasy API (OAuth2 required)",
    authHelp:
      "Complete Yahoo OAuth2 flow. Your league key format: nfl.l.{league_id}.\nYou will need to set up a Yahoo developer app — see README for instructions.",
  },
};

export default function SetupForm({ onStart }: Props) {
  const [platform,    setPlatform]    = useState<Platform>("sleeper");
  const [draftId,     setDraftId]     = useState("");
  const [userId,      setUserId]      = useState("");
  const [authToken,   setAuthToken]   = useState("");
  const [swid,        setSwid]        = useState("");
  const [numTeams,    setNumTeams]    = useState(12);
  const [ppr,         setPpr]         = useState(0.5);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");

  const info = PLATFORM_INFO[platform];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const resp = await fetch("/api/session", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          draft_id:   draftId.trim(),
          user_id:    userId.trim(),
          auth_token: authToken.trim() || undefined,
          swid:       swid.trim() || undefined,
          num_teams:  numTeams,
          ppr,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Failed to create session.");
      }
      const { session_id } = await resp.json();
      onStart({ platform, draft_id: draftId, user_id: userId, auth_token: authToken, swid, num_teams: numTeams, ppr });
      // Redirect to session view — handled by parent via onStart
      window.location.hash = session_id;
    } catch (err: any) {
      setError(err.message ?? "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 560, margin: "60px auto", padding: "0 16px" }}>
      <div style={{ textAlign: "center", marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: "#e2e8f0", margin: 0 }}>
          Fantasy Draft Agent
        </h1>
        <p style={{ color: "#64748b", marginTop: 8 }}>
          AI-powered auto-drafter using Value Based Drafting + Expert Consensus
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        style={{
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: 12,
          padding: 28,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {/* Platform selection */}
        <div>
          <label style={labelStyle}>Platform</label>
          <div style={{ display: "flex", gap: 8 }}>
            {(["sleeper", "espn", "yahoo"] as Platform[]).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPlatform(p)}
                style={{
                  flex: 1,
                  padding: "8px 4px",
                  borderRadius: 8,
                  border: platform === p ? "2px solid #3b82f6" : "1px solid #334155",
                  background: platform === p ? "#1e3a5f" : "#1e293b",
                  color: platform === p ? "#60a5fa" : "#94a3b8",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                  textTransform: "capitalize",
                }}
              >
                {PLATFORM_INFO[p].name}
              </button>
            ))}
          </div>
          <p style={{ fontSize: 11, color: "#64748b", marginTop: 4 }}>{info.description}</p>
        </div>

        {/* Draft / League ID */}
        <FormField
          label={platform === "espn" ? "League ID" : platform === "yahoo" ? "League Key (nfl.l.XXXXXX)" : "Draft ID"}
          value={draftId}
          onChange={setDraftId}
          placeholder={platform === "sleeper" ? "e.g. 12345678901234" : platform === "espn" ? "e.g. 12345678" : "e.g. nfl.l.123456"}
          required
        />

        {/* User ID */}
        <FormField
          label={platform === "yahoo" ? "Yahoo GUID" : "User ID"}
          value={userId}
          onChange={setUserId}
          placeholder={platform === "sleeper" ? "Sleeper user_id" : platform === "espn" ? "ESPN SWID without braces" : "Yahoo GUID"}
          required
        />

        {/* Auth token */}
        <FormField
          label={platform === "espn" ? "espn_s2 Cookie" : platform === "yahoo" ? "OAuth Access Token" : "Auth Token (optional for monitoring)"}
          value={authToken}
          onChange={setAuthToken}
          placeholder={platform === "sleeper" ? "From localStorage → sleeper_token" : ""}
          type="password"
        />

        {/* ESPN SWID */}
        {platform === "espn" && (
          <FormField
            label="SWID Cookie"
            value={swid}
            onChange={setSwid}
            placeholder="{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"
          />
        )}

        {/* Auth help */}
        <div
          style={{
            background: "#1e293b",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: 11,
            color: "#64748b",
            whiteSpace: "pre-wrap",
            lineHeight: 1.6,
          }}
        >
          {info.authHelp}
        </div>

        {/* League settings */}
        <div style={{ display: "flex", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Teams</label>
            <select
              value={numTeams}
              onChange={(e) => setNumTeams(Number(e.target.value))}
              style={inputStyle}
            >
              {[8, 10, 12, 14, 16].map((n) => (
                <option key={n} value={n}>{n} teams</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Scoring</label>
            <select
              value={ppr}
              onChange={(e) => setPpr(Number(e.target.value))}
              style={inputStyle}
            >
              <option value={0}>Standard</option>
              <option value={0.5}>Half PPR</option>
              <option value={1.0}>Full PPR</option>
            </select>
          </div>
        </div>

        {error && (
          <div
            style={{
              background: "#ef444420",
              border: "1px solid #ef4444",
              borderRadius: 8,
              padding: "8px 12px",
              color: "#ef4444",
              fontSize: 13,
            }}
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            background: loading ? "#1e293b" : "linear-gradient(135deg, #1d4ed8, #7c3aed)",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "12px 0",
            fontSize: 15,
            fontWeight: 700,
            cursor: loading ? "not-allowed" : "pointer",
            marginTop: 4,
          }}
        >
          {loading ? "Connecting…" : "Start Draft Agent"}
        </button>
      </form>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "#94a3b8",
  marginBottom: 4,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 6,
  padding: "7px 10px",
  color: "#e2e8f0",
  fontSize: 13,
  boxSizing: "border-box",
};

function FormField({
  label,
  value,
  onChange,
  placeholder = "",
  required = false,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: string;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        style={inputStyle}
      />
    </div>
  );
}
