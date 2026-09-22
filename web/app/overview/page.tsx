"use client";

import React, { useState, useEffect } from "react";
import { useOperationalState } from "@/hooks/useOperationalState";
import { SystemStatusIndicator } from "@/components/resilience/SystemStatusIndicator";
import { NirnayCard } from "@/components/nirnay/NirnayCard";
import { WeatherCard } from "@/components/dashboard/WeatherCard";
import { HazardCard } from "@/components/dashboard/HazardCard";
import { RiskCard } from "@/components/dashboard/RiskCard";
import { ImpactCard } from "@/components/dashboard/ImpactCard";
import { PipelineVisualization } from "@/components/dashboard/PipelineVisualization";
import { fetchCurrentWeather } from "@/lib/api/weather";
import { WeatherObservation } from "@/types/api";

export default function OverviewPage() {
  const {
    systemState,
    sourceStatus,
    llmStatus,
    lastVerifiedTimestamp,
    syncMessage,
    isSyncing,
    latestCard,
    events,
  } = useOperationalState("Gwalior District");

  const [weather, setWeather] = useState<WeatherObservation | null>(null);
  const [loadingWeather, setLoadingWeather] = useState<boolean>(true);

  useEffect(() => {
    async function loadWeather() {
      try {
        // Gwalior coordinates: 26.22, 78.18
        const w = await fetchCurrentWeather(26.22, 78.18);
        setWeather(w);
      } catch (e) {
        console.warn("Could not load weather observations:", e);
      } finally {
        setLoadingWeather(false);
      }
    }
    loadWeather();
  }, []);

  return (
    <div>
      {/* 1. Resilience & Data Status Banner (Android Parity) */}
      <SystemStatusIndicator
        systemState={systemState}
        llmStatus={llmStatus}
        lastVerifiedTimestamp={lastVerifiedTimestamp}
        syncMessage={syncMessage}
        isSyncing={isSyncing}
      />

      {/* 2. Location & Current Situation Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", margin: "1rem 0" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 800, color: "var(--vayu-text)" }}>
            Current Situation
          </h2>
          <div style={{ fontSize: "0.825rem", color: "var(--vayu-muted)" }}>
            Target Geography: <strong>Gwalior District, Madhya Pradesh</strong> • Lat: 26.22°N, Lon: 78.18°E
          </div>
        </div>

        <div style={{ fontSize: "0.75rem", color: "var(--vayu-muted)" }}>
          Source Authority: <strong>{sourceStatus}</strong>
        </div>
      </div>

      {/* 3. Top Metrics Row: Weather + Hazard + Risk + Impact */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1rem",
          marginBottom: "1.25rem",
        }}
      >
        <WeatherCard weather={weather} loading={loadingWeather} />

        <HazardCard
          level={latestCard?.severity || "LOW"}
          score={latestCard?.severity === "HIGH" ? 0.75 : 0.18}
          rainfallMm={weather?.precipitation_mm || 0.0}
        />

        <RiskCard
          level={latestCard?.severity || "LOW"}
          score={latestCard?.severity === "HIGH" ? 0.68 : 0.22}
          hazardScore={latestCard?.severity === "HIGH" ? 0.75 : 0.15}
          exposureScore={0.30}
          vulnerabilityScore={0.25}
          actionPriority={latestCard?.severity === "HIGH" ? "Immediate Evacuation Alert" : "Routine Monitoring"}
        />

        <ImpactCard
          agricultureImpact={latestCard?.verdict === "PROCEED_WITH_CAUTION" ? "Moderate wash-off risk" : "Nominal crop absorption"}
          infrastructureImpact="Low probability of urban waterlogging"
          populationImpact="No immediate localized evacuations required"
        />
      </div>

      {/* 4. Primary Decision Card (Nirnay) */}
      <div style={{ marginBottom: "1.25rem" }}>
        <NirnayCard card={latestCard} />
      </div>

      {/* 5. Primary 7-Stage Intelligence Pipeline Visualization */}
      <PipelineVisualization card={latestCard} />

      {/* 6. Recent Operational Events Stream */}
      {events.length > 0 && (
        <div className="vayu-card" style={{ marginTop: "1rem" }}>
          <div className="vayu-card-header">
            <span className="vayu-card-title">RECENT OPERATIONAL EVENTS</span>
            <span className="vayu-badge vayu-badge-cached">
              {events.length} Streamed
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.775rem" }}>
            {events.slice(0, 5).map((evt) => (
              <div
                key={evt.event_id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  backgroundColor: "var(--vayu-surface-variant)",
                  borderRadius: "8px",
                  border: "1px solid var(--vayu-border)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, color: "var(--vayu-text)" }}>
                    {evt.details?.headline || evt.event_type}
                  </div>
                  <div style={{ fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
                    {evt.geography} • Source: {evt.source_id} ({evt.source_authority})
                  </div>
                </div>

                <div style={{ textAlign: "right", fontSize: "0.7rem", color: "var(--vayu-muted)" }}>
                  <div>ID: {evt.event_id}</div>
                  <div>Seq: #{evt.sequence_number || 1}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
