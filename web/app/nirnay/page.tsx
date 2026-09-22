"use client";

import React, { useState } from "react";
import { NirnayCard } from "@/components/nirnay/NirnayCard";
import { useOperationalState } from "@/hooks/useOperationalState";

export default function NirnayPage() {
  const { latestCard, latestRevision } = useOperationalState("Gwalior District");
  const [selectedRevision, setSelectedRevision] = useState<number>(latestRevision || 1);

  const revisions = [
    {
      revNumber: 1,
      timestamp: "2026-09-22 05:30 IST",
      verdict: "MONITOR",
      severity: "LOW",
      reason: "Initial baseline assessment under nominal rainfall (1.2 mm/h).",
      changedStages: ["BASELINE"],
    },
    {
      revNumber: 2,
      timestamp: "2026-09-22 06:15 IST",
      verdict: "PROCEED_WITH_CAUTION",
      severity: "MODERATE",
      reason: "Precipitation delta exceeded +30 mm/h. Hazard recomputed; Exposure and Vulnerability reused.",
      changedStages: ["HAZARD", "RISK", "IMPACT", "DECISION"],
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          Nirnay Decision Intelligence
        </h2>
        <div style={{ fontSize: "0.825rem", color: "var(--vayu-muted)" }}>
          Audit-grade deterministic multi-criteria decision synthesis with revision lineage and supersession tracking.
        </div>
      </div>

      {/* Active Decision Card */}
      <div style={{ marginBottom: "1.5rem" }}>
        <NirnayCard card={latestCard} />
      </div>

      {/* Revision History Section */}
      <div className="vayu-card">
        <div className="vayu-card-header">
          <span className="vayu-card-title">DECISION REVISION TIMELINE</span>
          <span className="vayu-badge vayu-badge-cached">
            Current Revision: Rev {latestRevision || 1}
          </span>
        </div>

        <p style={{ fontSize: "0.8rem", color: "var(--vayu-muted)", marginBottom: "1rem" }}>
          Selective recalculation engine updates decisions when physical deltas exceed operational thresholds.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {revisions.map((rev) => (
            <div
              key={rev.revNumber}
              style={{
                border: "1px solid var(--vayu-border)",
                borderRadius: "var(--vayu-radius-md)",
                padding: "12px 16px",
                backgroundColor: rev.revNumber === (latestRevision || 1) ? "var(--vayu-primary-container)" : "var(--vayu-surface)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontWeight: 800, fontSize: "0.85rem", color: "var(--vayu-primary)" }}>
                    Revision {rev.revNumber}
                  </span>
                  <span
                    style={{
                      fontSize: "0.7rem",
                      fontWeight: 700,
                      padding: "2px 6px",
                      borderRadius: "4px",
                      backgroundColor: rev.severity === "LOW" ? "rgba(22, 163, 74, 0.12)" : "rgba(202, 138, 4, 0.12)",
                      color: rev.severity === "LOW" ? "var(--vayu-severity-green)" : "var(--vayu-severity-yellow)",
                    }}
                  >
                    {rev.verdict} ({rev.severity})
                  </span>
                </div>

                <span style={{ fontSize: "0.725rem", color: "var(--vayu-muted)" }}>
                  {rev.timestamp}
                </span>
              </div>

              <div style={{ fontSize: "0.785rem", color: "var(--vayu-text)", marginBottom: "6px" }}>
                {rev.reason}
              </div>

              <div style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
                Recalculated Stages: <strong>{rev.changedStages.join(" • ")}</strong>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
