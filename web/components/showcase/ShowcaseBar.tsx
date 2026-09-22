"use client";

import React, { useState, useEffect } from "react";
import { startShowcase, nextShowcaseStep, resetShowcase, fetchShowcaseStatus } from "@/lib/api/showcase";
import { ShowcaseStatus } from "@/types/api";

interface ShowcaseBarProps {
  onScenarioStepChanged?: () => void;
}

export const ShowcaseBar: React.FC<ShowcaseBarProps> = ({ onScenarioStepChanged }) => {
  const [status, setStatus] = useState<ShowcaseStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const refreshStatus = async () => {
    try {
      const s = await fetchShowcaseStatus();
      setStatus(s);
    } catch {
      // Backend might be offline or non-showcase mode
    }
  };

  useEffect(() => {
    refreshStatus();
  }, []);

  const handleStart = async () => {
    setIsLoading(true);
    try {
      await startShowcase();
      await refreshStatus();
      onScenarioStepChanged?.();
    } catch (err) {
      console.error("Failed to start showcase:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = async () => {
    setIsLoading(true);
    try {
      await nextShowcaseStep();
      await refreshStatus();
      onScenarioStepChanged?.();
    } catch (err) {
      console.error("Failed to advance showcase:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    setIsLoading(true);
    try {
      await resetShowcase();
      await refreshStatus();
      onScenarioStepChanged?.();
    } catch (err) {
      console.error("Failed to reset showcase:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: "#F1F5F9",
        borderBottom: "1px solid var(--vayu-border)",
        padding: "6px 1.5rem",
        fontSize: "0.75rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span
          style={{
            backgroundColor: "#FEF3C7",
            color: "#B45309",
            fontWeight: 700,
            padding: "2px 6px",
            borderRadius: "4px",
            fontSize: "0.685rem",
            border: "1px solid #FDE68A",
          }}
        >
          SCENARIO CONTROLLER
        </span>
        <span style={{ color: "var(--vayu-muted)" }}>
          Step: <strong>{status?.step_name || (status?.step_index !== undefined && status.step_index >= 0 ? `Step ${status.step_index}` : "Initial")}</strong>
        </span>
        {status?.verdict && (
          <span style={{ color: "var(--vayu-primary)", fontWeight: 600 }}>
            • Verdict: {status.verdict} ({status.severity || "LOW"})
          </span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <button
          type="button"
          onClick={handleReset}
          disabled={isLoading}
          style={{
            padding: "3px 8px",
            backgroundColor: "#FFFFFF",
            border: "1px solid var(--vayu-border)",
            borderRadius: "4px",
            fontWeight: 600,
            color: "var(--vayu-muted)",
            fontSize: "0.725rem",
          }}
        >
          Reset
        </button>

        <button
          type="button"
          onClick={handleStart}
          disabled={isLoading}
          style={{
            padding: "3px 8px",
            backgroundColor: "var(--vayu-primary)",
            color: "#FFFFFF",
            borderRadius: "4px",
            fontWeight: 600,
            fontSize: "0.725rem",
          }}
        >
          Start
        </button>

        <button
          type="button"
          onClick={handleNext}
          disabled={isLoading}
          style={{
            padding: "3px 8px",
            backgroundColor: "var(--vayu-secondary)",
            color: "#FFFFFF",
            borderRadius: "4px",
            fontWeight: 600,
            fontSize: "0.725rem",
          }}
        >
          Next Step ▶
        </button>
      </div>
    </div>
  );
};
