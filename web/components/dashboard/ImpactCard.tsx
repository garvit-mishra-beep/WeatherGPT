"use client";

import React from "react";

interface ImpactCardProps {
  agricultureImpact?: string;
  infrastructureImpact?: string;
  populationImpact?: string;
  loading?: boolean;
}

export const ImpactCard: React.FC<ImpactCardProps> = ({
  agricultureImpact = "Foliage absorption within nominal tolerance",
  infrastructureImpact = "Drainage networks operating normally",
  populationImpact = "No localized displacement risks identified",
  loading = false,
}) => {
  if (loading) {
    return (
      <div className="vayu-card" style={{ height: "100%" }}>
        <div className="vayu-card-header">
          <span className="vayu-card-title">POTENTIAL IMPACT</span>
        </div>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
          Evaluating multi-sector physical and economic impacts...
        </div>
      </div>
    );
  }

  return (
    <div className="vayu-card" style={{ height: "100%" }}>
      <div className="vayu-card-header">
        <span className="vayu-card-title">POTENTIAL IMPACT</span>
        <span className="vayu-badge vayu-badge-severity-low">ASSESSED</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px", margin: "0.5rem 0", fontSize: "0.785rem" }}>
        <div>
          <span style={{ fontWeight: 600, color: "var(--vayu-primary)" }}>🌾 Agriculture:</span>{" "}
          <span style={{ color: "var(--vayu-text)" }}>{agricultureImpact}</span>
        </div>
        <div>
          <span style={{ fontWeight: 600, color: "var(--vayu-secondary)" }}>🏗️ Infrastructure:</span>{" "}
          <span style={{ color: "var(--vayu-text)" }}>{infrastructureImpact}</span>
        </div>
        <div>
          <span style={{ fontWeight: 600, color: "var(--vayu-tertiary)" }}>👥 Population:</span>{" "}
          <span style={{ color: "var(--vayu-text)" }}>{populationImpact}</span>
        </div>
      </div>
    </div>
  );
};
