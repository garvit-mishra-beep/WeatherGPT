import { apiRequest } from "./client";
import { OperationalSyncResponse } from "@/types/api";

export async function fetchOperationalState(
  cursorSeq: number = 0,
  lastSyncedRevision: number = 0,
  district?: string
): Promise<OperationalSyncResponse> {
  const params = new URLSearchParams({
    cursor_seq: cursorSeq.toString(),
    last_synced_revision: lastSyncedRevision.toString(),
    limit: "50",
  });
  if (district) {
    params.append("district", district);
  }

  return apiRequest<OperationalSyncResponse>(`/sync/operational-state?${params.toString()}`, {
    cacheKey: "operational_sync_state",
    timeoutMs: 6000,
  });
}
