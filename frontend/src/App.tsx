import { AppShell } from "./components/AppShell";
import { DestinationPage } from "./features/destination/DestinationPage";
import { SetupPage } from "./features/setup/SetupPage";
import { SourcePage } from "./features/source/SourcePage";

export function App() {
  const path = window.location.pathname;
  const page = path.startsWith("/setup") ? <SetupPage /> : path.startsWith("/new/destination") ? <DestinationPage /> : path.startsWith("/new/source") ? <SourcePage /> : <section className="page"><div className="hero"><span className="eyebrow">LOCAL · PRIVATE · RESUMABLE</span><h1>Playlist Bridge</h1><p>Move a Spotify playlist to YouTube Music with reviewable matching and safe recovery.</p><a className="primary-link" href="/setup">Connect accounts</a></div></section>;
  return <AppShell>{page}</AppShell>;
}
