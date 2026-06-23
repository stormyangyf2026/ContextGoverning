/** TypeScript client for Context Platform API */
import type { Context, Entity, SearchResponse, Workspace } from './types';

export class ContextPlatformClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(baseUrl: string = 'http://localhost:8000', apiKey?: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { 'Content-Type': 'application/json' };
    if (this.apiKey) h['X-API-Key'] = this.apiKey;
    return h;
  }

  private async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  private async post<T>(path: string, data: unknown): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST', headers: this.headers(), body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  // Contexts
  async createContext(data: Partial<Context>): Promise<Context> {
    return this.post('/api/v1/external/contexts', data);
  }
  async getContext(contextId: string): Promise<Context> {
    return this.get(`/api/v1/external/contexts/${contextId}`);
  }
  async listContexts(domain?: string): Promise<Context[]> {
    const q = domain ? `?domain=${domain}` : '';
    return this.get(`/api/v1/external/contexts${q}`);
  }
  async updateContext(contextId: string, data: Partial<Context>): Promise<Context> {
    const res = await fetch(`${this.baseUrl}/api/v1/external/contexts/${contextId}`, {
      method: 'PUT', headers: this.headers(), body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }
  async deleteContext(contextId: string): Promise<void> {
    await fetch(`${this.baseUrl}/api/v1/external/contexts/${contextId}`, {
      method: 'DELETE', headers: this.headers(),
    });
  }

  // Search
  async search(query: string, mode: string = 'hybrid', filters?: Record<string, unknown>): Promise<SearchResponse> {
    return this.post('/api/v1/external/search', { query, mode, filters });
  }

  // Entities
  async listEntities(): Promise<Entity[]> {
    return this.get('/api/v1/external/entities');
  }
  async createEntity(name: string, type: string = 'other'): Promise<Entity> {
    return this.post('/api/v1/external/entities', { name, type });
  }
  async getEntity(entityId: string): Promise<Entity> {
    return this.get(`/api/v1/external/entities/${entityId}`);
  }
  async getEntityGraph(entityId: string, depth: number = 2): Promise<unknown> {
    return this.get(`/api/v1/external/entities/${entityId}/graph?depth=${depth}`);
  }

  // Workspaces
  async listWorkspaces(): Promise<Workspace[]> {
    return this.get('/api/v1/external/workspaces');
  }

  // Metrics
  async getOverview(): Promise<unknown> {
    return this.get('/api/v1/metrics/overview');
  }
}
