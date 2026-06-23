import React, { useState } from 'react';
import ReactDOM from 'react-dom/client';

const API_BASE = '/api/v1';

interface SearchResult {
  id: string; context_id: string; title: string; content: string;
  domain: string; confidence_level: string; confidence_score: number;
  lifecycle_status: string; created_at: string;
  consumption_guidance?: { can_agent_reference: boolean; usage_advice: string; reference_hint?: string };
}
interface GraphNode { id: string; name: string; type: string; is_center: boolean }
interface GraphEdge { source_id: string; target_id: string; type: string }
interface GraphData { center_entity: any; nodes: GraphNode[]; edges: GraphEdge[] }
interface EntityItem { id: string; name: string; type: string }

async function api<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

function SearchPage() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [meta, setMeta] = useState<any>(null);

  const modes = ['hybrid', 'exact', 'semantic', 'relation', 'timeline', 'contradiction'];

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true); setError('');
    try {
      const data = await api<any>('/search', {
        method: 'POST',
        body: JSON.stringify({ query, mode, page: 1, page_size: 20, include_confidence_detail: true }),
      });
      setResults(data.data || []);
      setMeta(data.meta);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="container">
      <h2 style={{marginBottom:16}}>Search Context</h2>
      <div className="search-bar">
        <input placeholder="Search contexts, entities, relationships..."
               value={query} onChange={e => setQuery(e.target.value)}
               onKeyDown={e => e.key==='Enter' && search()} />
        <button onClick={search}>Search</button>
      </div>
      <div className="mode-bar">
        {modes.map(m => (
          <button key={m} className={mode===m?'active':''} onClick={() => setMode(m)}>{m}</button>
        ))}
      </div>
      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Searching...</div>}
      {meta && <div style={{marginBottom:12,color:'#999',fontSize:13}}>{meta.total} results in {meta.query_time_ms}ms</div>}
      {!loading && results.length===0 && query && <div className="empty">No results found</div>}
      <div className="card" style={{padding:0}}>
        {results.map(r => (
          <div key={r.id} className="result-item">
            <div className="result-title">{r.title}</div>
            <div className="result-content">{r.content?.slice(0,200)}{r.content?.length>200?'...':''}</div>
            <div className="result-meta">
              <span className="badge bg-blue">{r.domain}</span>
              <span className={`badge ${r.confidence_level>='L3'?'bg-green':'bg-orange'}`}>{r.confidence_level}</span>
              <span className="badge bg-blue">{r.lifecycle_status}</span>
              <span style={{fontSize:12,color:'#999'}}>{r.created_at?.slice(0,10)}</span>
              {r.consumption_guidance?.can_agent_reference !== undefined && (
                <span className={`badge ${r.consumption_guidance.can_agent_reference?'bg-green':'bg-red'}`}>
                  {r.consumption_guidance.can_agent_reference ? 'Can reference' : 'Do not reference'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ContextDetail() {
  const [ctxId, setCtxId] = useState('');
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState('');

  const load = async () => {
    if (!ctxId.trim()) return;
    try {
      const data = await api<any>(`/contexts/${ctxId}`);
      setDetail(data); setError('');
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div className="container">
      <h2 style={{marginBottom:16}}>Context Detail</h2>
      <div className="flex mb12">
        <input placeholder="Context ID" value={ctxId} onChange={e => setCtxId(e.target.value)}
               style={{flex:1}} />
        <button onClick={load}>Load</button>
      </div>
      {error && <div className="error">{error}</div>}
      {detail && (
        <div className="card">
          <h3>{detail.title}</h3>
          <div className="result-meta" style={{margin:'8px 0 12px'}}>
            <span className="badge bg-blue">{detail.domain}</span>
            <span className={`badge ${detail.confidence_level>='L3'?'bg-green':'bg-orange'}`}>{detail.confidence_level}</span>
            <span className="badge bg-blue">{detail.lifecycle_status}</span>
          </div>
          <p style={{lineHeight:1.8,color:'#444'}}>{detail.content}</p>
          <div style={{marginTop:12,color:'#999',fontSize:12}}>
            Created by {detail.created_by} at {detail.created_at}
          </div>
        </div>
      )}
    </div>
  );
}

function GraphPage() {
  const [entityName, setEntityName] = useState('');
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [error, setError] = useState('');

  // Use entities list to find entity IDs
  const [entities, setEntities] = useState<EntityItem[]>([]);

  React.useEffect(() => {
    api<EntityItem[]>('/entities?limit=100').then(setEntities).catch(() => {});
  }, []);

  const loadGraph = async () => {
    if (!entityName.trim()) return;
    const entity = entities.find(e => e.name.includes(entityName) || e.id === entityName);
    const id = entity?.id || entityName;
    try {
      const data = await api<GraphData>(`/entities/${id}/graph?depth=2`);
      setGraph(data); setError('');
    } catch (e: any) { setError(e.message); }
  };

  return (
    <div className="container">
      <h2 style={{marginBottom:16}}>Knowledge Graph</h2>
      <div className="flex mb12">
        <input placeholder="Entity name or ID" value={entityName} onChange={e => setEntityName(e.target.value)}
               style={{flex:1}} />
        <button onClick={loadGraph}>Explore</button>
      </div>
      {error && <div className="error">{error}</div>}
      {entities.length > 0 && (
        <div style={{marginBottom:16}}>
          <span style={{fontSize:13,color:'#999'}}>Available entities: </span>
          {entities.slice(0,10).map(e => (
            <span key={e.id} className="badge bg-blue" style={{marginRight:4,cursor:'pointer'}}
                  onClick={() => {setEntityName(e.name); setTimeout(loadGraph,0)}}>{e.name}</span>
          ))}
        </div>
      )}
      {graph && (
        <div>
          <div className="card">
            <h3>Center: {graph.center_entity?.name} ({graph.center_entity?.type})</h3>
            <div style={{marginTop:8,fontSize:13,color:'#999'}}>{graph.nodes.length} nodes, {graph.edges.length} edges</div>
          </div>
          <div className="card">
            <h3 style={{marginBottom:12}}>Nodes ({graph.nodes.length})</h3>
            <div style={{display:'flex',flexWrap:'wrap',gap:8}}>
              {graph.nodes.map(n => (
                <span key={n.id} className={`badge ${n.is_center?'bg-green':'bg-blue'}`}
                      title={n.id}>{n.name} ({n.type})</span>
              ))}
            </div>
          </div>
          {graph.edges.length > 0 && (
            <div className="card">
              <h3 style={{marginBottom:12}}>Relations ({graph.edges.length})</h3>
              {graph.edges.map((e,i) => (
                <div key={i} style={{fontSize:13,marginBottom:4}}>
                  <span style={{color:'#999',fontFamily:'monospace'}}>{e.source_id?.slice(0,8)}</span>
                  <span style={{margin:'0 8px'}}>-- {e.type} --&gt;</span>
                  <span style={{color:'#999',fontFamily:'monospace'}}>{e.target_id?.slice(0,8)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MetricsView() {
  const [overview, setOverview] = useState<any>(null);
  const [err, setErr] = useState('');

  React.useEffect(() => {
    api<any>('/metrics/overview').then(setOverview).catch(e => setErr(e.message));
  }, []);

  return (
    <div className="container">
      <h2 style={{marginBottom:16}}>Platform Metrics</h2>
      {err && <div className="error">{err}</div>}
      {overview && (
        <div className="card">
          <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:16,marginBottom:16}}>
            <div><div style={{fontSize:28,fontWeight:700}}>{overview.total_contexts}</div><div style={{fontSize:12,color:'#999'}}>Contexts</div></div>
            <div><div style={{fontSize:28,fontWeight:700}}>{overview.total_entities}</div><div style={{fontSize:12,color:'#999'}}>Entities</div></div>
            <div><div style={{fontSize:28,fontWeight:700}}>{overview.total_relations}</div><div style={{fontSize:12,color:'#999'}}>Relations</div></div>
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [page, setPage] = useState('search');
  const nav = [
    { id: 'search', label: 'Search' },
    { id: 'detail', label: 'Detail' },
    { id: 'graph', label: 'Graph' },
    { id: 'metrics', label: 'Metrics' },
  ];

  return (
    <div>
      <header className="header">
        <h1>Context Platform</h1>
        <nav>
          {nav.map(n => (
            <a key={n.id} href="#" className={page===n.id?'active':''}
               onClick={e => {e.preventDefault(); setPage(n.id)}}>{n.label}</a>
          ))}
        </nav>
      </header>
      {page==='search' && <SearchPage />}
      {page==='detail' && <ContextDetail />}
      {page==='graph' && <GraphPage />}
      {page==='metrics' && <MetricsView />}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
