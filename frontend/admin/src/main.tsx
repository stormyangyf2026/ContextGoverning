import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';

const API_BASE = '/api/v1';

// ── Types ──────────────────────────────────────────────────
interface Stat { total_contexts: number; total_entities: number; total_relations: number; confidence_distribution: Record<string,number> }
interface Context { id: string; context_id: string; title: string; domain: string; confidence_level: string; lifecycle_status: string; created_at: string }
interface Entity { id: string; name: string; type: string; domain?: string }
interface User { id: string; username: string; email: string; role: string; full_name: string }

// ── API helpers ────────────────────────────────────────────
async function api<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Pages ──────────────────────────────────────────────────

function Dashboard() {
  const [stats, setStats] = useState<Stat | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => { api<Stat>('/metrics/overview').then(setStats).catch(e => setErr(e.message)); }, []);

  if (err) return <div className="error">{err}</div>;
  if (!stats) return <div className="loading">Loading...</div>;

  return (
    <div>
      <h2 style={{marginBottom:24}}>Dashboard</h2>
      <div className="stat-grid">
        <div className="stat-card"><div className="stat-value">{stats.total_contexts}</div><div className="stat-label">Total Contexts</div></div>
        <div className="stat-card"><div className="stat-value">{stats.total_entities}</div><div className="stat-label">Total Entities</div></div>
        <div className="stat-card"><div className="stat-value">{stats.total_relations}</div><div className="stat-label">Total Relations</div></div>
        <div className="stat-card"><div className="stat-value">{Object.keys(stats.confidence_distribution||{}).length}</div><div className="stat-label">Confidence Levels</div></div>
      </div>
      <div className="card">
        <h3 style={{marginBottom:12}}>Confidence Distribution</h3>
        {Object.entries(stats.confidence_distribution||{}).map(([k,v]) => (
          <span key={k} style={{marginRight:16,fontSize:14}}>
            <span className={`badge ${k>='L3'?'badge-success':k>='L2'?'badge-info':'badge-warning'}`}>{k}</span> {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function Contexts() {
  const [items, setItems] = useState<Context[]>([]);
  const [err, setErr] = useState('');
  const [domain, setDomain] = useState('');
  const [search, setSearch] = useState('');

  const load = () => {
    const params = new URLSearchParams();
    if (domain) params.set('domain', domain);
    if (search) params.set('search', search);
    api<Context[]>(`/contexts?${params}`).then(setItems).catch(e => setErr(e.message));
  };

  useEffect(load, []);

  return (
    <div>
      <h2 style={{marginBottom:16}}>Contexts</h2>
      {err && <div className="error">{err}</div>}
      <div className="flex mb12">
        <select value={domain} onChange={e => {setDomain(e.target.value); setTimeout(load,0)}}>
          <option value="">All domains</option>
          <option value="customer">Customer</option>
          <option value="project">Project</option>
          <option value="operations">Operations</option>
          <option value="external">External</option>
        </select>
        <input placeholder="Search..." value={search} onChange={e => {setSearch(e.target.value); setTimeout(load,500)}} />
        <button className="btn-primary" onClick={load}>Refresh</button>
      </div>
      <div className="card" style={{padding:0,overflow:'auto'}}>
        <table>
          <thead><tr><th>Context ID</th><th>Title</th><th>Domain</th><th>Confidence</th><th>Status</th><th>Created</th></tr></thead>
          <tbody>
            {items.map(c => (
              <tr key={c.id}>
                <td style={{fontFamily:'monospace',fontSize:12}}>{c.context_id}</td>
                <td>{c.title}</td>
                <td><span className="badge badge-info">{c.domain}</span></td>
                <td><span className={`badge ${c.confidence_level>='L3'?'badge-success':'badge-warning'}`}>{c.confidence_level}</span></td>
                <td><span className={`badge ${c.lifecycle_status==='active'?'badge-success':c.lifecycle_status==='pending_review'?'badge-warning':'badge-danger'}`}>{c.lifecycle_status}</span></td>
                <td style={{fontSize:12,color:'#999'}}>{c.created_at?.slice(0,10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EntitiesView() {
  const [items, setItems] = useState<Entity[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => { api<Entity[]>('/entities').then(setItems).catch(e => setErr(e.message)); }, []);

  return (
    <div>
      <h2 style={{marginBottom:16}}>Entities</h2>
      {err && <div className="error">{err}</div>}
      <div className="card" style={{padding:0,overflow:'auto'}}>
        <table>
          <thead><tr><th>Name</th><th>Type</th><th>Domain</th></tr></thead>
          <tbody>{items.map(e => (
            <tr key={e.id}><td>{e.name}</td><td><span className="badge badge-info">{e.type}</span></td><td>{e.domain||'-'}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function Users() {
  const [items, setItems] = useState<User[]>([]);
  const [err, setErr] = useState('');

  useEffect(() => { api<User[]>('/users').then(setItems).catch(e => setErr(e.message)); }, []);

  return (
    <div>
      <h2 style={{marginBottom:16}}>Users</h2>
      {err && <div className="error">{err}</div>}
      <div className="card" style={{padding:0,overflow:'auto'}}>
        <table>
          <thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Full Name</th></tr></thead>
          <tbody>{items.map(u => (
            <tr key={u.id}><td>{u.username}</td><td>{u.email}</td><td><span className="badge badge-info">{u.role}</span></td><td>{u.full_name}</td></tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}

function Settings() {
  return (
    <div>
      <h2 style={{marginBottom:16}}>System Settings</h2>
      <div className="card">
        <h3 style={{marginBottom:12}}>Configuration</h3>
        <p style={{color:'#999'}}>System configuration management interface. Use the API endpoints at /api/v1/config to manage settings.</p>
      </div>
      <div className="card">
        <h3 style={{marginBottom:12}}>Available Config Sections</h3>
        <ul style={{paddingLeft:20}}>
          {['confidence_engine','ingestion','search','llm','security','lifecycle','notification','export','integration','embedding'].map(s => (
            <li key={s} style={{marginBottom:8}}><code>{s}</code></li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// ── App ─────────────────────────────────────────────────────

function App() {
  const [page, setPage] = useState('dashboard');

  const nav = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'contexts', label: 'Contexts' },
    { id: 'entities', label: 'Entities' },
    { id: 'users', label: 'Users' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>Context Platform</h1>
        <nav>
          {nav.map(n => (
            <a key={n.id} href="#" className={page===n.id?'active':''}
               onClick={e => {e.preventDefault(); setPage(n.id)}}>{n.label}</a>
          ))}
        </nav>
      </aside>
      <main className="main">
        {page==='dashboard' && <Dashboard />}
        {page==='contexts' && <Contexts />}
        {page==='entities' && <EntitiesView />}
        {page==='users' && <Users />}
        {page==='settings' && <Settings />}
      </main>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
