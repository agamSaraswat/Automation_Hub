import { FormEvent, useEffect, useState } from "react";

import { apiClient } from "../api/client";
import { NetworkNode, NetworkStatsResponse } from "../types/api";

const EMPTY_NODE: NetworkNode = {
  id: "",
  name: "",
  company: "",
  role: "",
  linkedin_url: "",
  connection_strength: 3,
  last_contact_date: new Date().toISOString().slice(0, 10),
  mutual_connections: [],
  notes: "",
};

export function NetworkPage() {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [stats, setStats] = useState<NetworkStatsResponse | null>(null);
  const [pathCompany, setPathCompany] = useState("");
  const [paths, setPaths] = useState<NetworkNode[][]>([]);
  const [form, setForm] = useState<NetworkNode>(EMPTY_NODE);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      const [nodesResp, statsResp] = await Promise.all([
        apiClient.getNetworkNodes(),
        apiClient.getNetworkStats(),
      ]);
      setNodes(nodesResp.items);
      setStats(statsResp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load network");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function submitNode(e: FormEvent) {
    e.preventDefault();
    const ok = window.confirm("Add this contact to the network graph?");
    if (!ok) return;
    try {
      await apiClient.addNetworkNode(form);
      setForm(EMPTY_NODE);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add contact");
    }
  }

  async function findPath() {
    if (!pathCompany.trim()) return;
    try {
      const resp = await apiClient.findNetworkPath(pathCompany.trim());
      setPaths(resp.paths);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to find path");
    }
  }

  return (
    <div className="page-stack">
      <section className="grid-cards">
        <article className="status-card"><p className="status-card-title">Connections</p><p className="status-card-value">{stats?.connection_count ?? 0}</p></article>
        <article className="status-card"><p className="status-card-title">Edges</p><p className="status-card-value">{stats?.edge_count ?? 0}</p></article>
        <article className="status-card"><p className="status-card-title">Avg Trust</p><p className="status-card-value">{stats?.avg_trust_score ?? 0}</p></article>
      </section>

      <section className="panel">
        <h2>Add Contact</h2>
        {error && <p className="error-text">{error}</p>}
        <form className="filters-row" onSubmit={submitNode}>
          <label>ID<input value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })} required /></label>
          <label>Name<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>Company<input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} required /></label>
          <label>Role<input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} required /></label>
          <label>LinkedIn URL<input value={form.linkedin_url} onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })} /></label>
          <label>Connection Strength (1-5)
            <input type="number" min={1} max={5} value={form.connection_strength} onChange={(e) => setForm({ ...form, connection_strength: Number(e.target.value) })} />
          </label>
          <label>Last Contact Date
            <input type="date" value={form.last_contact_date} onChange={(e) => setForm({ ...form, last_contact_date: e.target.value })} />
          </label>
          <label>Notes<input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></label>
          <button type="submit">Add Contact (Confirm)</button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Path Finder</h2>
          <div className="button-row">
            <input type="text" value={pathCompany} onChange={(e) => setPathCompany(e.target.value)} placeholder="Enter company name" />
            <button onClick={findPath}>Find Warm Path</button>
          </div>
        </div>
        {paths.length === 0 ? <p>No path results yet.</p> : (
          <ul className="activity-list">
            {paths.map((path, idx) => (
              <li key={`path-${idx}`}>{path.map((node) => `${node.name} (${node.company})`).join(" → ")}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2>Contacts</h2>
        {nodes.length === 0 ? <p>No network contacts yet.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Name</th><th>Company</th><th>Role</th><th>Strength</th></tr></thead>
              <tbody>
                {nodes.map((node) => (
                  <tr key={node.id}>
                    <td>{node.name}</td>
                    <td>{node.company}</td>
                    <td>{node.role}</td>
                    <td>{node.connection_strength}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
