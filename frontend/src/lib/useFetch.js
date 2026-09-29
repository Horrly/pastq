import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

/**
 * Load an API path; returns { data, error, loading, reload, setData }. Pass null to skip.
 * `loading` is only true for the first load, so background refreshes don't flash a spinner.
 */
export function useFetch(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(Boolean(path));
  const hasData = useRef(false);

  const reload = useCallback(async () => {
    if (!path) return;
    if (!hasData.current) setLoading(true);
    try {
      setData(await api(path));
      hasData.current = true;
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    hasData.current = false;
    setData(null);
    reload();
  }, [reload]);

  return { data, error, loading, reload, setData };
}
