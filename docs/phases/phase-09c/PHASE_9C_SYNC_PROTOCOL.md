# PHASE 9C — INCREMENTAL SYNCHRONIZATION PROTOCOL

## 1. Protocol Overview
The VAYUBODHAK mobile synchronization protocol provides efficient, bandwidth-optimized synchronization between the central backend and Android field clients.

---

## 2. Cursor Handshake Flow

```mermaid
sequenceDiagram
    autonumber
    participant Android as Android Mobile App (Room DB)
    participant Server as FastAPI Sync Endpoint (/api/v1/sync)
    participant Repo as Event & Pipeline Repository

    Note over Android: Client holds cursor_seq=120, revision=4
    Android->>Server: GET /api/v1/sync/operational-state?cursor_seq=120&last_synced_revision=4
    Server->>Repo: Query events WHERE sequence_number > 120
    Repo-->>Server: Return events [121, 122, 123] + latest NirnayCard (rev=5)
    Server-->>Android: OperationalSyncResponse (latest_seq=123, rev=5, events, card)
    Note over Android: Room DB executes atomic transaction: updates cursor to 123, updates NirnayCard to rev 5
    Note over Android: UI re-renders with fresh badge and timestamp
```

---

## 3. Disconnect & Offline Recovery

When mobile device loses network connectivity:
1. Client detects network offline state via `ConnectivityManager`.
2. UI displays local cached NirnayCard with badge `CACHED` and header:
   `"OFFLINE — LAST VERIFIED [2026-09-21 14:30 UTC]"`.
3. Cached data is explicitly labeled; never masquerades as live data.
4. When connectivity returns:
   Client resumes handshake from `cursor_seq = 120`, avoiding full dataset re-download.
