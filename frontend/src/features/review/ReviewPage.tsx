import { useEffect, useState } from "react";
import { api } from "../../api/client";

type ReviewItem = { id: string; source_position: number; title: string; artists: string[]; match_status: string; candidates: { id: string; title: string; score: number }[] };

export function ReviewPage({ jobId }: { jobId: string }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const load = (next?: string | null) => api.get<{ items: ReviewItem[]; next_cursor: string | null }>(`/transfers/${jobId}/items?limit=50${next ? `&cursor=${next}` : ""}`).then((result) => { setItems((current) => next ? [...current, ...result.items] : result.items); setCursor(result.next_cursor); });
  useEffect(() => { load(); }, [jobId]);
  return <section className="page"><div className="hero"><span className="eyebrow">REVIEW</span><h1>Resolve uncertain matches</h1><p>Only this page is loaded at a time, so large playlists stay responsive.</p></div><div className="playlist-list">{items.map((item) => <article className="card" key={item.id}><span className="eyebrow">POSITION {item.source_position + 1} · {item.match_status}</span><h2>{item.title}</h2><p className="muted">{item.artists.join(", ")}</p>{item.candidates.map((candidate) => <button key={candidate.id} onClick={() => api.put(`/transfers/${jobId}/items/${item.id}/decision`, { action: "accept_candidate", candidate_id: candidate.id }).then(() => load())}>Accept {candidate.title} · {Math.round(candidate.score)}</button>)}<button className="secondary" onClick={() => api.put(`/transfers/${jobId}/items/${item.id}/decision`, { action: "skip" }).then(() => load())}>Skip</button></article>)}</div>{cursor && <button className="secondary" onClick={() => load(cursor)}>Load more</button>}</section>;
}
