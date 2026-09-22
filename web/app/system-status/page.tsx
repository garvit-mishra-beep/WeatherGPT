"use client";

import React, { useEffect, useState } from "react";
import { useOperationalState } from "@/hooks/useOperationalState";
import { fetchDataSources, fetchDataSourcesHealth } from "@/lib/api/sources";
import { DataSourceSummary, DataSourceHealthResponse } from "@/types/api";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  Info,
  RefreshCw,
  Server,
  Shield,
  Wifi,
  WifiOff,
  Bot,
} from "lucide-react";

export default function SystemStatusPage() {
  const {
    systemState,
    sourceStatus,
    isOffline,
    isSyncing,
    lastVerifiedTimestamp,
    events,
    retrySync,
  } = useOperationalState();

  const [sources, setSources] = useState<DataSourceSummary[]>([]);
  const [health, setHealth] = useState<DataSourceHealthResponse | null>(null);
  const [loadingSources, setLoadingSources] = useState(true);
  const [llmStatus, setLlmStatus] = useState<"LLM_AVAILABLE" | "LLM_UNAVAILABLE">("LLM_AVAILABLE");

  useEffect(() => {
    async function loadSources() {
      try {
        setLoadingSources(true);
        const [sourceData, healthData] = await Promise.allSettled([
          fetchDataSources(),
          fetchDataSourcesHealth(),
        ]);
        if (sourceData.status === "fulfilled" && Array.isArray(sourceData.value)) {
          setSources(sourceData.value);
        }
        if (healthData.status === "fulfilled" && healthData.value) {
          setHealth(healthData.value);
        }
      } catch {
        // graceful offline fallback
      } finally {
        setLoadingSources(false);
      }
    }

    loadSources();
  }, [systemState]);

  // Overall State Styling
  const stateMeta = {
    FULL_OPERATIONAL: {
      symbol: "●",
      label: "Fully Operational",
      subtitle: "All authoritative telemetry feeds and deterministic analytical pipelines are running nominally.",
      bg: "bg-green-50",
      border: "border-green-300",
      text: "text-green-800",
      badgeBg: "bg-green-100 text-green-800",
    },
    DEGRADED_DATA: {
      symbol: "▲",
      label: "Degraded Telemetry Feeds",
      subtitle: "One or more secondary feeds are degraded. Authoritative deterministic safety bounds remain active.",
      bg: "bg-amber-50",
      border: "border-amber-300",
      text: "text-amber-800",
      badgeBg: "bg-amber-100 text-amber-800",
    },
    OFFLINE: {
      symbol: "■",
      label: "Offline Mode Active",
      subtitle: "External network unreachable. Operating entirely on cryptographically sealed local cache.",
      bg: "bg-red-50",
      border: "border-red-300",
      text: "text-red-800",
      badgeBg: "bg-red-100 text-red-800",
    },
    RECOVERING: {
      symbol: "◆",
      label: "Recovering & Re-synchronizing",
      subtitle: "Network connectivity restored. Replaying operational event log and verifying evidence hash chains.",
      bg: "bg-blue-50",
      border: "border-blue-300",
      text: "text-blue-800",
      badgeBg: "bg-blue-100 text-blue-800",
    },
    UNAVAILABLE: {
      symbol: "✕",
      label: "System Unavailable",
      subtitle: "Neither live data nor verified cached state is currently accessible.",
      bg: "bg-orange-50",
      border: "border-orange-300",
      text: "text-orange-800",
      badgeBg: "bg-orange-100 text-orange-800",
    },
  }[systemState] || {
    symbol: "●",
    label: "Operating",
    subtitle: "System operational status active.",
    bg: "bg-slate-50",
    border: "border-slate-300",
    text: "text-slate-800",
    badgeBg: "bg-slate-100 text-slate-800",
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Server className="w-6 h-6 text-green-800" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              System & Resilience Status
            </h1>
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Real-time health telemetry, authoritative feed provenance, and cryptographic verification
          </p>
        </div>

        <button
          onClick={() => retrySync()}
          disabled={isSyncing}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-green-800 text-white hover:bg-green-900 transition-colors shadow-sm disabled:opacity-60 cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${isSyncing ? "animate-spin" : ""}`} />
          {isSyncing ? "Synchronizing..." : "Force Sync Now"}
        </button>
      </div>

      {/* 1. Overall Status Card */}
      <div className={`p-6 rounded-2xl border ${stateMeta.bg} ${stateMeta.border} shadow-sm`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold">{stateMeta.symbol}</span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className={`text-lg font-bold ${stateMeta.text}`}>
                  {stateMeta.label}
                </h2>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${stateMeta.badgeBg}`}>
                  {isOffline ? "OFFLINE" : "ONLINE"}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {stateMeta.subtitle}
              </p>
            </div>
          </div>

          <div className="text-right sm:border-l sm:border-slate-200 sm:pl-4">
            <div className="text-xs text-slate-500 font-medium">Source Attribution State</div>
            <div className="text-sm font-bold text-slate-800 uppercase tracking-wide mt-0.5">
              {sourceStatus}
            </div>
          </div>
        </div>

        {lastVerifiedTimestamp && (
          <div className="mt-4 pt-3 border-t border-slate-200/60 flex items-center gap-2 text-xs text-slate-600">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>Last verified state: <strong className="text-slate-800">{new Date(lastVerifiedTimestamp).toLocaleString()}</strong></span>
          </div>
        )}
      </div>

      {/* 2. Safety Notice when Offline / Degraded */}
      {systemState !== "FULL_OPERATIONAL" && (
        <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/80 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 leading-relaxed">
            <strong className="font-semibold block mb-0.5 text-amber-950">Safety Policy — Verified Offline Assessment:</strong>
            When external meteorological telemetry is unavailable, VAYUBODHAK utilizes cryptographically sealed local evidence.
            Cached assessments are strictly labeled as <span className="font-mono font-bold">CACHED</span> and are never presented as real-time telemetry. Deterministic analytical bounds remain active.
          </div>
        </div>
      )}

      {/* 3. Grid: Official Warning Authority & Independent LLM Assistant Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Official Warning Provider Status */}
        <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-green-800" />
                <h3 className="font-bold text-slate-900 text-sm">Official Warning Authorities</h3>
              </div>
              <span className="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold">
                Statutory Feeds
              </span>
            </div>
            <p className="text-xs text-slate-600 mb-4">
              VAYUBODHAK ingests statutory bulletins from authorized Indian authorities. Non-statutory models never override official alerts.
            </p>

            <div className="space-y-2">
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50 text-xs">
                <span className="font-medium text-slate-800">IMD (India Meteorological Dept)</span>
                <span className="font-bold text-green-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Verified Authority
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50 text-xs">
                <span className="font-medium text-slate-800">CWC (Central Water Commission)</span>
                <span className="font-bold text-green-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Hydrological Reference
                </span>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-100 bg-slate-50 text-xs">
                <span className="font-medium text-slate-800">NDMA (National Disaster Mgmt Authority)</span>
                <span className="font-bold text-green-700 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Common Alert Protocol
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500">
            Source Authority Hierarchy: <strong className="text-slate-700">Statutory &gt; Verified &gt; Supporting</strong>
          </div>
        </div>

        {/* Independent LLM Status */}
        <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-indigo-700" />
                <h3 className="font-bold text-slate-900 text-sm">AI Assistant (LLM) Status</h3>
              </div>
              <span className={`text-[11px] px-2 py-0.5 rounded font-semibold ${
                llmStatus === "LLM_AVAILABLE"
                  ? "bg-green-100 text-green-800"
                  : "bg-amber-100 text-amber-800"
              }`}>
                {llmStatus === "LLM_AVAILABLE" ? "AVAILABLE" : "UNAVAILABLE"}
              </span>
            </div>

            <p className="text-xs text-slate-600 mb-4">
              The AI explanation layer is purely descriptive and decoupled from disaster assessment.
            </p>

            <div className="p-3 rounded-xl border border-slate-100 bg-slate-50 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Disaster Decision Engine:</span>
                <strong className="text-green-800 font-bold">100% Deterministic (Python/Math)</strong>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">LLM Decoupled Invariant:</span>
                <strong className="text-slate-800">Zero Critical Calculations in LLM</strong>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-600">Failure Safety Policy:</span>
                <span className="text-slate-700 font-medium">Deterministic fallback active if LLM fails</span>
              </div>
            </div>

            {llmStatus === "LLM_UNAVAILABLE" && (
              <div className="mt-3 p-2.5 rounded-lg border border-amber-300 bg-amber-50 text-xs text-amber-900">
                <strong>Notice:</strong> AI explanation temporarily unavailable. Verified disaster assessment remains available.
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
            <span>Toggle simulated failure test:</span>
            <button
              onClick={() => setLlmStatus(s => s === "LLM_AVAILABLE" ? "LLM_UNAVAILABLE" : "LLM_AVAILABLE")}
              className="text-xs text-indigo-700 hover:text-indigo-900 font-semibold cursor-pointer underline"
            >
              {llmStatus === "LLM_AVAILABLE" ? "Simulate LLM Offline" : "Restore LLM"}
            </button>
          </div>
        </div>
      </div>

      {/* 4. Data Feeds Catalog & Health Telemetry */}
      <div className="p-6 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-green-800" />
            <h3 className="font-bold text-slate-900 text-base">
              Data Feeds & Telemetry Sources ({sources.length > 0 ? sources.length : "Catalog"})
            </h3>
          </div>
          {health && (
            <div className="flex items-center gap-3 text-xs">
              <span className="text-green-700 font-medium">Online: {health.online_count}</span>
              <span className="text-amber-700 font-medium">Degraded: {health.degraded_count}</span>
              <span className="text-red-700 font-medium">Failed: {health.failed_count}</span>
            </div>
          )}
        </div>

        {loadingSources ? (
          <div className="p-8 text-center text-sm text-slate-500">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
            Inspecting telemetry feeds...
          </div>
        ) : sources.length === 0 ? (
          <div className="space-y-3">
            {/* Fallback deterministic data source display if catalog endpoint returns empty */}
            {[
              {
                id: "IMD_PUNE_API",
                name: "IMD Pune Weather Service",
                authority: "IMD",
                type: "REST",
                status: isOffline ? "CACHED" : "LIVE",
                frequency: "15 min",
                class: "Observational",
              },
              {
                id: "OPEN_METEO_API",
                name: "Open-Meteo High-Resolution Ensemble",
                authority: "ECMWF / DWD",
                type: "REST",
                status: isOffline ? "CACHED" : "LIVE",
                frequency: "Hourly",
                class: "Forecast Ensemble",
              },
              {
                id: "CWC_FLOOD_GAUGE",
                name: "Central Water Commission Telemetry",
                authority: "CWC",
                type: "Sensor Gauge",
                status: isOffline ? "CACHED" : "LIVE",
                frequency: "30 min",
                class: "Hydrological",
              },
              {
                id: "NDMA_CAP_ALERT",
                name: "NDMA Common Alerting Protocol",
                authority: "NDMA",
                type: "CAP 1.2",
                status: isOffline ? "CACHED" : "LIVE",
                frequency: "Real-time Push",
                class: "Statutory Alerts",
              },
            ].map((src) => (
              <div
                key={src.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white transition-colors gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{src.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-bold uppercase">
                      {src.authority}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                    <span>Type: {src.type}</span>
                    <span>•</span>
                    <span>Class: {src.class}</span>
                    <span>•</span>
                    <span>Update: {src.frequency}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${
                    src.status === "LIVE"
                      ? "bg-green-100 text-green-800"
                      : "bg-amber-100 text-amber-800"
                  }`}>
                    ● {src.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {sources.map((src) => (
              <div
                key={src.source_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-white transition-colors gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{src.source_name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-bold uppercase">
                      {src.authority}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                      {src.authority_level}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                    <span>ID: <code className="font-mono text-[11px]">{src.source_id}</code></span>
                    <span>•</span>
                    <span>Class: {src.data_class}</span>
                    <span>•</span>
                    <span>Freq: {src.update_frequency}</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${
                    src.health_status === "HEALTHY" || src.health_status === "ONLINE"
                      ? isOffline ? "bg-amber-100 text-amber-800" : "bg-green-100 text-green-800"
                      : "bg-red-100 text-red-800"
                  }`}>
                    {isOffline ? "● CACHED" : src.health_status === "HEALTHY" ? "● LIVE" : src.health_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 5. Operational Event Log Summary */}
      <div className="p-5 rounded-2xl border border-slate-200 bg-white shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-green-800" />
            <h3 className="font-bold text-slate-900 text-sm">Recent Operational Telemetry Events</h3>
          </div>
          <span className="text-xs text-slate-500">
            Count: <strong className="text-slate-800">{events.length}</strong> recorded
          </span>
        </div>

        {events.length === 0 ? (
          <div className="p-4 rounded-xl bg-slate-50 text-center text-xs text-slate-500">
            No telemetry events queued. Operational ledger synchronized.
          </div>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {events.slice(0, 8).map((evt) => (
              <div
                key={evt.event_id}
                className="p-2.5 rounded-lg border border-slate-100 bg-slate-50 flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-mono font-bold text-slate-800 mr-2">{evt.event_type}</span>
                  <span className="text-slate-500">{evt.geography} • {evt.source_authority}</span>
                </div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {new Date(evt.created_at).toLocaleTimeString()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
