"use client";

import React from "react";
import Link from "next/link";
import { SystemOperationalState, LlmStatus } from "@/types/api";

interface SystemStatusIndicatorProps {
  systemState: SystemOperationalState;
  llmStatus?: LlmStatus;
  lastVerifiedTimestamp?: string | null;
  syncMessage?: string | null;
  isSyncing?: boolean;
}

interface StatusConfig {
  bg: string;
  border: string;
  dot: string;
  text: string;
  label: string;
  subtitle: string;
}

const STATUS_CONFIGS: Record<SystemOperationalState, StatusConfig> = {
  FULL_OPERATIONAL: {
    bg: "#F0FDF4",
    border: "#BBF7D0",
    dot: "#16A34A",
    text: "#15803D",
    label: "Full Operational",
    subtitle: "All authoritative feeds & local models verified",
  },
  DEGRADED_DATA: {
    bg: "#FFFBEB",
    border: "#FDE68A",
    dot: "#D97706",
    text: "#B45309",
    label: "Degraded Data",
    subtitle: "One or more secondary feeds unavailable — fallback in use",
  },
  OFFLINE: {
    bg: "#FEF2F2",
    border: "#FECACA",
    dot: "#DC2626",
    text: "#B91C1C",
    label: "Offline Mode",
    subtitle: "No network connection — operating on verified local cache",
  },
  RECOVERING: {
    bg: "#EFF6FF",
    border: "#BFDBFE",
    dot: "#2563EB",
    text: "#1D4ED8",
    label: "Recovering",
    subtitle: "Network restored — synchronizing state & reconciling data",
  },
  UNAVAILABLE: {
    bg: "#FFF7ED",
    border: "#FED7AA",
    dot: "#EA580C",
    text: "#C2410C",
    label: "Service Unavailable",
    subtitle: "Critical services unreachable",
  },
};

export const SystemStatusIndicator: React.FC<SystemStatusIndicatorProps> = ({
  systemState,
  llmStatus = "LLM_AVAILABLE",
  lastVerifiedTimestamp,
  syncMessage,
  isSyncing,
}) => {
  const config = STATUS_CONFIGS[systemState] || STATUS_CONFIGS.FULL_OPERATIONAL;
  const displaySubtitle = isSyncing && syncMessage ? syncMessage : config.subtitle;

  return (
    <div style={{ width: "100%", marginBottom: "0.75rem" }}>
      <Link href="/system-status" style={{ textDecoration: "none" }}>
        <div
          role="status"
          aria-label={`${config.label}: ${displaySubtitle}. Click to inspect system status.`}
          style={{
            backgroundColor: config.bg,
            border: `1px solid ${config.border}`,
            borderRadius: "12px",
            padding: "8px 14px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              style={{
                display: "inline-block",
                width: "10px",
                height: "10px",
                borderRadius: "50%",
                backgroundColor: config.dot,
                flexShrink: 0,
              }}
              className={isSyncing ? "vayu-pulse" : ""}
            />
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ fontSize: "0.78rem", fontWeight: 700, color: config.text }}>
                  {config.label}
                </span>
                {lastVerifiedTimestamp && systemState !== "FULL_OPERATIONAL" && (
                  <span style={{ fontSize: "0.725rem", fontWeight: 500, color: config.text, opacity: 0.85 }}>
                    • Verified {lastVerifiedTimestamp}
                  </span>
                )}
              </div>
              <div style={{ fontSize: "0.725rem", color: config.text, opacity: 0.9 }}>
                {displaySubtitle}
              </div>
            </div>
          </div>

          <div style={{ fontSize: "0.75rem", fontWeight: 600, color: config.text, whiteSpace: "nowrap" }}>
            Details ›
          </div>
        </div>
      </Link>

      {/* Independent LLM degradation alert notice (never hides deterministic assessment) */}
      {llmStatus === "LLM_UNAVAILABLE" && (
        <div
          style={{
            marginTop: "6px",
            backgroundColor: "#F8FAFC",
            border: "1px solid #E2E8F0",
            borderRadius: "8px",
            padding: "6px 12px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "0.725rem",
            color: "#475569",
            fontWeight: 500,
          }}
        >
          <span>ℹ️</span>
          <span>
            AI explanation temporarily unavailable. Verified disaster assessment remains available.
          </span>
        </div>
      )}
    </div>
  );
};
