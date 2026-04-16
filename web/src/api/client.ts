import type { SearchResult, Game, PlayerHistory, HealthCheck } from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const DEFAULT_TIMEOUT = 45_000; // 45 seconds — matches the bot's httpx timeout

export class ApiRequestError extends Error {
  status: number;
  body: { error: string; message: string; identifier?: string; source?: string };

  constructor(
    status: number,
    body: ApiRequestError["body"],
  ) {
    super(body.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.body = body;
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  private async fetch<T>(
    path: string,
    options?: { signal?: AbortSignal },
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(new DOMException("timeout", "AbortError")),
      DEFAULT_TIMEOUT,
    );

    // Link external signal (for search/component cancellation)
    let onExternalAbort: (() => void) | undefined;
    if (options?.signal) {
      if (options.signal.aborted) {
        controller.abort((options.signal as { reason?: unknown }).reason);
      }
      onExternalAbort = () =>
        controller.abort((options.signal as { reason?: unknown }).reason);
      options.signal.addEventListener("abort", onExternalAbort, { once: true });
    }

    try {
      const response = await globalThis.fetch(`${this.baseUrl}${path}`, {
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          error: "unknown",
          message: response.statusText,
        }));
        throw new ApiRequestError(response.status, error);
      }

      return (await response.json()) as T;
    } catch (err) {
      if (
        err instanceof DOMException &&
        err.name === "AbortError" &&
        controller.signal.reason instanceof DOMException &&
        controller.signal.reason.message === "timeout"
      ) {
        throw new ApiRequestError(408, {
          error: "timeout",
          message: "Request timed out",
        });
      }
      throw err;
    } finally {
      clearTimeout(timeoutId);
      if (options?.signal && onExternalAbort) {
        options.signal.removeEventListener("abort", onExternalAbort);
      }
    }
  }

  async searchGames(
    query: string,
    topN = 5,
    signal?: AbortSignal,
  ): Promise<SearchResult[]> {
    const params = new URLSearchParams({
      q: query,
      top_n: String(topN),
    });
    return this.fetch<SearchResult[]>(`/games/search?${params}`, { signal });
  }

  async getGame(appid: string, signal?: AbortSignal): Promise<Game> {
    return this.fetch<Game>(`/games/${encodeURIComponent(appid)}`, { signal });
  }

  async getActivePlayers(
    appid: string,
    signal?: AbortSignal,
  ): Promise<PlayerHistory[]> {
    return this.fetch<PlayerHistory[]>(
      `/games/${encodeURIComponent(appid)}/active-players`,
      { signal },
    );
  }

  async healthCheck(): Promise<HealthCheck> {
    return this.fetch<HealthCheck>("/health");
  }
}

export const apiClient = new ApiClient();
