import { useState, useEffect, useCallback } from 'react';
import client from '../api/client';

export function usePolling<T>(endpoint: string, interval: number = 10000) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const response = await client.get<T>(endpoint);
      setData(response.data);
      setError(null);
    } catch (err) {
      if (err instanceof Error) {
        setError(err);
      } else {
        setError(new Error('An unknown error occurred'));
      }
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    fetchData(); // initial fetch

    const timer = setInterval(() => {
      fetchData();
    }, interval);

    return () => {
      clearInterval(timer);
    };
  }, [fetchData, interval]);

  const manualRefresh = useCallback(() => {
    setLoading(true); // show loading state on manual refresh
    fetchData();
  }, [fetchData]);

  return { data, loading, error, manualRefresh };
}