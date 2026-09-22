"use client";

import React, { useState } from "react";
import { NirnayCard as NirnayCardType, DecisionVerdict, DecisionSeverity } from "@/types/api";

interface NirnayCardProps {
  card: NirnayCardType | null;
  loading?: boolean;
}

export const NirnayCard: React.FC<NirnayCardProps> = ({ card, loading }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  if (loading) {
    return (
      <div className="vayu-card" style={{ padding: "2rem", textAlign: "center" }}>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.875rem" }}>
          Evaluating deterministic operational decision (Nirnay)...
        </div>
      </div>
    );
  }

  if (!card) {
    return (
      <div className="vayu-card" style={{ padding: "1.5rem", textAlign: "center" }}>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.85rem" }}>
          No active Nirnay decision recorded for current district.
        </div>
      </div>
    );
  }

  const getVerdictStyle = (verdict: DecisionVerdict) => {
    switch (verdict) {
      case "GO":
        return {
          bg: "#DCFCE7",
          border: "#BBF7D0",
          color: "#16A34A",
          label: "GO",
        };
      case "PROCEED_WITH_CAUTION":
        return {
          bg: "#FEF9C3",
          border: "#FDE68A",
          color: "#854D0E",
          label: "PROCEED WITH CAUTION",
        };
      case "POSTPONE":
        return {
          bg: "#FFEDD5",
          border: "#FED7AA",
          color: "#EA580C",
          label: "POSTPONE",
        };
      case "NO_GO":
        return {
          bg: "#FEE2E2",
          border: "#FECACA",
          color: "#DC2626",
          label: "NO GO",
        };
      case "MONITOR":
      default:
        return {
          bg: "#F1F5F9",
          border: "#E2E8F0",
          color: "#475569",
          label: "MONITOR",
        };
    }
  };

  const getSeverityStyle = (severity: DecisionSeverity) => {
    switch (severity) {
      case "LOW":
        return { color: "#16A34A", bg: "rgba(22, 163, 74, 0.12)" };
      case "MODERATE":
        return { color: "#CA8A04", bg: "rgba(202, 138, 4, 0.12)" };
      case "HIGH":
        return { color: "#EA580C", bg: "rgba(234, 88, 12, 0.12)" };
      case "CRITICAL":
        return { color: "#DC2626", bg: "rgba(220, 38, 38, 0.12)" };
      default:
        return { color: "#16A34A", bg: "rgba(22, 163, 74, 0.12)" };
    }
  };

  const getSourceBadgeStyle = (status: string) => {
    const s = status.toUpperCase();
    if (s === "LIVE") {
      return { bg: "#DCFCE7", color: "#15803D" };
    }
    if (s === "CACHED") {
      return { bg: "#E0F2FE", color: "#0369A1" };
    }
    if (s === "FALLBACK") {
      return { bg: "#FEF3C7", color: "#B45309" };
    }
    return { bg: "#F1F5F9", color: "#475569" };
  };

  const verdictStyle = getVerdictStyle(card.verdict);
  const severityStyle = getSeverityStyle(card.severity);
  const sourceStyle = getSourceBadgeStyle(card.sourceStatus || "LIVE");

  return (
    <div className="vayu-card" style={{ border: "1px solid var(--vayu-border)" }}>
      {/* 1. Header: Domain Badge + Severity Pill + Source Status Badge */}
      <div className="vayu-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              width: "24px",
              height: "24px",
              borderRadius: "50%",
              backgroundColor: "var(--vayu-primary-container)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "12px",
            }}
          >
            ⚡
          </div>
          <span className="vayu-card-title">NIRNAY DECISION</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {/* Source Status Badge */}
          <span
            style={{
              backgroundColor: sourceStyle.bg,
              color: sourceStyle.color,
              padding: "2px 6px",
              borderRadius: "6px",
              fontSize: "0.685rem",
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            {card.sourceStatus || "LIVE"}
          </span>

          {/* Severity Pill */}
          <span
            style={{
              backgroundColor: severityStyle.bg,
              color: severityStyle.color,
              padding: "3px 8px",
              borderRadius: "8px",
              fontSize: "0.725rem",
              fontWeight: 700,
            }}
          >
            {card.severity} RISK
          </span>
        </div>
      </div>

      {/* 2. Verdict Banner */}
      <div
        style={{
          backgroundColor: verdictStyle.bg,
          border: `1px solid ${verdictStyle.border}`,
          borderRadius: "12px",
          padding: "1rem",
          margin: "0.5rem 0 1rem 0",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
          <span
            style={{
              backgroundColor: verdictStyle.color,
              color: "#FFFFFF",
              padding: "2px 8px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 800,
              letterSpacing: "0.05em",
            }}
          >
            {verdictStyle.label}
          </span>
          <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--vayu-text)" }}>
            {card.headline}
          </span>
        </div>
        <p style={{ fontSize: "0.85rem", color: "var(--vayu-muted)", lineHeight: 1.4, marginTop: "6px" }}>
          {card.recommended_action}
        </p>
      </div>

      {/* 3. Action Window (if available) */}
      {card.action_window && card.action_window.best_window && (
        <div
          style={{
            backgroundColor: "var(--vayu-surface-variant)",
            borderRadius: "8px",
            padding: "10px 14px",
            marginBottom: "1rem",
            fontSize: "0.785rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
            <span style={{ fontWeight: 600, color: "var(--vayu-primary)" }}>
              Recommended Operational Window
            </span>
            <span style={{ color: "var(--vayu-muted)" }}>
              Duration: {card.action_window.best_window.duration_hours} hrs
            </span>
          </div>
          <div style={{ display: "flex", gap: "16px", color: "var(--vayu-muted)", marginTop: "4px" }}>
            <span>Wind: {card.action_window.best_window.avg_wind_kmh.toFixed(1)} km/h</span>
            <span>Rain Prob: {card.action_window.best_window.avg_rain_prob_pct.toFixed(0)}%</span>
            <span>Score: {(card.action_window.best_window.overall_score * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* 4. Verification Ledger Toggle */}
      {card.ledger && card.ledger.rules_evaluated && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              width: "100%",
              padding: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.775rem",
              fontWeight: 600,
              color: "var(--vayu-primary)",
              borderTop: "1px solid var(--vayu-border)",
              marginTop: "0.5rem",
            }}
          >
            <span>
              {isExpanded ? "Hide Verification Ledger ▲" : "Inspect Verification Ledger (" + card.ledger.rules_evaluated.length + " rules) ▼"}
            </span>
            <span style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
              ID: {card.ledger.decision_id.slice(0, 16)}...
            </span>
          </button>

          {isExpanded && (
            <div style={{ marginTop: "8px", fontSize: "0.75rem" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {card.ledger.rules_evaluated.map((rule, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "6px 10px",
                      backgroundColor: "var(--vayu-surface-variant)",
                      borderRadius: "6px",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, color: "var(--vayu-text)" }}>
                        {rule.description}
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
                        Threshold: {rule.threshold} • Observed: {rule.observed_value}
                      </div>
                    </div>
                    <span
                      style={{
                        color: rule.status === "PASSED" ? "var(--vayu-severity-green)" : "var(--vayu-severity-red)",
                        fontWeight: 700,
                      }}
                    >
                      {rule.status === "PASSED" ? "✓ PASS" : "✕ FAIL"}
                    </span>
                  </div>
                ))}
              </div>

              {card.ledger.signature && (
                <div style={{ marginTop: "8px", fontSize: "0.685rem", color: "var(--vayu-muted)" }}>
                  Cryptographic Signature: {card.ledger.signature.slice(0, 32)}...
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
