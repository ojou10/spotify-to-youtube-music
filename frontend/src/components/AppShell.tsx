import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return <><a className="skip-link" href="#main">Skip to content</a><header className="topbar"><div><span className="eyebrow">LOCAL TRANSFER TOOL</span><strong>Playlist Bridge</strong></div><nav aria-label="Primary"><a href="/setup">Setup</a><a href="/new/source">New transfer</a></nav></header><main id="main">{children}</main></>;
}
