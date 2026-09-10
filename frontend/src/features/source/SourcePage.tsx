import { useState } from "react";
import { api } from "../../api/client";
import type { PlaylistPreview } from "../../api/types";

export function SourcePage() {
  const [url, setUrl] = useState("");
  const [preview, setPreview] = useState<PlaylistPreview | null>(null);
  const [error, setError] = useState("");
  return <section className="page"><div className="hero"><span className="eyebrow">STEP 02 · SOURCE</span><h1>Choose a Spotify playlist</h1><p>Paste a public playlist link. We’ll verify ownership before reading tracks.</p></div><article className="card form-card"><label>Spotify playlist URL<input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://open.spotify.com/playlist/..." /></label><button onClick={() => { setError(""); api.post<PlaylistPreview>("/spotify/inspect", { url }).then(setPreview).catch((reason: Error) => setError(reason.message)); }}>Inspect playlist</button>{error && <p className="error" role="alert">{error}</p>}{preview && <div className="preview"><div><span className="eyebrow">ELIGIBLE PLAYLIST</span><h2>{preview.name}</h2><p>{preview.owner_name} · {preview.total.toLocaleString()} tracks · {preview.public ? "Public" : "Private"}</p><a href={preview.spotify_url} target="_blank" rel="noreferrer">Open in Spotify</a></div><a className="primary-link" href="/new/destination">Continue to destination</a></div>}</article></section>;
}
