/** React hooks for Context Platform */
import { useState, useEffect, useCallback } from 'react';
import { ContextPlatformClient } from './client';
import type { SearchResult, SearchResponse, Context, Entity } from './types';

let _client: ContextPlatformClient | null = null;

export function useContextPlatform(baseUrl?: string, apiKey?: string) {
  if (!_client) {
    _client = new ContextPlatformClient(baseUrl, apiKey);
  }
  return _client;
}

export function useSearch(query: string, mode: string = 'hybrid') {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const search = useCallback(async (q: string, m?: string) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const client = useContextPlatform();
      const data = await client.search(q, m || mode);
      setResults(data.data);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  return { results, loading, error, search };
}
