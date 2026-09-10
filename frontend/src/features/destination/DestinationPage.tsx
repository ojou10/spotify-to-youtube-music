import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { DestinationPlaylist } from "../../api/types";

export function DestinationPage() {
  const [mode, setMode] = useState<"create" | "append">("create");
  const [name, setName] = useState("My Spotify playlist");
  const [visibility, setVisibility] = useState("private");
  const [playlists, setPlaylists] = useState<DestinationPlaylist[]>([]);
  useEffect(() => { if (mode === "append") api.get<{ items: DestinationPlaylist[] }>("/youtube/playlists").then((result) => setPlaylists(result.items)); }, [mode]);
  return <section className="page"><div className="hero"><span className="eyebrow">STEP 03 · DESTINATION</span><h1>Where should the playlist go?</h1><p>New playlists default to private. Appending never changes existing items.</p></div><div className="segmented"><button className={mode === "create" ? "selected" : ""} onClick={() => setMode("create")}>Create new</button><button className={mode === "append" ? "selected" : ""} onClick={() => setMode("append")}>Append existing</button></div>{mode === "create" ? <article className="card form-card"><label>Playlist name<input value={name} onChange={(event) => setName(event.target.value)} /></label><label>Visibility<select value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="private">Private</option><option value="public">Public</option></select></label><button onClick={() => api.post("/transfers", { source_url: "", destination_mode: "create", destination_name: name, destination_visibility: visibility })}>Create transfer</button></article> : <article className="card"><h2>Select an owned playlist</h2>{playlists.length ? <div className="playlist-list">{playlists.map((playlist) => <button key={playlist.playlist_id} className="playlist-option">{playlist.title}<span>{playlist.count} tracks</span></button>)}</div> : <p className="muted">No owned playlists found.</p>}</article>}</section>;
}
