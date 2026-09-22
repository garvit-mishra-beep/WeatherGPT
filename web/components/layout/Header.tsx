"use client";

import React from "react";
import Link from "next/link";
import { SystemOperationalState, DataSourceStatus } from "@/types/api";

interface HeaderProps {
  currentDistrict?: string;
  sourceStatus?: DataSourceStatus;
  systemState?: SystemOperationalState;
  onRefresh?: () => void;
  isSyncing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentDistrict = "Gwalior District",
  sourceStatus = "LIVE",
  systemState = "FULL_OPERATIONAL",
  onRefresh,
  isSyncing = false,
}) => {
  return (
    <header
      style={{
        backgroundColor: "var(--vayu-surface)",
        borderBottom: "1px solid var(--vayu-border)",
        padding: "0.85rem 1.5rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <Link href="/overview" style={{ display: "flex", alignItems: "center", gap: "8px", textDecoration: "none" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              backgroundColor: "var(--vayu-primary)",
              color: "#FFFFFF",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: "1rem",
            }}
          >
            V
          </div>
          <div>
            <h1
              style={{
                fontSize: "1.1rem",
                fontWeight: 800,
                color: "var(--vayu-primary)",
                letterSpacing: "0.02em",
                lineHeight: 1.1,
              }}
            >
              VAYUBODHAK
            </h1>
            <div style={{ fontSize: "0.685rem", color: "var(--vayu-muted)", fontWeight: 500 }}>
              Evidence-First Disaster Intelligence
            </div>
          </div>
        </Link>

        {/* Location Selector Badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            padding: "4px 10px",
            backgroundColor: "var(--vayu-surface-variant)",
            borderRadius: "var(--vayu-radius-sm)",
            fontSize: "0.785rem",
            fontWeight: 600,
            color: "var(--vayu-text)",
            border: "1px solid var(--vayu-border)",
          }}
        >
          <span>📍</span>
          <span>{currentDistrict}</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Source Status Pill */}
        <span
          className={`vayu-badge vayu-badge-${sourceStatus.toLowerCase() === "live" ? "live" : "cached"}`}
          style={{ padding: "4px 8px" }}
        >
          {sourceStatus} ASSESSMENTS
        </span>

        {/* Refresh Button */}
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            disabled={isSyncing}
            style={{
              padding: "5px 10px",
              backgroundColor: "var(--vayu-surface-variant)",
              border: "1px solid var(--vayu-border)",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--vayu-muted)",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            <span className={isSyncing ? "vayu-pulse" : ""}>🔄</span>
            <span>{isSyncing ? "Syncing..." : "Sync"}</span>
          </button>
        )}
      </div>
    </header>
  );
};
