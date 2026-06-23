/** TypeScript type definitions for Context Platform SDK */

export interface Context {
  id: string;
  context_id: string;
  title: string;
  content: string;
  domain: string;
  confidence_level: string;
  confidence_score: number;
  lifecycle_status: string;
  created_by: string;
  created_at?: string;
  version?: number;
  is_immutable?: boolean;
}

export interface Entity {
  id: string;
  name: string;
  type: string;
  domain?: string;
  aliases?: string[];
}

export interface Relation {
  id: string;
  source_id: string;
  target_id: string;
  type: string;
  direction?: string;
}

export interface SearchResult {
  id: string;
  context_id: string;
  title: string;
  content: string;
  domain: string;
  confidence_level: string;
  confidence_score: number;
  lifecycle_status: string;
  created_at?: string;
  score?: number;
  consumption_guidance?: {
    can_agent_reference: boolean;
    usage_advice: string;
    reference_hint?: string;
  };
}

export interface SearchResponse {
  data: SearchResult[];
  meta: {
    total: number;
    page: number;
    page_size: number;
    query_time_ms: number;
    mode: string;
  };
}

export interface Workspace {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
}
