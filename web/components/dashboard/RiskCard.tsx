"use client";

import React from "react";

interface RiskCardProps {
  level?: string;
  score?: number;
  hazardScore?: number;
  exposureScore?: number;
  vulnerabilityScore?: number;
  actionPriority?: string;
  loading?: boolean;
}

export const RiskCard: React.FC<RiskCardProps> = ({
  level = "LOW",
  score = 0.22,
  hazardScore = 0.15,
  exposureScore = 0.30,
  vulnerabilityScore = 0.25,
  actionPriority = "Routine Monitoring",
  loading = false,
}) => {
  const getBadgeClass = (lvl: string) => {
    switch (lvl.toUpperCase()) {
      case "CRITICAL":
        return "vayu-badge-severity-critical";
      case "HIGH":
        return "vayu-badge-severity-high";
      case "MODERATE":
        return "vayu-badge-severity-moderate";
      case "LOW":
      default:
        return "vayu-badge-severity-low";
    }
  };

  if (loading) {
    return (
      <div className="vayu-card" style={{ height: "100%" }}>
        <div className="vayu-card-header">
          <span className="vayu-card-title">RISK SYNTHESIS</span>
        </div>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
          Synthesizing composite risk matrix...
        </div>
      </div>
    );
  }

  return (
    <div className="vayu-card" style={{ height: "100%" }}>
      <div className="vayu-card-header">
        <span className="vayu-card-title">COMPOSITE RISK</span>
        <span className={`vayu-badge ${getBadgeClass(level)}`}>
          {level} RISK
        </span>
      </div>

      <div style={{ margin: "0.5rem 0" }}>
        <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          {(score * 10).toFixed(1)}{" "}
          <span style={{ fontSize: "0.9rem", color: "var(--vayu-muted)", fontWeight: 500 }}>
            / 10.0
          </span>
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--vayu-muted)", marginTop: "2px" }}>
          Action Priority: <strong style={{ color: "var(--vayu-primary)" }}>{actionPriority}</strong>
        </div>
      </div>

      {/* Component decomposition */}
      <div
        style={{
          borderTop: "1px solid var(--vayu-border)",
          paddingTop: "0.75rem",
          marginTop: "0.75rem",
          fontSize: "0.725rem",
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "6px",
          textAlign: "center",
        }}
      >
        <div style={{ backgroundColor: "var(--vayu-surface-variant)", padding: "4px", borderRadius: "6px" }}>
          <div style={{ color: "var(--vayu-muted)" }}>Hazard (50%)</div>
          <strong>{(hazardScore * 10).toFixed(1)}</strong>
        </div>
        <div style={{ backgroundColor: "var(--vayu-surface-variant)", padding: "4px", borderRadius: "6px" }}>
          <div style={{ color: "var(--vayu-muted)" }}>Exposure (30%)</div>
          <strong>{(exposureScore * 10).toFixed(1)}</strong>
        </div>
        <div style={{ backgroundColor: "var(--vayu-surface-variant)", padding: "4px", borderRadius: "6px" }}>
          <div style={{ color: "var(--vayu-muted)" }}>Vuln (20%)</div>
          <strong>{(vulnerabilityScore * 10).toFixed(1)}</strong>
        </div>
      </div>
    </div>
  );
};
