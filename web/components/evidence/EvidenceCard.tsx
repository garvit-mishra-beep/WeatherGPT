"use client";

import React from "react";

export interface EvidenceRecordProps {
  recordId: string;
  sourceId: string;
  authority: string;
  observedTime: string;
  retrievalTime: string;
  validityInterval: string;
  quality: string;
  freshness: string;
  payloadHash: string;
}

export const EvidenceCard: React.FC<{ record: EvidenceRecordProps }> = ({ record }) => {
  const isOfficial = record.authority.includes("E0") || record.sourceId.includes("IMD") || record.sourceId.includes("CWC");

  return (
    <div
      className="vayu-card"
      style={{
        border: "1px solid var(--vayu-border)",
        borderRadius: "var(--vayu-radius-md)",
        marginBottom: "0.85rem",
      }}
    >
      <div className="vayu-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "1.1rem" }}>{isOfficial ? "🏛️" : "📡"}</span>
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--vayu-text)" }}>
              {record.sourceId}
            </div>
            <div style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
              ID: {record.recordId}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", gap: "6px" }}>
          <span className={`vayu-badge ${isOfficial ? "vayu-badge-live" : "vayu-badge-cached"}`}>
            {record.authority}
          </span>
          <span className="vayu-badge vayu-badge-fallback">
            {record.freshness}
          </span>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "8px",
          fontSize: "0.75rem",
          margin: "0.5rem 0",
        }}
      >
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Observed At:</span>{" "}
          <strong>{record.observedTime}</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Ingestion:</span>{" "}
          <strong>{record.retrievalTime}</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Validity:</span>{" "}
          <strong>{record.validityInterval}</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Quality State:</span>{" "}
          <strong style={{ color: "var(--vayu-primary)" }}>{record.quality}</strong>
        </div>
      </div>

      <div
        style={{
          marginTop: "0.5rem",
          paddingTop: "0.5rem",
          borderTop: "1px solid var(--vayu-border)",
          fontSize: "0.685rem",
          color: "var(--vayu-muted)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>Cryptographic Hash:</span>
        <code style={{ fontFamily: "monospace", color: "var(--vayu-text)" }}>
          {record.payloadHash.slice(0, 24)}...
        </code>
      </div>
    </div>
  );
};
