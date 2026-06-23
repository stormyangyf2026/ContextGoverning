/** Context Platform TypeScript SDK — Main entry point */
export { ContextPlatformClient } from './client';
export type { Context, Entity, Relation, SearchResult, SearchResponse, Workspace } from './types';
export { useSearch, useContextPlatform } from './hooks';
export { EventHandler } from './events';
