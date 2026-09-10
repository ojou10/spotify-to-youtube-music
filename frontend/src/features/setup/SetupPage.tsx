import { useState } from "react";
import { api } from "../../api/client";
import type { SetupStatus } from "../../api/types";

export function SetupPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [spotifyClient, setSpotifyClient] = useState("");
  const [youtubeClient, setYoutubeClient] = useState("");
  const [youtubeSecret, setYoutubeSecret] = useState("");
  const [challenge, setChallenge] = useState<{ challenge_id: string; user_code: string; verification_url: string } | null>(null);
  const refresh = () => api.get<SetupStatus>("/setup").then(setStatus);
  return <section className="page"><div className="hero"><span className="eyebrow">STEP 01 · CONNECTIONS</span><h1>Connect your music accounts</h1><p>Credentials stay on this computer. Playlist Bridge never stores them in the browser.</p></div><div className="grid two"><article className="card"><h2>Spotify</h2><p className="muted">Sign in to the account that owns the public playlist.</p>{status?.spotify.connected ? <p className="success">Connected{status.spotify.display_name ? ` as ${status.spotify.display_name}` : ""}.</p> : <><label>Spotify client ID<input value={spotifyClient} onChange={(event) => setSpotifyClient(event.target.value)} /></label><button onClick={() => api.post<{ authorization_url: string }>("/setup/spotify/start", { client_id: spotifyClient }).then((result) => { window.location.href = result.authorization_url; })}>Connect Spotify</button></>}</article><article className="card"><h2>YouTube Music</h2><p className="muted">Use a Google TV and Limited Input device OAuth client.</p>{status?.youtube.connected ? <p className="success">Connected.</p> : <><label>Google client ID<input value={youtubeClient} onChange={(event) => setYoutubeClient(event.target.value)} /></label><label>Client secret<input type="password" value={youtubeSecret} onChange={(event) => setYoutubeSecret(event.target.value)} /></label><button onClick={() => api.post<typeof challenge>("/setup/youtube/start", { client_id: youtubeClient, client_secret: youtubeSecret }).then(setChallenge)}>Start YouTube setup</button>{challenge && <div className="challenge"><p>Visit <a href={challenge.verification_url} target="_blank" rel="noreferrer">Google verification</a> and enter <strong>{challenge.user_code}</strong>.</p><button onClick={() => api.post("/setup/youtube/poll", { challenge_id: challenge.challenge_id }).then(refresh)}>Check connection</button></div>}</>}</article></div><button className="secondary" onClick={refresh}>Refresh connection status</button></section>;
}
