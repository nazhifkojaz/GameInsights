import { useState, useEffect } from "react";
import { apiClient, ApiRequestError } from "../api/client";
import type { Game, PlayerHistory } from "../types/api";

interface GameDataState {
  game: Game | null;
  playerHistory: PlayerHistory | null;
  loading: boolean;
  longWait: boolean;
  error: ApiRequestError | null;
}

export function useGameData(appid: string): GameDataState {
  const [state, setState] = useState<GameDataState>({
    game: null,
    playerHistory: null,
    loading: true,
    longWait: false,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    const longWaitTimer = setTimeout(() => {
      if (!cancelled) setState((s) => ({ ...s, longWait: true }));
    }, 5000);

    async function fetchData() {
      try {
        const [game, players] = await Promise.all([
          apiClient.getGame(appid),
          apiClient.getActivePlayers(appid).catch(() => null),
        ]);

        if (!cancelled) {
          setState({
            game,
            playerHistory: players?.[0] ?? null,
            loading: false,
            longWait: false,
            error: null,
          });
        }
      } catch (err) {
        if (!cancelled) {
          const error =
            err instanceof ApiRequestError
              ? err
              : new ApiRequestError(0, {
                  error: "unknown",
                  message: err instanceof Error ? err.message : "An unexpected error occurred",
                });
          setState({
            game: null,
            playerHistory: null,
            loading: false,
            longWait: false,
            error,
          });
        }
      }
    }

    fetchData();

    return () => {
      cancelled = true;
      clearTimeout(longWaitTimer);
    };
  }, [appid]);

  return state;
}
