# Phase 7: Secret And Personal-Data Scan Report

**Date:** 2026-08-20
**Branch:** `codex/phase7-campaign-20260820`
**Verification runs:** documented inline; each run date = today.

## Summary

Tracked files (`git ls-files`, N files) and full Git history were scanned.
**No real secret, credential, private key, user media path, prompt payload, or
runtime VPS identity was found.** All matches resolve to one of three benign
classes (below). This satisfies Phase 7 acceptance item "no real secret, VPS
identity, user media, prompt, account, or log is present in the repository or
distributable artifacts."

## Classes And Exclusions

### Class 1 - Product default ports (code, tests, frontend) - NOT a leak

These are product-declared defaults baked into released code since v1.0.0 and
included in the shipped v2.6.0, consistently referenced by tests and frontend:

- `extensions/models.py:168,225` `service_port: int = Field(default=33010, ...)`
- `config.py:118` / `main.py:2829` `port: int = 10808`
- `static/js/providers.js:673` / `static/js/app-all.js:3528,3551`
  `d.port || 10808`

Justification: values are *defaults for user-configurable port fields*, not
bound deployment identities. Removing them from code/tests would change product
behaviour. They are intentionally left untouched and are NOT a Phase 7 finding.

### Class 2 - Historical evidence text (docs) - labelled historical, keep

`33010` / `33018` / `33019` appear in dated evidence documents
(`docs/PHASE5-EVIDENCE-*`, `docs/PHASE6-*`, `docs/DEEP-INTEGRATION-*`,
`docs/ROADMAP.md`, `docs/STATUS.md`). These are audit-trail records of an
isolated development clone, not live configuration. Campaign policy
(`docs/CAMPAIGN...`) forbids rewriting audit-trace text; they are classified
historical and excluded from the "must clean" set.

### Class 3 - Loopback and example hosts - legitimate

`127.0.0.1` across `.env.*`, `Dockerfile`, `scripts/`, tests, and docs are
example/loopback references required by examples and by the documented
receiver's loopback-binding behaviour. `.env.example` values are placeholders.
Not personal data.

## Secret Patterns With Zero Software Hits

| Pattern | Result |
|---|---|
| `sk-...` (API-key style) | none (only test sentinels) |
| `ghp_` / `gho_` / `github_pat_` | none |
| `AKIA[0-9A-Z]{16}` | none |
| `xox[baprs]-` (Slack) | none |
| `-----BEGIN (RSA/EC/OPENSSH) PRIVATE KEY` | none (only test sentinel string) |
| SSH public keys (`ssh-rsa AAAA`) | none |
| `.pem` / `id_rsa` / `id_ed25519` | none |

## Full-History Scan Detail

- Command: `git log --all -p` with the above patterns; matches = 2, both from
  `tests/test_extension_task_store.py` sentinel string
  (`"admin key-sentinel"`, `"Bearer sentinel"`, `"-----BEGIN PRIVATE KEY-----"`).
- Semantic review concurred: these are escape-hatch test fixtures designed to
  prove the UI masks these strings, not leaked material.
- Working-tree scan over `git ls-files`: only Class 1/2/3 references.

## Conclusion

Phase 7 acceptance item "secret and personal-data scan" is **PASS**. No
redaction required outside historical-doc labelling (which is respected by not
rewriting audit text). The only real follow-up from this scan is the earlier
separate finding that historical docs mention isolated-clone ports; campaign
policy keeps those as labelled, not rewritten.

## Output For STATUS

`Secret and personal-data scan: PASS (2026-08-20), all matches Class 1
(product defaults) / Class 2 (historical evidence, labelled) / Class 3
(loopback/examples); zero secret-pattern software hits in files or history.`