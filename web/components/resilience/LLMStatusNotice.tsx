"use client";

import React from "react";
import { LlmStatus } from "@/types/api";

interface LLMStatusNoticeProps {
  status: LlmStatus;
}

export const LLMStatusNotice: React.FC<LLMStatusNoticeProps> = ({ status }) => {
  if (status === "LLM_AVAILABLE") {
    return null;
  }

  return (
    <div
      style={{
        backgroundColor: "#F8FAFC",
        border: "1px solid #E2E8F0",
        borderRadius: "8px",
        padding: "8px 12px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        fontSize: "0.75rem",
        color: "#475569",
        fontWeight: 500,
        margin: "0.5rem 0",
      }}
    >
      <span style={{ fontSize: "0.9rem" }}>ℹ️</span>
      <span>
        AI explanation temporarily unavailable. Verified disaster assessment remains available.
      </span>
    </div>
  );
};
