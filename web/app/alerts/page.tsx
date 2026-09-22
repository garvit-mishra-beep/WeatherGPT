"use client";

import React from "react";
import { useOperationalState } from "@/hooks/useOperationalState";

export default function AlertsPage() {
  const { events } = useOperationalState("Gwalior District");

  const sampleNotifications = [
    {
      id: "NOTIF-001",
      priority: "OFFICIAL_WARNING",
      priorityLabel: "OFFICIAL WARNING (CONTROLLED SCENARIO)",
      title: "[CONTROLLED SCENARIO] Orange Warning: Gwalior District",
      body: "Heavy to very heavy rainfall advisory (Benchmark scenario data for verification). Non-live authority feed.",
      timestamp: "10 min ago",
      badgeColor: "#EA580C",
      badgeBg: "#FFEDD5",
    },
    {
      id: "NOTIF-002",
      priority: "DECISION_CHANGE",
      priorityLabel: "DECISION CHANGE",
      title: "Decision Update [PROCEED_WITH_CAUTION]: Gwalior District",
      body: "Nirnay decision transitioned from MONITOR to PROCEED_WITH_CAUTION following precipitation escalation delta.",
      timestamp: "24 min ago",
      badgeColor: "#CA8A04",
      badgeBg: "#FEF9C3",
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: "1.25rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          Operational Alerts & Notifications
        </h2>
        <div style={{ fontSize: "0.825rem", color: "var(--vayu-muted)" }}>
          Real-time event notifications emitted by the near-real-time operational event engine.
        </div>
      </div>

      {/* Notifications Stream */}
      <div className="vayu-card" style={{ marginBottom: "1.25rem" }}>
        <div className="vayu-card-header">
          <span className="vayu-card-title">DISPATCHED NOTIFICATIONS</span>
          <span className="vayu-badge vayu-badge-live">OUTBOX SYNCED</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {sampleNotifications.map((notif) => (
            <div
              key={notif.id}
              style={{
                border: "1px solid var(--vayu-border)",
                borderRadius: "var(--vayu-radius-md)",
                padding: "12px 14px",
                backgroundColor: "var(--vayu-surface)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <span
                  style={{
                    backgroundColor: notif.badgeBg,
                    color: notif.badgeColor,
                    fontSize: "0.685rem",
                    fontWeight: 800,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    letterSpacing: "0.03em",
                  }}
                >
                  {notif.priorityLabel}
                </span>
                <span style={{ fontSize: "0.725rem", color: "var(--vayu-muted)" }}>
                  {notif.timestamp}
                </span>
              </div>

              <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--vayu-text)", marginBottom: "4px" }}>
                {notif.title}
              </div>

              <div style={{ fontSize: "0.785rem", color: "var(--vayu-muted)", lineHeight: 1.4 }}>
                {notif.body}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Raw Operational Event Log */}
      <div className="vayu-card">
        <div className="vayu-card-header">
          <span className="vayu-card-title">OPERATIONAL EVENT LOG</span>
          <span className="vayu-badge vayu-badge-cached">
            {events.length} Events Total
          </span>
        </div>

        {events.length === 0 ? (
          <div style={{ textAlign: "center", padding: "1.5rem", color: "var(--vayu-muted)", fontSize: "0.8rem" }}>
            No operational events logged yet for current session.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.775rem" }}>
            {events.map((e) => (
              <div
                key={e.event_id}
                style={{
                  padding: "8px 12px",
                  backgroundColor: "var(--vayu-surface-variant)",
                  borderRadius: "6px",
                  border: "1px solid var(--vayu-border)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: "var(--vayu-text)" }}>
                    {e.event_type} • {e.geography}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
                    Source: {e.source_id} ({e.source_authority})
                  </div>
                </div>
                <div style={{ textAlign: "right", color: "var(--vayu-muted)", fontSize: "0.7rem" }}>
                  <div>Seq #{e.sequence_number || 1}</div>
                  <div>ID: {e.event_id}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
