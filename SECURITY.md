# Security Policy

## Current status

Playlist Bridge is in planning and does not yet have a supported release. Security reports about repository content, planned credential handling, or future implementation are still welcome.

## Reporting a vulnerability

Do not open a public issue containing a vulnerability, credential, token, cookie, private playlist, account identifier, or transfer report.

Use GitHub's private vulnerability reporting feature from the repository Security tab when it is available. Include:

- the affected file, component, or documented workflow;
- the impact and reproducible conditions;
- a minimal proof that contains no real credentials or personal playlist data;
- a suggested mitigation, if known.

## Accidental credential exposure

If any provider credential reaches a commit, issue, log, report, screenshot, or message:

1. Revoke or rotate it immediately at the provider.
2. Remove the exposed material from public access.
3. Review repository history and published artifacts.
4. Treat the old value as compromised even after deletion.

Never post a real secret while asking whether it is sensitive.

## Local data boundary

The first version stores authentication material, its SQLite database, and transfer history only in the current operating-system user's application-data directory. The public repository must contain only dummy field names and setup instructions.
