import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { JobSummary } from "../../api/types";

export function HistoryPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  useEffect(() => { api.get<{ items: JobSummary[] }>("/transfers").then((result) => setJobs(result.items)); }, []);
  return <section className="page"><div className="hero"><span className="eyebrow">HISTORY</span><h1>Your transfer jobs</h1><p>Jobs remain local and resumable.</p></div><div className="playlist-list">{jobs.map((job) => <a className="card" key={job.id} href={`/jobs/${job.id}/progress`}><strong>{job.source_name || "Untitled playlist"}</strong><p className="muted">{job.status} · {job.counts?.done ?? 0} completed</p></a>)}</div></section>;
}
