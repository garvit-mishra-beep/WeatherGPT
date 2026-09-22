"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  label: string;
  href: string;
  icon: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/overview", icon: "🏠" },
  { label: "Nirnay Decision", href: "/nirnay", icon: "⚡" },
  { label: "Intelligence (Brains)", href: "/intelligence/analyst", icon: "🧠" },
  { label: "Evidence Foundation", href: "/evidence", icon: "📜" },
  { label: "Operational Alerts", href: "/alerts", icon: "🚨" },
  { label: "Spatial Map", href: "/map", icon: "🗺️" },
  { label: "System Status", href: "/system-status", icon: "🛡️" },
];

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  return (
    <aside
      style={{
        backgroundColor: "var(--vayu-surface)",
        borderRight: "1px solid var(--vayu-border)",
        padding: "1.25rem 1rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        minHeight: "calc(100vh - 60px)",
      }}
    >
      <div>
        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--vayu-muted)", letterSpacing: "0.05em", textTransform: "uppercase", padding: "0 0.5rem 0.5rem 0.5rem" }}>
          Navigation
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || (item.href.startsWith("/intelligence") && pathname.startsWith("/intelligence"));

            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  fontSize: "0.85rem",
                  fontWeight: isActive ? 700 : 500,
                  backgroundColor: isActive ? "var(--vayu-primary-container)" : "transparent",
                  color: isActive ? "var(--vayu-primary)" : "var(--vayu-text)",
                  transition: "all 0.15s ease",
                  textDecoration: "none",
                }}
              >
                <span style={{ fontSize: "1rem" }}>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div
        style={{
          borderTop: "1px solid var(--vayu-border)",
          paddingTop: "0.75rem",
          fontSize: "0.7rem",
          color: "var(--vayu-muted)",
          lineHeight: 1.4,
          paddingLeft: "0.5rem",
        }}
      >
        <div><strong>VAYUBODHAK v1.0</strong></div>
        <div>FastAPI + Next.js Hybrid</div>
        <div style={{ marginTop: "4px", color: "var(--vayu-primary)", fontWeight: 600 }}>
          Deterministic Pipeline
        </div>
      </div>
    </aside>
  );
};
