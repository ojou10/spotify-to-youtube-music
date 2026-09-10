import { useEffect, useState } from "react";
import { api } from "../../api/client";

export function ReportPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<{ destination_playlist_id: string | null; destination_name: string | null; status: string } | null>(null);
  useEffect(() => { api.get<typeof job>(`/transfers/${jobId}`).then(setJob); }, [jobId]);
  return <section className="page"><div className="hero"><span className="eyebrow">REPORT</span><h1>Transfer summary</h1><p>Export a safe audit of every source position.</p></div><article className="card"><h2>{job?.status || "Loading"}</h2>{job?.destination_playlist_id && <p><a href={`https://music.youtube.com/playlist?list=${job.destination_playlist_id}`} target="_blank" rel="noreferrer">Open {job.destination_name || "destination playlist"}</a></p>}<p><a className="primary-link" href={`/api/transfers/${jobId}/exports/csv`}>Download CSV</a> <a className="secondary" href={`/api/transfers/${jobId}/exports/json`}>Download JSON</a></p></article></section>;
}
