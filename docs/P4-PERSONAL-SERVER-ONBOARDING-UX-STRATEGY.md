# P4 Personal Server Onboarding UX Strategy

**Date:** 2026-07-27
**Evidence scope:** local design and UI work only. This strategy does not claim
that a server connector, VPS connection, deployment, or cross-project Push
flow has been verified.

## Product Decision

Remove the user-visible `连接服务器` mega-step. It currently combines target
metadata, host identity, session credentials, and deployment permission checks
on one page, which makes the normal state transition look like a loop.

The new primary task is **部署 GenBox 扩展服务**. The working SSH path is a
small, linear sub-flow inside that task. A future server connector remains the
recommended direction, but it is unavailable until an installable agent,
enrollment, authenticated outbound transport, bounded operations, and tests
exist.

## Personal-Use Safety Baseline

This is a personal media project, so daily UI must not ask users to interpret
an algorithm or SHA-256 fingerprint. That changes presentation, not the
security outcome. The following are minimum personal safeguards rather than
enterprise-only process:

- SSH still binds a target to its canonical host-key algorithm and SHA-256
  fingerprint. A changed identity stops the session and needs explicit recovery.
- Passwords, private keys, sudo passwords, pairing responses, Push keys, and
  management keys stay out of URLs, browser storage, normal logs, screenshots,
  Git, and status documents.
- Browser requests carry structured choices only. Backend adapters generate
  fixed, allowlisted operations; there is no web terminal or browser-supplied
  shell.
- Existing production sources remain read-only; deployment mutation remains
  limited to a confirmed isolated-development target.
- Source media is retained until an authenticated matching receipt and explicit
  cleanup opt-in exist.

Raw identity details belong to advanced diagnostics. The normal UI says only
whether the server is confirmed or needs reconfirmation.

## Beginner Workflow

1. **Start deployment:** the page presents the honest route choice. `服务器连接器`
   is informational while unavailable. `使用 SSH 设置服务器` begins the working
   path.
2. **Server details:** select a saved server or provide its display name,
   address, SSH user, port, and purpose. Saving these non-secret details moves
   immediately to identity confirmation when needed.
3. **Confirm server:** this is an isolated view. It contains no SSH credential
   controls. Existing trusted-session pairing and advanced manual confirmation
   remain available behind the same backend contracts.
4. **Read-only environment check:** only after identity confirmation does the
   credential view appear. Credentials stay in the current page memory. Its
   one primary action performs the bounded host-key-verified discovery first;
   it does not deploy or probe sudo. A deployment-access diagnostic is a
   separate optional action only when the user is ready to plan a deployment.
5. **Recover precisely:** a changed server identity presents a dedicated
   recovery view with `重新确认这台服务器` and `返回修改服务器资料`. It never returns
   the user to a mixed form or masks a cleared password as `***`.

Every view has one primary action and a visible back/restart action. Refresh
restores durable, non-secret target/deployment state only; it never restores a
credential or pairing response.

## Design References

- VS Code Remote-SSH starts from a target selection, supports session prompts,
  recommends key authentication, and states that passwords/tokens are not saved:
  <https://code.visualstudio.com/docs/remote/ssh>
- GitHub Codespaces hides managed SSH mechanics behind a high-level connection
  surface, but relies on managed infrastructure rather than arbitrary VPS OAuth:
  <https://docs.github.com/en/codespaces/developing-in-a-codespace/using-github-codespaces-with-github-cli>
- Railway keeps service selection and deployment approval as separate actions:
  <https://docs.railway.com/services>
- Fly Launch scans defaults before asking for an explicit adjustment, and Fly
  recommends narrow, expiring tokens rather than broad credentials:
  <https://fly.io/docs/launch/create/>
  <https://fly.io/docs/security/tokens/>

## Non-Goals

- Do not pretend that an unavailable connector can connect or deploy.
- Do not weaken SSH host-key verification or auto-accept a changed host key.
- Do not add an embedded terminal or generic OAuth-as-SSH replacement.
- Do not block the existing Phase 4 SSH deployment/discovery/plan sequence.
