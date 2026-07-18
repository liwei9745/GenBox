---
status: verifying
trigger: "GenBox AsyncSSH reports permission denied while system OpenSSH accepts the same VPS root password"
created: 2026-07-18
updated: 2026-07-18
---

## Symptoms

- Expected behavior: GenBox password-mode SSH test connects to the isolated VPS development target after host-key confirmation.
- Actual behavior: GenBox reports a sanitized SSH authentication rejection while Windows OpenSSH can log in with the same user-confirmed password.
- Error: GenBox maps AsyncSSH `PermissionDenied` to `SSHAuthenticationError`.
- Timeline: Reproduced after restarting the laboratory on commit `0550d8d`.
- Reproduction: Open Extension Center, select password mode, enter the VPS target and confirmed password, then test the connection.

## Current Focus

- hypothesis: AsyncSSH does not complete password authentication, but current evidence cannot distinguish a pre-password close from a close after AsyncSSH requests the password.
- test: Load the secret-free per-attempt tracker and perform exactly one isolated-target connection test.
- expecting: The diagnostic distinguishes pre-password termination from rejection after password selection without logging credentials, host identity, or raw protocol traffic.
- next_action: Restart the administrator laboratory on the diagnostic build, run one password test, and record only the returned diagnostic stage and timestamp.
- reasoning_checkpoint: VPS sshd recorded `Accepted password` for the system OpenSSH attempt at 12:03:29, while the likely GenBox attempt at 11:56:31 recorded only `Connection closed ... [preauth]` and no `Failed password`.

## Evidence

- timestamp: 2026-07-18T12:03:29Z
  fact: VPS sshd logged `Accepted password for root` for the user's system OpenSSH session.
- timestamp: 2026-07-18T11:56:31Z
  fact: VPS sshd logged only a pre-authentication connection close for the user's public IP during the likely GenBox attempt.
- timestamp: 2026-07-18
  fact: AsyncSSH 2.24.0 consumes a supplied `password` before invoking the optional client callback.
- timestamp: 2026-07-18
  fact: The diagnostic uses the official `SSHClient.password_auth_requested()` callback, persists no attempt data, and passed 29 focused plus 183 full tests, including a real local AsyncSSH password-authentication server.

## Eliminated

- hypothesis: The VPS password is globally invalid.
  reason: The server explicitly accepted it through system OpenSSH.
- hypothesis: The current error proves a wrong password.
  reason: There is no matching `Failed password` record for the likely GenBox attempt.
- hypothesis: Host-key mismatch caused the reported authentication rejection.
  reason: Host-key validation occurs before authentication and maps to a different failure path.
- hypothesis: The nearby `Connection closed ... [preauth]` journal entry definitely represents the credential-bearing GenBox attempt.
  reason: GenBox's credential-free host-key probe can also create a pre-authentication close.

## Resolution

- root_cause:
- fix: Added non-persistent, allowlisted authentication-stage diagnostics; root cause is not yet determined.
- verification: Local automated verification passed; one isolated-target runtime attempt remains.
- files_changed: extensions/orchestrator.py, main.py, tests/test_extensions.py, docs/STATUS.md
