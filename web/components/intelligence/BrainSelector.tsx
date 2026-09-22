"use client";

import React from "react";
import Link from "next/link";
import { BrainType } from "@/types/api";

interface BrainSelectorProps {
  activeBrain: BrainType;
  onSelectBrain?: (brain: BrainType) => void;
}

interface BrainMetadata {
  id: BrainType;
  title: string;
  subtitle: string;
  icon: string;
  badge: string;
  description: string;
}

export const BRAIN_CATALOG: BrainMetadata[] = [
  {
    id: "GENERAL",
    title: "General Brain",
    subtitle: "Conversational Intelligence",
    icon: "💬",
    badge: "Interactive",
    description: "Natural language weather guidance grounded in verified context without calculating critical disaster decisions.",
  },
  {
    id: "FARMER",
    title: "Farmer Brain",
    subtitle: "Agricultural Advisory",
    icon: "🌾",
    badge: "Field Ops",
    description: "Deterministic FAO-56 crop water balance, evapotranspiration (ET0), and safe chemical spray action windows.",
  },
  {
    id: "RESEARCHER",
    title: "Researcher Brain",
    subtitle: "Scientific Evidence",
    icon: "🔬",
    badge: "Evidence-First",
    description: "Direct access to immutable observation provenance, NWP model divergence, and historical climate norms.",
  },
  {
    id: "ANALYST",
    title: "Analyst Brain",
    subtitle: "Disaster Risk Synthesis",
    icon: "📊",
    badge: "Mission Critical",
    description: "Deterministic 0.50*H + 0.30*E + 0.20*V composite risk matrix and emergency response action priorities.",
  },
];

export const BrainSelector: React.FC<BrainSelectorProps> = ({ activeBrain, onSelectBrain }) => {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
        gap: "12px",
        marginBottom: "1.5rem",
      }}
    >
      {BRAIN_CATALOG.map((brain) => {
        const isActive = activeBrain === brain.id;
        const brainHref = `/intelligence/${brain.id.toLowerCase()}`;

        return (
          <Link
            key={brain.id}
            href={brainHref}
            onClick={() => onSelectBrain?.(brain.id)}
            style={{ textDecoration: "none" }}
          >
            <div
              className="vayu-card"
              style={{
                borderColor: isActive ? "var(--vayu-primary)" : "var(--vayu-border)",
                backgroundColor: isActive ? "var(--vayu-primary-container)" : "var(--vayu-surface)",
                cursor: "pointer",
                height: "100%",
                transition: "all 0.15s ease",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "1.5rem" }}>{brain.icon}</span>
                <span
                  style={{
                    fontSize: "0.685rem",
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: "6px",
                    backgroundColor: isActive ? "var(--vayu-primary)" : "var(--vayu-surface-variant)",
                    color: isActive ? "#FFFFFF" : "var(--vayu-muted)",
                    textTransform: "uppercase",
                  }}
                >
                  {brain.badge}
                </span>
              </div>

              <h3
                style={{
                  fontSize: "0.95rem",
                  fontWeight: 700,
                  color: isActive ? "var(--vayu-primary)" : "var(--vayu-text)",
                  marginBottom: "2px",
                }}
              >
                {brain.title}
              </h3>
              <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)", marginBottom: "6px" }}>
                {brain.subtitle}
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--vayu-muted)", lineHeight: 1.35 }}>
                {brain.description}
              </p>
            </div>
          </Link>
        );
      })}
    </div>
  );
};
