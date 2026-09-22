"use client";

import React from "react";
import { WeatherObservation } from "@/types/api";

interface WeatherCardProps {
  weather: WeatherObservation | null;
  loading?: boolean;
}

export const WeatherCard: React.FC<WeatherCardProps> = ({ weather, loading }) => {
  if (loading || !weather) {
    return (
      <div className="vayu-card" style={{ height: "100%" }}>
        <div className="vayu-card-header">
          <span className="vayu-card-title">CURRENT WEATHER</span>
          <span className="vayu-badge vayu-badge-cached">SYNCING</span>
        </div>
        <div style={{ color: "var(--vayu-muted)", fontSize: "0.85rem", padding: "1.5rem 0", textAlign: "center" }}>
          Retrieving surface meteorological observations...
        </div>
      </div>
    );
  }

  return (
    <div className="vayu-card" style={{ height: "100%" }}>
      <div className="vayu-card-header">
        <span className="vayu-card-title">CURRENT WEATHER</span>
        <span className={`vayu-badge vayu-badge-${weather.provenance.quality.toLowerCase() === "verified" ? "live" : "cached"}`}>
          {weather.provenance.provider} ({weather.provenance.authority})
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: "12px", margin: "0.5rem 0" }}>
        <span style={{ fontSize: "2.25rem", fontWeight: 800, color: "var(--vayu-text)" }}>
          {weather.temperature_c.toFixed(1)}°C
        </span>
        <span style={{ fontSize: "0.85rem", color: "var(--vayu-muted)", fontWeight: 500 }}>
          Feels like {weather.feels_like_c.toFixed(1)}°C
        </span>
      </div>

      <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--vayu-primary)", marginBottom: "1rem" }}>
        {weather.weather_condition || "Clear Sky"}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "10px",
          borderTop: "1px solid var(--vayu-border)",
          paddingTop: "0.75rem",
          fontSize: "0.785rem",
        }}
      >
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Rainfall:</span>{" "}
          <strong style={{ color: "var(--vayu-accent-rain)" }}>{weather.precipitation_mm.toFixed(1)} mm</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Wind:</span>{" "}
          <strong style={{ color: "var(--vayu-accent-wind)" }}>{weather.wind_speed_kmh.toFixed(1)} km/h</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Humidity:</span>{" "}
          <strong>{weather.relative_humidity_pct.toFixed(0)}%</strong>
        </div>
        <div>
          <span style={{ color: "var(--vayu-muted)" }}>Pressure:</span>{" "}
          <strong>{weather.surface_pressure_hpa.toFixed(0)} hPa</strong>
        </div>
      </div>
    </div>
  );
};
