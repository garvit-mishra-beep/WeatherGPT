// ==============================================================================
// VAYUBODHAK CENTRALIZED API CLIENT
// ==============================================================================

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (typeof window !== "undefined" ? "/api/backend" : "http://127.0.0.1:8000/api/v1");

export interface ApiClientOptions extends RequestInit {
  timeoutMs?: number;
  cacheKey?: string;
  useCacheOnFailure?: boolean;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail: string,
    public isOffline: boolean = false
  ) {
    super(`API Error ${status} (${statusText}): ${detail}`);
    this.name = "ApiError";
  }
}

/**
 * Executes an HTTP request with timeout, error translation, and offline cache fallback.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: ApiClientOptions = {}
): Promise<T> {
  const {
    timeoutMs = 8000,
    cacheKey,
    useCacheOnFailure = true,
    headers = {},
    ...rest
  } = options;

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errorJson = await response.json();
        detail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
      } catch {
        // Fallback to statusText
      }
      throw new ApiError(response.status, response.statusText, detail, false);
    }

    const data: T = await response.json();

    // Cache successful response in localStorage if cacheKey provided
    if (cacheKey && typeof window !== "undefined") {
      try {
        localStorage.setItem(
          `vayu_cache_${cacheKey}`,
          JSON.stringify({
            data,
            timestamp: new Date().toISOString(),
          })
        );
      } catch (e) {
        console.warn("Storage quota exceeded or unavailable:", e);
      }
    }

    return data;
  } catch (err: any) {
    clearTimeout(timeoutId);

    const isOffline =
      err.name === "AbortError" ||
      err.message?.includes("Failed to fetch") ||
      err.message?.includes("NetworkError") ||
      err.message?.includes("ECONNREFUSED");

    // Check cached fallback if offline or request failed
    if (useCacheOnFailure && cacheKey && typeof window !== "undefined") {
      const cached = localStorage.getItem(`vayu_cache_${cacheKey}`);
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          return parsed.data as T;
        } catch {
          // Ignore parse errors
        }
      }
    }

    if (err instanceof ApiError) {
      throw err;
    }

    throw new ApiError(
      isOffline ? 0 : 500,
      isOffline ? "Offline" : "Internal Error",
      isOffline
        ? "Network connection unavailable. Operating in verified offline mode."
        : err.message || "An unexpected error occurred.",
      isOffline
    );
  }
}
