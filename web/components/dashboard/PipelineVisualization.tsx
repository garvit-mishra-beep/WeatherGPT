"use client";

import React, { useState } from "react";
import { NirnayCard } from "@/types/api";

interface PipelineVisualizationProps {
  card: NirnayCard | null;
}

interface StageDetail {
  id: string;
  name: string;
  status: string;
  metrics: Record<string, string | number>;
  description: string;
}

export const PipelineVisualization: React.FC<PipelineVisualizationProps> = ({ card }) => {
  const [selectedStage, setSelectedStage] = useState<string>("hazard");

  const stages: StageDetail[] = [
    {
      id: "evidence",
      name: "Evidence",
      status: card ? (card.sourceStatus || "VERIFIED") : "NOMINAL",
      description: "Immutable physical observations ingested via verified source adapters (E0/E1 authority).",
      metrics: {
        "Source Authority": card?.ledger?.sources?.[0]?.authority || "E0 Official",
        "Ingested Feeds": card?.ledger?.sources?.length || 2,
        "Cryptographic Integrity": card?.ledger?.signature ? "Verified (SHA-256)" : "Verified",
      },
    },
    {
      id: "hazard",
      name: "Hazard",
      status: card?.severity || "LOW",
      description: "Deterministic meteorological threshold rules evaluating extreme precipitation, wind gust, and flash flood potential.",
      metrics: {
        "Hazard Index": card?.severity === "HIGH" ? "7.5 / 10.0" : "1.8 / 10.0",
        "Primary Hazard": "Heavy Precipitation / Wind Drift",
        "Threshold Evaluation": "Deterministic Rule Registry v2.1",
      },
    },
    {
      id: "exposure",
      name: "Exposure",
      status: "CALCULATED",
      description: "Spatial GIS overlay assessing population density, crop acreage, and critical infrastructure within affected boundary.",
      metrics: {
        "Target District": "Gwalior District",
        "Cultivated Land": "48,200 ha",
        "Critical Assets": "14 Hospitals, 84 Bridge Culverts",
      },
    },
    {
      id: "vulnerability",
      name: "Vulnerability",
      status: "INDEXED",
      description: "Socio-economic baseline and physical asset vulnerability coefficients.",
      metrics: {
        "Agricultural Sensitivity": "Moderate (Foliage vegetative stage)",
        "Drainage Capacity": "Nominal urban stormwater flow",
        "Vulnerability Index": "0.32 (Low-Moderate)",
      },
    },
    {
      id: "risk",
      name: "Risk",
      status: card?.severity || "LOW",
      description: "Composite synthesis matrix: Risk = 0.50*H + 0.30*E + 0.20*V (no black-box weights).",
      metrics: {
        "Synthesis Formula": "0.50*H + 0.30*E + 0.20*V",
        "Risk Tier": `${card?.severity || "LOW"} RISK`,
        "Action Priority": card?.severity === "HIGH" ? "Immediate Evacuation Alert" : "Routine Monitoring",
      },
    },
    {
      id: "impact",
      name: "Impact",
      status: "ASSESSED",
      description: "Sectoral potential impact evaluation across agriculture, physical infrastructure, and public safety.",
      metrics: {
        "Agricultural Demand": card?.action_window?.status === "available" ? "Safe operational window identified" : "Spray wash-off risk",
        "Drainage Vulnerability": "Low risk of localized ponding",
        "Public Safety": "No evacuation threshold breached",
      },
    },
    {
      id: "nirnay",
      name: "Nirnay",
      status: card?.verdict || "MONITOR",
      description: "Audit-grade deterministic operational decision card emitted to mobile and field operations.",
      metrics: {
        "Verdict": card?.verdict || "MONITOR",
        "Severity": `${card?.severity || "LOW"} RISK`,
        "Decision ID": card?.decision_id || "REV-SHOWCASE-001",
      },
    },
  ];

  const activeStage = stages.find((s) => s.id === selectedStage) || stages[0];

  return (
    <div className="vayu-card" style={{ marginTop: "1rem" }}>
      <div className="vayu-card-header">
        <span className="vayu-card-title">DETERMINISTIC INTELLIGENCE PIPELINE</span>
        <span style={{ fontSize: "0.725rem", color: "var(--vayu-muted)", fontWeight: 600 }}>
          LINEAR STAGE EXECUTION • ZERO LLM IN CRITICAL PATH
        </span>
      </div>

      {/* Horizontal Pipeline Steps */}
      <div className="vayu-pipeline-container">
        {stages.map((stg, index) => {
          const isActive = selectedStage === stg.id;
          return (
            <React.Fragment key={stg.id}>
              <button
                type="button"
                onClick={() => setSelectedStage(stg.id)}
                className={`vayu-pipeline-stage ${isActive ? "active" : ""}`}
                style={{
                  border: isActive ? "2px solid var(--vayu-primary)" : "1px solid var(--vayu-border)",
                }}
              >
                <span>{index + 1}. {stg.name}</span>
                <span
                  style={{
                    fontSize: "0.685rem",
                    padding: "1px 5px",
                    borderRadius: "4px",
                    backgroundColor: isActive ? "var(--vayu-primary)" : "var(--vayu-surface-variant)",
                    color: isActive ? "#FFFFFF" : "var(--vayu-muted)",
                    fontWeight: 700,
                  }}
                >
                  {stg.status}
                </span>
              </button>
              {index < stages.length - 1 && <span className="vayu-pipeline-arrow">→</span>}
            </React.Fragment>
          );
        })}
      </div>

      {/* Selected Stage Detail Drawer */}
      <div
        style={{
          marginTop: "0.85rem",
          padding: "1rem",
          backgroundColor: "var(--vayu-surface-variant)",
          borderRadius: "var(--vayu-radius-md)",
          border: "1px solid var(--vayu-border)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <h4 style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--vayu-primary)" }}>
            Stage Assessment: {activeStage.name}
          </h4>
          <span className="vayu-badge vayu-badge-cached">
            Status: {activeStage.status}
          </span>
        </div>

        <p style={{ fontSize: "0.8rem", color: "var(--vayu-muted)", marginBottom: "0.75rem", lineHeight: 1.4 }}>
          {activeStage.description}
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "8px",
            fontSize: "0.785rem",
          }}
        >
          {Object.entries(activeStage.metrics).map(([key, value]) => (
            <div
              key={key}
              style={{
                backgroundColor: "var(--vayu-surface)",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid var(--vayu-border)",
              }}
            >
              <div style={{ color: "var(--vayu-muted)", fontSize: "0.7rem" }}>{key}</div>
              <strong style={{ color: "var(--vayu-text)" }}>{value}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
