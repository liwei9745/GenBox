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

- hypothesis: The remote compatibility issue may remain, but the repeated development blocker was also amplified by a confirmed mixed-runtime defect: cached/new static UI was being used with an old or stopped Python backend.
- test: Start the Loop 2 build through the owned Lab launcher, verify the runtime/source identity, then run one credential-bearing network task against the isolated target using the saved host fingerprint when available.
- expecting: Historical deployment resumes at network selection; empty credentials create no request; one network task reports an exact sanitized stage and does not mark completion until the VPS-to-GenBox probe passes.
- next_action: Run `./start-lab.ps1 start`, verify the footer reports the current development runtime on `8892`, load the saved target, enter a fresh session credential, and run the private-network check once.
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
- timestamp: 2026-07-18
  fact: State-machine Loop 1 passed 103 focused and 191 full tests. It separates deployment and network completion, rejects missing or ambiguous credentials before side effects, prevents duplicate/stale requests, persists only the confirmed public host fingerprint, and protects visible one-time delivery.
- timestamp: 2026-07-18
  fact: Port 8892 was observed first without a listener and later with a legacy GenBox process that returned the setup contract and OpenAPI identity but lacked the new runtime identity endpoint. This confirmed that browser refresh and backend reload had been treated as the same operation.
- timestamp: 2026-07-18
  fact: Runtime-integrity Loop 2 added owned lifecycle records, Git/source identity checks, an offline browser heartbeat, and disabled HTTP process mutation. Focused checks passed 50 tests and the final full suite passed 209 tests.

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

- root_cause: A still-unverified AsyncSSH/VPS compatibility issue was compounded by incorrect UI recovery and a mixed local runtime in which cached/new static UI did not prove that the matching Python backend was loaded.
- fix: Added allowlisted authentication diagnostics, credential-gated single-flight state handling, safe recovery navigation, owned Lab lifecycle identity, source fingerprint verification, offline browser heartbeat, and removal of browser-triggered process mutation.
- verification: 50 focused and 209 full local tests passed; one isolated-target runtime network attempt remains.
- files_changed: main.py, scripts/genbox_lab.py, start-lab.ps1, start-lab.cmd, static/index.html, static/css/app.css, static/js/app-all.js, static/js/extensions.js, static/js/i18n.js, tests/test_genbox_lab.py, tests/test_setup_security.py, docs/STATUS.md, docs/ROADMAP.md, docs/DECISIONS.md
