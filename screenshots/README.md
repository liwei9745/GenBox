# Public Screenshot Set

Only the current, reviewed images under `screenshots/sanitized/` may be linked
from public documentation.

## Current Views

- `01-dashboard.png`: Dashboard with labeled synthetic device and usage data.
- `02-generate-workspace.png`: Multi-model image workspace from an empty client.
- `03-extension-center.png`: Extension Center using RFC 5737 placeholder values.
- `04-onboarding.png`: Beginner onboarding and capability overview.

## Capture Rules

1. Capture at `1440x900` from an isolated empty-data GenBox client.
2. Never capture a developer's normal `storage/`, `.env`, activity feed, media,
   Provider endpoints, VPS records, credentials, logs, or real IP addresses.
3. Use `192.0.2.0/24`, `198.51.100.0/24`, or `203.0.113.0/24` for example IPs.
4. Save reviewed output directly under `screenshots/sanitized/`; raw captures
   belong in an ignored temporary directory.
5. Generate the public Dashboard image from a raw `1440x900` capture with:

```powershell
python scripts/sanitize_dashboard_screenshot.py raw-dashboard.png screenshots/sanitized/01-dashboard.png
```

The sanitizer replaces host-specific values with explicit demo data and labels
the panel accordingly. Inspect every final PNG before committing it.
