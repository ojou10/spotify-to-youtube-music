# Security Policy

Playlist Bridge is a local application in active development. Report vulnerabilities through GitHub private vulnerability reporting; do not open public issues containing credentials, tokens, cookies, private playlist data, or reports.

If a provider credential is exposed in a commit, issue, log, screenshot, or message, revoke or rotate it immediately, remove public copies, and review repository history. Treat the old value as compromised even after deletion.

Provider secrets, cookies, tokens, SQLite data, and transfer history stay in the operating-system per-user application-data directory. They must never be logged, returned to the browser, exported, or committed. The release gate scans tracked files for credential-shaped values and runtime artifacts.
