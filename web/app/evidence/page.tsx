"use client";

import React from "react";
import { EvidenceCard, EvidenceRecordProps } from "@/components/evidence/EvidenceCard";
import { useOperationalState } from "@/hooks/useOperationalState";

export default function EvidencePage() {
  const { latestCard, sourceStatus } = useOperationalState("Gwalior District");

  const sampleEvidenceRecords: EvidenceRecordProps[] = [
    {
      recordId: "EVD-20260922-001",
      sourceId: "OpenWeather Operational Feed",
      authority: "E1 Supporting",
      observedTime: "2026-09-22T05:30:00Z",
      retrievalTime: "2026-09-22T05:31:12Z",
      validityInterval: "3 hours",
      quality: "Verified (QC Passed)",
      freshness: "FRESH (12 min old)",
      payloadHash: "4f8a3c89b2e041d8e57f12a9c40213b7a549d01248ec2a66e4a",
    },
    {
      recordId: "EVD-20260922-002",
      sourceId: "WeatherAPI Surface Observation",
      authority: "E1 Supporting",
      observedTime: "2026-09-22T05:30:00Z",
      retrievalTime: "2026-09-22T05:31:14Z",
      validityInterval: "3 hours",
      quality: "Verified",
      freshness: "FRESH (12 min old)",
      payloadHash: "7b1c4e92a83f502d9c12a784ec50183b92a40e1158a74e22f3b",
    },
    {
      recordId: "EVD-20260922-003",
      sourceId: "IMD District Warning Bulletin (Recorded Fixture)",
      authority: "E0 Official (Fixture)",
      observedTime: "2026-09-22T03:00:00Z",
      retrievalTime: "2026-09-22T03:05:00Z",
      validityInterval: "24 hours",
      quality: "Official Benchmark",
      freshness: "NOMINAL",
      payloadHash: "a93e82d1c5b47a0914e687b1c40293a84e201b77a514d932e18",
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          Evidence Foundation
        </h2>
        <div style={{ fontSize: "0.825rem", color: "var(--vayu-muted)" }}>
          Every assessment, risk tier, and Nirnay decision is anchored in immutable physical evidence records with cryptographic provenance.
        </div>
      </div>

      <div
        style={{
          backgroundColor: "var(--vayu-primary-container)",
          border: "1px solid #BBF7D0",
          borderRadius: "var(--vayu-radius-md)",
          padding: "1rem 1.25rem",
          marginBottom: "1.25rem",
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <span style={{ fontSize: "1.5rem" }}>🛡️</span>
        <div>
          <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--vayu-primary)" }}>
            VAYUBODHAK is Evidence-First
          </div>
          <div style={{ fontSize: "0.785rem", color: "#14532D", marginTop: "2px" }}>
            No black-box inferences or ungrounded generative predictions are permitted in the critical disaster decision path.
          </div>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {sampleEvidenceRecords.map((rec) => (
          <EvidenceCard key={rec.recordId} record={rec} />
        ))}
      </div>
    </div>
  );
}
