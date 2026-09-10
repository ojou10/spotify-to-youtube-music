import { useEffect, useState } from "react";
import { api } from "../../api/client";

export function ProgressPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<{ status: string; source_track_count: number; counts: Record<string, number>; revision: number } | null>(null);
  useEffect(() => { api.get<typeof job>(`/transfers/${jobId}`).then(setJob); const events = new EventSource(`/api/transfers/${jobId}/events`); events.addEventListener("progress", (event) => { const payload = JSON.parse((event as MessageEvent).data); setJob((current) => current && payload.revision >= current.revision ? { ...current, status: payload.status, counts: payload.counts, revision: payload.revision } : current); }); return () => events.close(); }, [jobId]);
  const done = job?.counts?.done ?? 0;
  return <section className="page"><div className="hero"><span className="eyebrow">TRANSFER PROGRESS</span><h1>Working through your playlist</h1><p>Keep this page open or come back later. The worker continues locally.</p></div><article className="card">{job ? <><h2>{job.status}</h2><progress max={job.source_track_count || 1} value={done} /> <p>{done.toLocaleString()} of {(job.source_track_count || 0).toLocaleString()} positions completed</p><div className="segmented"><a className="primary-link" href={`/jobs/${jobId}/review`}>Review matches</a><a className="secondary" href={`/jobs/${jobId}/report`}>Open report</a></div></> : <p>Loading job…</p>}</article></section>;
}
