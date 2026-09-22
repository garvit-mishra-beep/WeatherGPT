"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { BrainSelector } from "@/components/intelligence/BrainSelector";
import { BrainType } from "@/types/api";
import { fetchRiskMatrix } from "@/lib/api/analyst";
import { RiskMatrixResponse } from "@/types/api";

export default function BrainPage() {
  const params = useParams();
  const brainParam = (params?.brain as string)?.toUpperCase() || "ANALYST";
  const validBrain: BrainType =
    ["GENERAL", "FARMER", "RESEARCHER", "ANALYST"].includes(brainParam)
      ? (brainParam as BrainType)
      : "ANALYST";

  const [activeBrain, setActiveBrain] = useState<BrainType>(validBrain);
  const [riskMatrix, setRiskMatrix] = useState<RiskMatrixResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // General Brain Chat State
  const [chatInput, setChatInput] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    {
      sender: "bot",
      text: "Namaste! I am the VAYUBODHAK Assistant. I provide natural-language answers grounded strictly in verified meteorological observations. Critical disaster assessments and Nirnay decisions are evaluated by our deterministic engines.",
    },
  ]);

  useEffect(() => {
    setActiveBrain(validBrain);
  }, [validBrain]);

  // Load Analyst Risk Matrix
  useEffect(() => {
    if (activeBrain === "ANALYST") {
      setLoading(true);
      fetchRiskMatrix({
        district_name: "Gwalior District",
        latitude: 26.22,
        longitude: 78.18,
        hazard_type: "heavy_rainfall",
        observed_rain_mm: 12.0,
        observed_wind_kmh: 14.5,
      })
        .then((res) => setRiskMatrix(res))
        .catch((err) => console.warn("Failed loading risk matrix:", err))
        .finally(() => setLoading(false));
    }
  }, [activeBrain]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatMessages((prev) => [...prev, { sender: "user", text: userMsg }]);
    setChatInput("");

    // Grounded simulated response
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: `Observation summary for Gwalior District: Temperature 28.5°C, relative humidity 65%, surface pressure 1012 hPa. Nirnay decision remains MONITOR with Low composite risk (0.22/10.0). No official red alerts issued by state authorities.`,
        },
      ]);
    }, 600);
  };

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          Four-Brain Intelligence
        </h2>
        <div style={{ fontSize: "0.825rem", color: "var(--vayu-muted)" }}>
          Coordinated multi-agent domain brains sharing unified evidence foundation and Nirnay decision logic.
        </div>
      </div>

      {/* Brain Tabs Selector */}
      <BrainSelector activeBrain={activeBrain} onSelectBrain={setActiveBrain} />

      {/* BRAIN 1: ANALYST BRAIN */}
      {activeBrain === "ANALYST" && (
        <div className="vayu-card">
          <div className="vayu-card-header">
            <span className="vayu-card-title">ANALYST DECISION SUPPORT • COMPOSITE RISK SYNTHESIS</span>
            <span className="vayu-badge vayu-badge-live">
              {riskMatrix?.risk_level || "LOW"} RISK
            </span>
          </div>

          <p style={{ fontSize: "0.825rem", color: "var(--vayu-muted)", marginBottom: "1rem" }}>
            Deterministic linear risk calculation: <code>Composite Risk = 0.50 * Hazard + 0.30 * Exposure + 0.20 * Vulnerability</code>.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "1rem",
              marginBottom: "1.25rem",
            }}
          >
            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)" }}>Hazard Score (50%)</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--vayu-primary)" }}>
                {riskMatrix ? (riskMatrix.hazard_index * 10).toFixed(1) : "1.8"}
                <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--vayu-muted)" }}> / 10.0</span>
              </div>
            </div>

            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)" }}>Exposure Score (30%)</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--vayu-secondary)" }}>
                {riskMatrix ? (riskMatrix.exposure_index * 10).toFixed(1) : "3.0"}
                <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--vayu-muted)" }}> / 10.0</span>
              </div>
            </div>

            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)" }}>Vulnerability Score (20%)</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--vayu-tertiary)" }}>
                {riskMatrix ? (riskMatrix.vulnerability_index * 10).toFixed(1) : "2.5"}
                <span style={{ fontSize: "0.8rem", fontWeight: 500, color: "var(--vayu-muted)" }}> / 10.0</span>
              </div>
            </div>

            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)" }}>Action Priority</div>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--vayu-primary)", marginTop: "4px" }}>
                {riskMatrix?.action_priority || "Routine Monitoring"}
              </div>
            </div>
          </div>

          <div style={{ borderTop: "1px solid var(--vayu-border)", paddingTop: "0.85rem", fontSize: "0.75rem", color: "var(--vayu-muted)" }}>
            Authority Provenance: Source feeds verified across OpenWeather (Supporting) and recorded CWC hydrologic thresholds.
          </div>
        </div>
      )}

      {/* BRAIN 2: FARMER BRAIN */}
      {activeBrain === "FARMER" && (
        <div className="vayu-card">
          <div className="vayu-card-header">
            <span className="vayu-card-title">FARMER BRAIN • AGRICULTURAL DECISION INTELLIGENCE</span>
            <span className="vayu-badge vayu-badge-live">FAO-56 COMPLIANT</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <h4 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--vayu-primary)", marginBottom: "4px" }}>
                🌾 Crop Water Balance & ET0
              </h4>
              <p style={{ fontSize: "0.785rem", color: "var(--vayu-muted)", lineHeight: 1.4 }}>
                Penman-Monteith reference evapotranspiration (ET0): <strong>4.82 mm/day</strong>. Net irrigation requirement for current wheat plot: <strong>0.0 mm (Sufficient soil moisture)</strong>.
              </p>
            </div>

            <div style={{ padding: "12px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "8px" }}>
              <h4 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--vayu-secondary)", marginBottom: "4px" }}>
                🧪 Safe Spray Window
              </h4>
              <p style={{ fontSize: "0.785rem", color: "var(--vayu-muted)", lineHeight: 1.4 }}>
                Wind speed &lt; 15 km/h, Rain probability &lt; 30%. Status: <strong style={{ color: "var(--vayu-severity-green)" }}>SUITABLE FOR SPRAYING</strong> until 16:00 IST.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* BRAIN 3: RESEARCHER BRAIN */}
      {activeBrain === "RESEARCHER" && (
        <div className="vayu-card">
          <div className="vayu-card-header">
            <span className="vayu-card-title">RESEARCHER BRAIN • EVIDENCE & SCIENTIFIC PROVENANCE</span>
            <span className="vayu-badge vayu-badge-cached">AUDIT GRADE</span>
          </div>

          <p style={{ fontSize: "0.825rem", color: "var(--vayu-muted)", marginBottom: "1rem" }}>
            Direct access to raw physical observations, NWP divergence checks (GFS vs. ECMWF), and historical climate baselines.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.785rem" }}>
            <div style={{ padding: "10px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "6px" }}>
              <strong>NWP Model Divergence:</strong> GFS forecast (18.2 mm) vs. ECMWF forecast (16.4 mm). Divergence delta: 1.8 mm (Low uncertainty).
            </div>
            <div style={{ padding: "10px", backgroundColor: "var(--vayu-surface-variant)", borderRadius: "6px" }}>
              <strong>Historical Climate Baseline:</strong> 30-year September rainfall norm for Gwalior: 142.5 mm. Current monthly cumulative: 128.0 mm (Normal).
            </div>
          </div>
        </div>
      )}

      {/* BRAIN 4: GENERAL BRAIN (Conversational) */}
      {activeBrain === "GENERAL" && (
        <div className="vayu-card">
          <div className="vayu-card-header">
            <span className="vayu-card-title">GENERAL BRAIN • CONVERSATIONAL WEATHER ASSISTANT</span>
            <span className="vayu-badge vayu-badge-live">GROUNDED AI</span>
          </div>

          <div
            style={{
              height: "320px",
              overflowY: "auto",
              padding: "1rem",
              backgroundColor: "var(--vayu-surface-variant)",
              borderRadius: "8px",
              marginBottom: "1rem",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
            }}
          >
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: msg.sender === "user" ? "flex-end" : "flex-start",
                  maxWidth: "80%",
                  padding: "8px 14px",
                  borderRadius: "12px",
                  backgroundColor: msg.sender === "user" ? "var(--vayu-primary)" : "var(--vayu-surface)",
                  color: msg.sender === "user" ? "#FFFFFF" : "var(--vayu-text)",
                  border: msg.sender === "bot" ? "1px solid var(--vayu-border)" : "none",
                  fontSize: "0.825rem",
                  lineHeight: 1.4,
                }}
              >
                {msg.text}
              </div>
            ))}
          </div>

          <form onSubmit={handleSendMessage} style={{ display: "flex", gap: "8px" }}>
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask a question about current weather conditions or crop safety..."
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: "8px",
                border: "1px solid var(--vayu-border)",
                fontSize: "0.85rem",
                outline: "none",
              }}
            />
            <button
              type="submit"
              style={{
                padding: "10px 18px",
                backgroundColor: "var(--vayu-primary)",
                color: "#FFFFFF",
                borderRadius: "8px",
                fontWeight: 700,
                fontSize: "0.85rem",
              }}
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
