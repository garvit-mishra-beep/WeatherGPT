"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  NirnayCard,
  OperationalEvent,
  SystemOperationalState,
  DataSourceStatus,
  LlmStatus,
} from "@/types/api";
import { fetchOperationalState } from "@/lib/api/sync";

export interface OperationalHookState {
  systemState: SystemOperationalState;
  sourceStatus: DataSourceStatus;
  llmStatus: LlmStatus;
  isSyncing: boolean;
  isOffline: boolean;
  syncMessage: string | null;
  lastVerifiedTimestamp: string | null;
  latestRevision: number;
  latestSequence: number;
  events: OperationalEvent[];
  latestCard: NirnayCard | null;
  error: string | null;
  refresh: () => Promise<void>;
  retrySync: () => Promise<void>;
}

export function useOperationalState(district: string = "Gwalior District"): OperationalHookState {
  const [systemState, setSystemState] = useState<SystemOperationalState>("FULL_OPERATIONAL");
  const [sourceStatus, setSourceStatus] = useState<DataSourceStatus>("LIVE");
  const [llmStatus, setLlmStatus] = useState<LlmStatus>("LLM_AVAILABLE");
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [lastVerifiedTimestamp, setLastVerifiedTimestamp] = useState<string | null>(null);
  const [latestRevision, setLatestRevision] = useState<number>(0);
  const [latestSequence, setLatestSequence] = useState<number>(0);
  const [events, setEvents] = useState<OperationalEvent[]>([]);
  const [latestCard, setLatestCard] = useState<NirnayCard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cursorRef = useRef<number>(0);
  const revRef = useRef<number>(0);

  const sync = useCallback(async () => {
    setIsSyncing(true);
    setSyncMessage("Synchronizing operational intelligence...");

    try {
      const resp = await fetchOperationalState(cursorRef.current, revRef.current, district);

      cursorRef.current = resp.latest_sequence;
      revRef.current = resp.latest_revision;

      setLatestSequence(resp.latest_sequence);
      setLatestRevision(resp.latest_revision);
      setSourceStatus((resp.source_status as DataSourceStatus) || "LIVE");

      if (resp.latest_nirnay_card) {
        setLatestCard(resp.latest_nirnay_card);
      }

      if (resp.events && resp.events.length > 0) {
        setEvents((prev) => {
          const ids = new Set(prev.map((e) => e.event_id));
          const newUnique = resp.events.filter((e) => !ids.has(e.event_id));
          return [...newUnique, ...prev].slice(0, 100);
        });
      }

      const nowStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      setLastVerifiedTimestamp(nowStr);

      setSystemState("FULL_OPERATIONAL");
      setError(null);
      setSyncMessage(null);
    } catch (err: any) {
      if (err.isOffline || !navigator.onLine) {
        setSystemState("OFFLINE");
        setSyncMessage("Operating in offline resilience mode");
      } else {
        setSystemState("DEGRADED_DATA");
        setSyncMessage("Operating with cached operational state");
      }

      setError("Live updates temporarily suspended. Displaying verified local assessment.");
    } finally {
      setIsSyncing(false);
    }
  }, [district]);

  useEffect(() => {
    sync();
    const interval = setInterval(sync, 6000);
    return () => clearInterval(interval);
  }, [sync]);

  // Listen for browser online/offline events for immediate recovery
  useEffect(() => {
    const handleOnline = () => {
      setSystemState("RECOVERING");
      setSyncMessage("Network reconnected. Re-verifying operational sync...");
      sync();
    };

    const handleOffline = () => {
      setSystemState("OFFLINE");
      setSyncMessage("Network connection lost. Serving last verified cache.");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [sync]);

  return {
    systemState,
    sourceStatus,
    llmStatus,
    isSyncing,
    isOffline: systemState === "OFFLINE",
    syncMessage,
    lastVerifiedTimestamp,
    latestRevision,
    latestSequence,
    events,
    latestCard,
    error,
    refresh: sync,
    retrySync: sync,
  };
}
