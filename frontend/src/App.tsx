import { AppShell } from "./components/AppShell";
import { DestinationPage } from "./features/destination/DestinationPage";
import { HistoryPage } from "./features/history/HistoryPage";
import { ProgressPage } from "./features/progress/ProgressPage";
import { ReportPage } from "./features/report/ReportPage";
import { ReviewPage } from "./features/review/ReviewPage";
import { SetupPage } from "./features/setup/SetupPage";
import { SourcePage } from "./features/source/SourcePage";

export function App() {
  const path = window.location.pathname;
  const jobMatch = path.match(/^\/jobs\/([^/]+)\/(progress|review|report)$/);
  const page = path.startsWith("/setup") ? <SetupPage /> : path === "/history" ? <HistoryPage /> : jobMatch?.[2] === "progress" ? <ProgressPage jobId={jobMatch[1]} /> : jobMatch?.[2] === "review" ? <ReviewPage jobId={jobMatch[1]} /> : jobMatch?.[2] === "report" ? <ReportPage jobId={jobMatch[1]} /> : path.startsWith("/new/destination") ? <DestinationPage /> : path.startsWith("/new/source") ? <SourcePage /> : <section className="page"><div className="hero"><span className="eyebrow">LOCAL · PRIVATE · RESUMABLE</span><h1>Playlist Bridge</h1><p>Move a Spotify playlist to YouTube Music with reviewable matching and safe recovery.</p><a className="primary-link" href="/setup">Connect accounts</a></div></section>;
  return <AppShell>{page}</AppShell>;
}
