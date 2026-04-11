import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../api/client";
import { OutreachDraftItem, OutreachQueueItem } from "../types/api";

export function OutreachPage() {
  const [queue, setQueue] = useState<OutreachQueueItem[]>([]);
  const [drafts, setDrafts] = useState<OutreachDraftItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});

  async function load() {
    setLoading(true);
    setError("");
    try {
      const [queueResp, draftsResp] = await Promise.all([
        apiClient.getOutreachQueue(),
        apiClient.getOutreachDrafts(),
      ]);
      setQueue(queueResp.items);
      setDrafts(draftsResp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load outreach data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const warmCount = useMemo(
    () => queue.filter((item) => item.classification === "warm_intro").length,
    [queue],
  );
  const coldCount = useMemo(
    () => queue.filter((item) => item.classification !== "warm_intro").length,
    [queue],
  );

  async function runPipeline() {
    const ok = window.confirm("Run outreach drafting pipeline now? This creates draft files for review.");
    if (!ok) return;
    setRunning(true);
    try {
      await apiClient.runOutreach(true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run outreach pipeline");
    } finally {
      setRunning(false);
    }
  }

  async function approveDraft(draftId: string) {
    const ok = window.confirm("Approve this draft? It will be moved to approved/ for manual send.");
    if (!ok) return;
    await apiClient.approveOutreachDraft(draftId, true);
    await load();
  }

  async function rejectDraft(draftId: string) {
    const reason = (rejectReason[draftId] || "").trim();
    if (!reason) {
      setError("Rejection reason is required.");
      return;
    }
    const ok = window.confirm("Reject this draft? It will be moved to rejected/ with the reason.");
    if (!ok) return;
    await apiClient.rejectOutreachDraft(draftId, reason, true);
    await load();
  }

  return (
    <div className="page-stack">
      <section className="grid-cards">
        <article className="status-card"><p className="status-card-title">Outreach Targets</p><p className="status-card-value">{queue.length}</p></article>
        <article className="status-card"><p className="status-card-title">Warm Intro</p><p className="status-card-value">{warmCount}</p></article>
        <article className="status-card"><p className="status-card-title">Cold</p><p className="status-card-value">{coldCount}</p></article>
        <article className="status-card"><p className="status-card-title">Pending Drafts</p><p className="status-card-value">{drafts.length}</p></article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Outreach Queue</h2>
          <button onClick={runPipeline} disabled={running}>{running ? "Running..." : "Run Outreach Pipeline"}</button>
        </div>
        {loading && <p>Loading outreach queue...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && queue.length === 0 && <p>No outreach targets for today.</p>}
        {!loading && queue.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Company</th><th>Role</th><th>Classification</th></tr></thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={`${item.company}-${item.job_url}`}>
                    <td>{item.company}</td>
                    <td>{item.role}</td>
                    <td>{item.classification}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <h2>Draft Review</h2>
        {drafts.length === 0 ? <p>No pending drafts.</p> : (
          <div className="activity-list">
            {drafts.map((draft) => (
              <div key={draft.draft_id} className="panel">
                <p><strong>{draft.kind}</strong> — {draft.filename}</p>
                <p className="status-card-title">{draft.path}</p>
                <pre className="text-output">{draft.content}</pre>
                <label className="filters-row">
                  Reject reason
                  <input
                    type="text"
                    value={rejectReason[draft.draft_id] || ""}
                    onChange={(e) => setRejectReason((prev) => ({ ...prev, [draft.draft_id]: e.target.value }))}
                    placeholder="Reason for rejection"
                  />
                </label>
                <div className="button-row">
                  <button onClick={() => approveDraft(draft.draft_id)}>Approve (Confirm)</button>
                  <button className="secondary-button" onClick={() => rejectDraft(draft.draft_id)}>Reject (Confirm)</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
