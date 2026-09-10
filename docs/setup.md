# Setup

1. Create a Spotify developer app and register the exact loopback callback shown by the local setup screen. Use Authorization Code with PKCE; do not put a client secret in this app or repository.
2. Create a Google OAuth client of type **TVs and Limited Input devices** for the YouTube Music device flow. Keep the client ID and secret local; the setup form sends them only to the loopback backend.
3. Start the app, connect both providers, paste a public playlist owned by the connected Spotify account, and inspect it before creating or appending a destination.

The browser receives only connection state, user codes, playlist metadata, progress, and review candidates. It never receives access tokens, refresh tokens, cookies, or client secrets. Revoke and rotate credentials immediately if they are exposed.
