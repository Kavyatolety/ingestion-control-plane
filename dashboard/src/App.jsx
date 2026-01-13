import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return res.json();
}

export default function App() {
  const [sources, setSources] = useState([]);
  const [selectedSourceId, setSelectedSourceId] = useState(null);

  const [newName, setNewName] = useState("Sample CSV");
  const [newPath, setNewPath] = useState("./data/sample.csv");

  const [job, setJob] = useState(null);
  const [events, setEvents] = useState([]);
  const [errors, setErrors] = useState([]);

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const selectedSource = useMemo(
    () => sources.find((s) => s.id === selectedSourceId) || null,
    [sources, selectedSourceId]
  );

  async function refreshSources() {
    const data = await api("/sources");
    setSources(data);
    if (data.length && selectedSourceId == null) setSelectedSourceId(data[0].id);
  }

  async function refreshJob(jobId) {
    const j = await api(`/ingestions/${jobId}`);
    setJob(j);
    const ev = await api(`/ingestions/${jobId}/events`);
    setEvents(ev);
    const er = await api(`/ingestions/${jobId}/errors`);
    setErrors(er);
  }

  useEffect(() => {
    refreshSources().catch((e) => setMsg(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onCreateSource(e) {
    e.preventDefault();
    setMsg("");
    setLoading(true);
    try {
      const s = await api("/sources", {
        method: "POST",
        body: JSON.stringify({ name: newName, csv_path: newPath }),
      });
      await refreshSources();
      setSelectedSourceId(s.id);
      setMsg(`Created source #${s.id}`);
    } catch (e2) {
      setMsg(e2.message);
    } finally {
      setLoading(false);
    }
  }

  async function onStartIngestion() {
    if (!selectedSource) return;
    setMsg("");
    setLoading(true);
    try {
      const j = await api(`/sources/${selectedSource.id}/ingestions`, { method: "POST" });
      setJob(j);
      setEvents([]);
      setErrors([]);
      setMsg(`Started job #${j.id}`);
      await refreshJob(j.id);
    } catch (e2) {
      setMsg(e2.message);
    } finally {
      setLoading(false);
    }
  }

  async function onRefresh() {
    setMsg("");
    setLoading(true);
    try {
      await refreshSources();
      if (job?.id) await refreshJob(job.id);
    } catch (e2) {
      setMsg(e2.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 24, maxWidth: 1000, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 8 }}>Ingestion Control Plane</h1>
      <div style={{ color: "#666", marginBottom: 16 }}>
        API: <code>{API_BASE}</code>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, alignItems: "start" }}>
        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Sources</h2>

          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <select
              value={selectedSourceId ?? ""}
              onChange={(e) => setSelectedSourceId(Number(e.target.value))}
              style={{ flex: 1, padding: 8 }}
            >
              {sources.length === 0 ? (
                <option value="">(No sources yet)</option>
              ) : (
                sources.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.id} — {s.name} ({s.status})
                  </option>
                ))
              )}
            </select>

            <button onClick={onRefresh} disabled={loading} style={{ padding: "8px 12px" }}>
              Refresh
            </button>
          </div>

          <button
            onClick={onStartIngestion}
            disabled={loading || !selectedSource}
            style={{ padding: "10px 12px", width: "100%" }}
          >
            Start Ingestion
          </button>

          <hr style={{ margin: "16px 0", border: "none", borderTop: "1px solid #eee" }} />

          <h3 style={{ marginTop: 0 }}>Create Source</h3>
          <form onSubmit={onCreateSource} style={{ display: "grid", gap: 8 }}>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Source name" style={{ padding: 10 }} />
            <input value={newPath} onChange={(e) => setNewPath(e.target.value)} placeholder="./data/sample.csv" style={{ padding: 10 }} />
            <button type="submit" disabled={loading} style={{ padding: "10px 12px" }}>
              Create
            </button>
          </form>
        </div>

        <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
          <h2 style={{ marginTop: 0 }}>Latest Job</h2>

          {!job ? (
            <div style={{ color: "#666" }}>No job yet. Start an ingestion.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              <div><strong>ID:</strong> {job.id}</div>
              <div><strong>Status:</strong> {job.status}</div>
              <div><strong>Started:</strong> {job.started_at ?? "(not started)"}</div>
              <div><strong>Finished:</strong> {job.finished_at ?? "(not finished)"}</div>
              <div><strong>Checkpoint:</strong> {job.checkpoint ?? "(none)"}</div>
            </div>
          )}

          <hr style={{ margin: "16px 0", border: "none", borderTop: "1px solid #eee" }} />

          <h3 style={{ marginTop: 0 }}>Events</h3>
          {events.length === 0 ? (
            <div style={{ color: "#666" }}>(none)</div>
          ) : (
            <ul style={{ paddingLeft: 18 }}>
              {events.map((e, idx) => (
                <li key={idx} style={{ marginBottom: 8 }}>
                  <div>
                    <code>{e.type}</code> <span style={{ color: "#666" }}>{e.ts}</span>
                  </div>
                  <pre style={{ margin: 0, background: "#fafafa", padding: 8, borderRadius: 8, overflowX: "auto" }}>
                    {JSON.stringify(e.payload, null, 2)}
                  </pre>
                </li>
              ))}
            </ul>
          )}

          <h3>Errors</h3>
          {errors.length === 0 ? (
            <div style={{ color: "#666" }}>(none)</div>
          ) : (
            <ul style={{ paddingLeft: 18 }}>
              {errors.map((e, idx) => (
                <li key={idx} style={{ marginBottom: 8 }}>
                  <div>
                    <strong>{e.code}</strong> — {e.message}{" "}
                    <span style={{ color: "#666" }}>({e.severity}, retryable: {String(e.retryable)})</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {msg && (
        <div style={{ marginTop: 16, padding: 12, borderRadius: 12, background: "#fffbe6", border: "1px solid #ffe58f" }}>
          {msg}
        </div>
      )}
    </div>
  );
}
