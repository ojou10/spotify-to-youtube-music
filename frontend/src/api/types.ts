export type ApiErrorBody = {
  error: { code: string; message: string; action: string | null; field_errors: Record<string, string> | null };
};

export type SetupStatus = {
  spotify: { configured: boolean; connected: boolean; display_name: string | null };
  youtube: { configured: boolean; connected: boolean; display_name: string | null };
};

export type PlaylistPreview = {
  playlist_id: string;
  name: string;
  owner_name: string | null;
  public: boolean;
  total: number;
  spotify_url: string;
  artwork_url: string | null;
  snapshot_id: string | null;
};

export type DestinationPlaylist = { playlist_id: string; title: string; count: number; owned: boolean; url: string | null };

export type JobSummary = { id: string; revision: number; status: string; source_name: string | null; counts: Record<string, number> };
