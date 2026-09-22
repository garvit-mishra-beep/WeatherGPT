"use client";

import React from "react";

interface HazardCardProps {
  level?: string;
  score?: number;
  hazardType?: string;
  rainfallMm?: number;
  loading?: boolean;
}

export const HazardCard: React.FC<HazardCardProps> = ({
  level = "LOW",
  score = 0.15,
  hazardType = "Heavy Rainfall",
  rainfallMm = 0.0,
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
          <span className="vayu-card-title">HAZARD STATE</span>
        </div>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
          Evaluating meteorological hazard indicators...
        </div>
      </div>
    );
  }

  return (
    <div className="vayu-card" style={{ height: "100%" }}>
      <div className="vayu-card-header">
        <span className="vayu-card-title">HAZARD ASSESSMENT</span>
        <span className={`vayu-badge ${getBadgeClass(level)}`}>
          {level} HAZARD
        </span>
      </div>

      <div style={{ margin: "0.5rem 0" }}>
        <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--vayu-text)" }}>
          {hazardType}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--vayu-muted)", marginTop: "2px" }}>
          Composite Hazard Index: <strong>{(score * 10).toFixed(1)} / 10.0</strong>
        </div>
      </div>

      <div
        style={{
          borderTop: "1px solid var(--vayu-border)",
          paddingTop: "0.75rem",
          marginTop: "1rem",
          fontSize: "0.785rem",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span style={{ color: "var(--vayu-muted)" }}>Observed Intensity:</span>
        <strong>{rainfallMm.toFixed(1)} mm/hr</strong>
      </div>
    </div>
  );
};
