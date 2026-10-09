"use client";
import { useCallback, useEffect, useState } from "react";

type State<T> = { fetcher: unknown; nonce: number; data?: T; error?: Error };

/**
 * Runs `fetcher` whenever it changes (wrap it in useCallback) and exposes loading / error / reload.
 * A cancelled flag stops a slow old response from overwriting a newer one.
 */
export function useApi<T>(fetcher: () => Promise<T>) {
  const [state, setState] = useState<State<T>>({ fetcher: null, nonce: -1 });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetcher().then(
      (data) => { if (!cancelled) setState({ fetcher, nonce, data }); },
      (error: Error) => { if (!cancelled) setState({ fetcher, nonce, error }); },
    );
    return () => { cancelled = true; };
  }, [fetcher, nonce]);

  const loading = state.fetcher !== fetcher || state.nonce !== nonce;
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data: loading ? undefined : state.data, error: loading ? undefined : state.error, loading, reload };
}
