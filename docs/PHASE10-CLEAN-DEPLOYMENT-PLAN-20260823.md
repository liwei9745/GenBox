# Phase 10 Clean Deployment W3 Plan

AGENT: Phase 10 clean deployment W3 方案审计 Agent
WAVE: W3 local clean deployment plan and Store API acceptance
STATUS: EXECUTION BLOCKED; clean clone/build passed, runtime Store acceptance did not complete
INPUT_HEAD: `1383f537ad4c1602e6586b6437c939dc80378f5c` (`1383f53`)
CHANGED_FILES: `docs/PHASE10-CLEAN-DEPLOYMENT-PLAN-20260823.md` only
RESULT: A disposable, loopback-only local clean deployment plan is defined below. It does not claim a live remote target, VPS evidence, browser evidence, or Phase 10 completion.
EVIDENCE: Read-only review of `docs/DEVELOPMENT-LIFECYCLE.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/STATUS.md`, `docs/PRODUCT.md`, `docker-compose.yml`, `Dockerfile`, `README.md`, `README_EN.md`, `docs/DOCKER-QUICKSTART.md`, `.env.example`, `.env.docker.example`, `docs/extensions-deployment-contract.md`, `docs/deployment-invariants.md`, `docs/GENBOX-STORE-REPAIR-COPILOT.md`, `tests/test_release_packaging.py`, `tests/test_extensions.py`, and the Phase 10 Store contract/frontend tests.
UNKNOWN: Docker Engine/Compose availability, local free disk, image build result, loopback port availability, and runtime response values must be discovered during the separately authorized run. No remote environment facts are known from this plan.
RISKS: The current Compose file uses a unique bind-mounted `./storage` directory rather than a named Docker volume; the directory is the unique persistent volume boundary for this run. A local image built from the target commit is local clean-deployment evidence, not immutable published-image or VPS evidence.
NEXT: Resolve the local Windows Compose/runtime execution issue in a separately
authorized diagnostic wave; retain Phase 10 In Progress.

## 11. Execution Record

- Personal branch push was authorized and completed before this run; no
  upstream PR or production target was touched.
- Clean clone at commit `1383f537ad4c1602e6586b6437c939dc80378f5c` and local
  Docker image build both passed.
- Compose runs were not accepted: Windows path conversion caused Compose to
  report that the cloned `docker-compose.yml` could not be opened. The failed
  resources were cleaned each time.
- A Docker-only fallback also built the clean image and created synthetic
  storage, but stopped at the `/api/setup/status` assertion before Store API
  assertions. This is `BLOCKED`, not a product pass; no response body was
  retained because it could contain runtime-sensitive details.
- No container, image, clone, temporary secret, VPS, SSH, browser, npm, or
  production resource remains from the attempts.

## 1. Scope And Prohibitions

This is a plan for one local, disposable GenBox runtime built from the exact
remote branch commit above. It must be run from a new temporary clone, never
from the current worktree. The current worktree has an unrelated pre-existing
modification and is not an input to the deployment.

The run is limited to:

- A synthetic administrator key and a synthetic Push key generated in memory.
- A random host loopback port mapped to the container's fixed `8891` port.
- One unique Compose project, container name, and temporary storage bind mount.
- HTTP readiness plus `GET /api/extensions/store` with its `installed`,
  `recommended`, and `all` views.
- Fail-closed unknown facts, planned catalog rows, external installed rows,
  public metadata redaction, and persistence across a container restart.

The run must not use SSH, any VPS or production endpoint, real media, real
accounts, real credentials, a browser, npm, Node package installation, Docker
Compose against a remote host, or any provider/network enrollment. It must not
call deployment, discovery, Push, vault, network, lifecycle, repair, or image
update operations. It must not update `docs/STATUS.md` as a side effect.

Every runtime value in the run is local synthetic evidence. In particular,
`127.0.0.1`, the temporary port, synthetic target record, and synthetic facts
must never be described as a live remote target or VPS observation.

## 2. Feasibility Matrix

| Path | W3 decision | Reason and boundary |
|---|---|---|
| `GET /api/setup/status` | Feasible readiness gate | The Docker healthcheck uses this route. It confirms the local process is serving and reports production auth mode; it is not Store acceptance evidence. |
| `GET /api/extensions/store` with `X-Admin-Key` | Feasible and required | The route returns the stable `installed`, `recommended`, and `all` projections. Production mode requires the synthetic admin key because the route is not in `AUTH_EXEMPT_PATHS`. |
| `GET /api/extensions/store` without the key | Feasible negative check | Expected `401`; proves the local production-mode auth boundary without exposing a secret. |
| `POST /api/extensions/targets` | Technically feasible but not needed | It can save target metadata, but it cannot create a verified environment projection or facts and is outside the Store-only acceptance matrix. Do not use it in W3. |
| `POST /api/extensions/discover` | Infeasible under W3 rules | It requires a server-confirmed target, SSH host-key trust, and a session credential. It is SSH-backed and must not be attempted. Its absence means no live environment fact can be claimed. |
| `POST /api/extensions/deploy/plan` or deploy start | Prohibited | It is a remote lifecycle path, requires SSH/discovery and an isolated target, and is outside Store projection verification. Do not infer deploy success from a catalog `deploy` action. |
| Browser Store rendering | Out of scope | Static frontend contracts are already covered by repository tests. No browser or npm command is permitted in this run. |
| Direct runtime fixture seed | Feasible setup-only mechanism | There is no public API for injecting synthetic `EnvironmentFacts` or `ExtensionInstance` records. A temporary pre-start fixture may write only synthetic `storage/extensions.json`; subsequent acceptance must use the Store HTTP API. |

The Store route is read-only. The target commit deliberately prevents browser
target metadata from injecting environment projection or facts. Therefore a
high-confidence Store recommendation cannot be obtained honestly through the
allowed HTTP paths alone. The fixture below exercises the public projection
with a complete Docker/Compose projection and incomplete facts so the expected
public result is `confidence=unknown` and `actions=[]`.

## 3. Preconditions And Clean Clone

Run the following in PowerShell from a terminal that is not inside the current
checkout. `$Repo` is the absolute path of the current repository only for
reading its `origin` URL; no files are read or written there by this plan.

```powershell
$Repo = 'E:\AI\GenBox-worktrees\p4planux\GenBox-od-release-v2.6.0-20260820'
$OriginUrl = git -C $Repo remote get-url origin
$Suffix = [guid]::NewGuid().ToString('N').Substring(0,12).ToLowerInvariant()
$RunRoot = Join-Path ([IO.Path]::GetTempPath()) ("genbox-p10-w3-" + $Suffix)
$EvidenceRoot = Join-Path $RunRoot 'evidence'
New-Item -ItemType Directory -Path $EvidenceRoot -Force | Out-Null

git clone --branch codex/phase7-campaign-20260820 --single-branch `
  $OriginUrl $RunRoot
git -C $RunRoot checkout --detach 1383f537ad4c1602e6586b6437c939dc80378f5c

if ((git -C $RunRoot rev-parse HEAD) -ne '1383f537ad4c1602e6586b6437c939dc80378f5c') {
  throw 'clean clone is not at the required input commit'
}
if ((git -C $RunRoot status --porcelain) -ne '') {
  throw 'clean clone is not clean after checkout'
}
if (-not (git -C $RunRoot branch -r --contains 1383f537ad4c1602e6586b6437c939dc80378f5c | Select-String 'origin/codex/phase7-campaign-20260820')) {
  throw 'required commit is not confirmed on the origin phase branch'
}

$StorageRoot = Join-Path $RunRoot 'storage'
New-Item -ItemType Directory -Path $StorageRoot -Force | Out-Null
$Project = ('p10w3' + $Suffix).ToLowerInvariant()
$Container = ('p10w3-genbox-' + $Suffix).ToLowerInvariant()
$Image = ('genbox-p10-w3:' + $Suffix).ToLowerInvariant()

$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start()
$Port = $listener.LocalEndpoint.Port
$listener.Stop()
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'invalid loopback port' }
```

The port is only a candidate. The post-start HTTP probe and container inspect
must confirm that this exact port belongs to this Compose project/container.
If another process takes it before startup, stop and select a new random port;
never use a fixed product or historical port.

The clone must be independently checked for release shape before building:

```powershell
python -m pytest -q tests/test_release_packaging.py tests/test_extensions.py
```

This is an optional preflight regression command, not Store runtime evidence.
If the available Python has no pytest, record `BLOCKED` and use the repository's
already configured test interpreter only if that does not install dependencies.
Do not install npm or browser dependencies. The plan does not require running
the full suite to proceed, but a failed packaging test is a stop condition.

## 4. Synthetic Configuration And Image

Generate both keys without printing them, storing them in Git, putting them in
URLs, or copying them into evidence. They may exist only in the temporary
`.env` and process memory until teardown.

```powershell
$AdminKey = 'gbx-w3-admin-' + [guid]::NewGuid().ToString('N')
$PushKey = 'gbx-w3-push-' + [guid]::NewGuid().ToString('N')
$EnvPath = Join-Path $RunRoot '.env'
@
APP_MODE=prod
GENBOX_PORT=8891
GENBOX_CONTAINER_NAME=$Container
GENBOX_IMAGE=$Image
ALLOWED_ORIGINS=http://127.0.0.1:$Port
ADMIN_KEY=$AdminKey
GENBOX_PUSH_KEYS={"w3-synthetic-source":"$PushKey"}
@
| Set-Content -LiteralPath $EnvPath -Encoding ascii
```

The Compose file passes `ADMIN_KEY` through the mounted `.env`, but the current
Compose file does not pass `GENBOX_PUSH_KEYS` as a process environment variable.
Because `sync/ingest.py` reads that value from process environment, create a
temporary, untracked override beside the clone. This does not alter the tracked
Compose file:

```powershell
$OverridePath = Join-Path $EvidenceRoot 'docker-compose.w3.override.yml'
@
services:
  genbox:
    environment:
      GENBOX_PUSH_KEYS: `${GENBOX_PUSH_KEYS}
@
| Set-Content -LiteralPath $OverridePath -Encoding ascii
```

Do not run `docker compose config`, `docker inspect` with environment output, or
any command that prints the generated `.env`; those commands can disclose keys.

Build from the exact clean clone. This tests the Phase 10 code in the clone,
not the published `2.6.1` image and not an image from the current worktree:

```powershell
docker build --pull=false --tag $Image $RunRoot
if ($LASTEXITCODE -ne 0) { throw 'local image build failed' }
```

`--pull=false` avoids silently changing the source provenance during the run.
If a required base image is not already available locally, stop and record the
build as `BLOCKED`; do not substitute a different source or claim clean
deployment. The local tag is only immediate local evidence, not a published
immutable repository digest.

## 5. Synthetic Store Fixture

Before starting the application, create a transient helper outside tracked
files and run it with the just-built image using `--network none`. It writes no
secrets and creates only synthetic Store records. This setup is not itself API
evidence; all acceptance assertions after startup use HTTP.

```powershell
$SeedPath = Join-Path $EvidenceRoot 'seed_store.py'
@
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from extensions.models import EnvironmentFacts, EnvironmentProjection, ExtensionInstance, ExtensionTarget
from extensions.store import target_identity_digest

out = Path(sys.argv[1])
target = ExtensionTarget(
    id="w3-target", name="synthetic-local-target", host="127.0.0.1", port=1,
    username="synthetic-user", target_role="isolated-development",
    identity_version=1,
)
digest = target_identity_digest(target)
observed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
projection = EnvironmentProjection(
    target_id=target.id, target_identity_digest=digest, observed_at=observed,
    docker_available=True, compose_available=True, evidence_complete=True,
    confidence="high",
)
facts = EnvironmentFacts(
    target_id=target.id, target_identity_digest=digest, observed_at=observed,
    os=None, arch="x86_64", cpu_cores=None, memory_mb=None, disk_mb=None,
    docker_version=None, compose_version=None, python_version=None, uv_version=None,
)
external = ExtensionInstance(
    id="external-w3", target_id=target.id, project="chatgpt2api",
    strategy="existing", deployment_mode="compose", service_port=1,
    install_dir="/synthetic/external", data_dir="/synthetic/external/data",
    image="registry.invalid/synthetic@sha256:" + "a" * 64,
    status="running", managed=False, ownership="external",
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    "targets": [target.model_dump()],
    "instances": [external.model_dump()],
    "environment_projections": [projection.model_dump()],
    "environment_facts": [facts.model_dump()],
    "batch_target_ids": [], "target_generations": {target.id: 1},
}, indent=2), encoding="utf-8")
@
| Set-Content -LiteralPath $SeedPath -Encoding ascii

docker run --rm --network none `
  --volume "$StorageRoot:/app/storage" `
  --volume "$SeedPath:/tmp/seed_store.py:ro" `
  --entrypoint python $Image /tmp/seed_store.py /app/storage/extensions.json
if ($LASTEXITCODE -ne 0) { throw 'synthetic Store fixture failed' }
```

The fixture intentionally makes all nine recommendation facts not fully known:
only `arch` is observed. The saved projection is complete and Docker/Compose
positive, but the facts gate must still force the recommendation to unknown and
remove actions. The external instance is intentionally not managed, so it must
be installed read-only even though its catalog project is `chatgpt2api`.

## 6. Start And Scope Check

Start only this local project. The original Compose file's relative
`./storage:/app/storage` therefore resolves to the unique clone directory. The
project name and container name make collisions detectable.

```powershell
$Compose = @('-f', (Join-Path $RunRoot 'docker-compose.yml'), '-f', $OverridePath,
  '--project-name', $Project, '--env-file', $EnvPath)

docker compose @Compose up -d --no-build
if ($LASTEXITCODE -ne 0) { throw 'Compose startup failed' }

$containerInfo = docker inspect $Container --format '{{.Name}}|{{.State.Status}}|{{json .State.Health.Status}}|{{json .Mounts}}'
if ($LASTEXITCODE -ne 0 -or $containerInfo -notmatch [regex]::Escape($Container)) {
  throw 'expected unique container was not found'
}
```

Inspect output must be limited to name, state, health, and mount destination/
source shape. Never inspect environment variables. Confirm that the mount
source is under `$RunRoot\storage`, the container target is `/app/storage`, and
no source path is outside the temporary clone.

Wait for the healthcheck without reading logs:

```powershell
$deadline = (Get-Date).AddSeconds(90)
do {
  $health = docker inspect $Container --format '{{.State.Health.Status}}'
  if ($health -eq 'healthy') { break }
  Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($health -ne 'healthy') { throw "local container did not become healthy: $health" }
```

The readiness route is the only non-Store HTTP gate:

```powershell
$BaseUrl = "http://127.0.0.1:$Port"
$setup = Invoke-WebRequest "$BaseUrl/api/setup/status" -UseBasicParsing
if ($setup.StatusCode -ne 200) { throw 'setup readiness failed' }
$setupBody = $setup.Content | ConvertFrom-Json
if ($setupBody.app_mode -ne 'prod' -or $setupBody.auth_required -ne $true) {
  throw 'runtime is not in the expected production auth mode'
}
```

## 7. Store API Acceptance Matrix

Use the synthetic key in a request header, but never print the header or key.
The helper below stores only public response bodies in the temporary evidence
directory.

```powershell
$headers = @{ 'X-Admin-Key' = $AdminKey }
$StoreBeforePath = Join-Path $EvidenceRoot 'store-before.json'
$storeResponse = Invoke-WebRequest "$BaseUrl/api/extensions/store" -Headers $headers -UseBasicParsing
if ($storeResponse.StatusCode -ne 200) { throw 'Store API did not return 200' }
$storeResponse.Content | Set-Content -LiteralPath $StoreBeforePath -Encoding utf8
$store = $storeResponse.Content | ConvertFrom-Json

if (@($store.PSObject.Properties.Name) -join ',' -ne 'installed,recommended,all') {
  throw 'Store response does not have the stable three-view shape'
}
foreach ($view in @('installed','recommended','all')) {
  if ($null -eq $store.$view -or $store.$view -isnot [array]) {
    throw "Store view is not an array: $view"
  }
}

$unauthorized = Invoke-WebRequest "$BaseUrl/api/extensions/store" -UseBasicParsing -SkipHttpErrorCheck
if ($unauthorized.StatusCode -ne 401) { throw 'Store API did not fail closed without admin auth' }
```

Apply these assertions to the decoded response:

1. **Three views and catalog stability:** `installed`, `recommended`, and
   `all` are present as arrays. Every `all` item has at least `id`, `name`,
   `repository`, `status`, `manifest_version`, `license`, `provenance`,
   `permissions`, `network_exposure`, `data_sensitivity`,
   `operational_risk`, `adapter_ref`, and `actions`. Every `actions` value is
   an array.
2. **Unknown facts fail closed:** find the `chatgpt2api` item in
   `recommended`; require `confidence == "unknown"`, `actions` empty, and
   `unknown_facts` containing `os`, `cpu_cores`, `memory_mb`, `disk_mb`,
   `docker_version`, `compose_version`, `python_version`, and `uv_version`.
   Require that no unknown field is rendered as a guessed value in
   `reasons`; the expected reason form is `field=未观测` for each absent fact.
3. **Planned rows:** in `all`, every item whose `status` is `planned`,
   `repository_unverified`, or `unknown` must have `actions == []`. In
   particular, `grok2api` is planned and `kiro2api` is repository-unverified
   at this commit; their catalog metadata may be public, but they are not
   executable.
4. **External row:** in `installed`, find `instance_id == "external-w3"`;
   require `ownership == "external"` and `actions == []`. Do not call any
   management or adoption endpoint. The available `chatgpt2api` catalog item
   may carry a backend-derived `deploy` action in `all`, but no W3 step may
   execute it and it does not turn the synthetic external instance into a
   managed instance.
5. **Metadata non-leak:** serialize the full Store response and assert it does
   not contain these field names or values: `container_id`, `container_name`,
   `install_dir`, `data_dir`, `compose_project`, `service_port`, `image`,
   `host`, `host_key`, `network_url`, `credentials`, `private_key`,
   `password`, `token`, or the synthetic admin/Push key values. The public
   response may include non-sensitive `instance_id`, `instance_status`, and
   `ownership` for the installed projection.

The following PowerShell assertion block is executable without browser or npm:

```powershell
$plannedStatuses = @('planned','repository_unverified','unknown')
$planned = @($store.all | Where-Object { $plannedStatuses -contains $_.status })
if (-not $planned -or @($planned | Where-Object { @($_.actions).Count -ne 0 }).Count) {
  throw 'planned or unverified Store row exposed an action'
}

$recommended = @($store.recommended | Where-Object { $_.id -eq 'chatgpt2api' })
if ($recommended.Count -ne 1 -or $recommended[0].confidence -ne 'unknown' -or @($recommended[0].actions).Count -ne 0) {
  throw 'unknown facts did not fail closed'
}
$expectedUnknown = @('os','cpu_cores','memory_mb','disk_mb','docker_version','compose_version','python_version','uv_version')
foreach ($field in $expectedUnknown) {
  if (@($recommended[0].unknown_facts) -notcontains $field) { throw "missing unknown fact: $field" }
}

$external = @($store.installed | Where-Object { $_.instance_id -eq 'external-w3' })
if ($external.Count -ne 1 -or $external[0].ownership -ne 'external' -or @($external[0].actions).Count -ne 0) {
  throw 'external Store row was not read-only'
}

$publicText = Get-Content -LiteralPath $StoreBeforePath -Raw
foreach ($forbidden in @('container_id','container_name','install_dir','data_dir','compose_project','service_port','image','host_key','network_url','credentials','private_key','password','token',$AdminKey,$PushKey)) {
  if ($publicText.Contains($forbidden)) { throw "Store response leaked forbidden text: $forbidden" }
}
```

The assertion for `host` should be applied to public field names if the
response is parsed recursively; do not reject the loopback URL used to contact
the local API merely because it appears in the test command. The fixture's
private operational paths and image must not appear in the Store body.

## 8. Restart State Behavior

The restart check verifies that the public state remains the same and that the
application does not invent facts or acquire actions after a process restart.
It does not test deployment-task recovery, which is outside W3.

```powershell
$BeforeCanonical = ($store | ConvertTo-Json -Depth 30 -Compress)
docker compose @Compose restart genbox
if ($LASTEXITCODE -ne 0) { throw 'Compose restart failed' }

$deadline = (Get-Date).AddSeconds(90)
do {
  $health = docker inspect $Container --format '{{.State.Health.Status}}'
  if ($health -eq 'healthy') { break }
  Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)
if ($health -ne 'healthy') { throw "container was not healthy after restart: $health" }

$StoreAfterPath = Join-Path $EvidenceRoot 'store-after-restart.json'
$afterResponse = Invoke-WebRequest "$BaseUrl/api/extensions/store" -Headers $headers -UseBasicParsing
if ($afterResponse.StatusCode -ne 200) { throw 'Store API failed after restart' }
$afterResponse.Content | Set-Content -LiteralPath $StoreAfterPath -Encoding utf8
$after = $afterResponse.Content | ConvertFrom-Json
$AfterCanonical = ($after | ConvertTo-Json -Depth 30 -Compress)
if ($BeforeCanonical -ne $AfterCanonical) { throw 'Store projection changed across restart' }
```

Success requires the same three views, the same unknown facts, empty planned
and external actions, and the same metadata redaction after restart. A changed
projection, newly guessed fact, newly available external action, or lost
fixture state is a failure even if the container is healthy.

## 9. Teardown And Failure Evidence

The run must use a `try/finally` wrapper around startup and acceptance. Teardown
is mandatory on both pass and fail and is limited to the generated project,
container, network, image tag, temporary clone, and temporary storage.

```powershell
$RunFailed = $false
try {
  # Execute Sections 3 through 8 here.
}
catch {
  $RunFailed = $true
  $_ | Out-String | ForEach-Object {
    $_ -replace [regex]::Escape($AdminKey), '[REDACTED-ADMIN-KEY]' `
       -replace [regex]::Escape($PushKey), '[REDACTED-PUSH-KEY]'
  } | Set-Content (Join-Path $EvidenceRoot 'failure-summary.txt') -Encoding utf8
  throw
}
finally {
  docker compose @Compose down --volumes --remove-orphans 2>$null
  docker rm -f $Container 2>$null
  docker image rm $Image 2>$null
  if (-not $RunFailed) {
    Remove-Item -LiteralPath $RunRoot -Recurse -Force -ErrorAction SilentlyContinue
  }
}
```

Failure handling rules:

- Before teardown, retain only sanitized status, health, mount shape, response
  bodies, and the redacted failure summary under the temporary evidence root.
  Do not save `.env`, Compose-expanded configuration, environment inspection,
  raw command lines containing keys, or unredacted logs.
- If startup or HTTP assertions fail, stop immediately; do not retry a failed
  deploy path, change the fixture to obtain a pass, or contact any remote
  service. The failed run remains `FAIL` or `BLOCKED`, not partial acceptance.
- If teardown itself fails, keep `$RunRoot` and record the exact cleanup command
  and non-secret error. Do not manually delete an unknown Docker resource by a
  broad name or prune all Docker resources. Resolve only the recorded project,
  container, image, and temporary path after inspection.
- On a clean pass, remove the full temporary root, including `.env`, seed
  helper, storage, response bodies, and image tag. Do not commit generated
  evidence. If a separate evidence record is required, retain only redacted
  summaries with the exact commit SHA and a `LOCAL CLEAN DEPLOYMENT` label.

## 10. Acceptance Decision

The local W3 run is `PASS` only when all of the following are true:

- The clone is clean and exactly at `1383f537ad4c1602e6586b6437c939dc80378f5c`.
- The image is built from that clone, the Compose project/container are unique,
  and the storage bind mount is unique and temporary.
- Startup reaches healthy on the random `127.0.0.1` port with production auth
  enabled and synthetic credentials only.
- The Store HTTP response has exactly the three required views.
- Partial facts produce explicit unknown facts and no recommendation action.
- Planned and repository-unverified entries have no actions.
- The synthetic external installed row is advisory/read-only with no actions.
- Public Store metadata contains no private operational fields, paths, image
  identity, credentials, or synthetic secret values.
- The exact public projection survives restart unchanged.
- Teardown removes the generated Compose resources and temporary secrets.

A pass is still only **LOCAL CLEAN DEPLOYMENT / SYNTHETIC STORE API EVIDENCE**.
It does not prove a VPS target, SSH authority, remote Docker/Compose facts,
private-network reachability, real sender integration, real media transfer,
production non-mutation, published-image provenance, browser behavior, or
adapter lifecycle completion. It cannot close Phase 10 by itself.

## Handoff

AGENT: Phase 10 clean deployment W3 方案审计 Agent
WAVE: W3 local clean deployment plan and Store API acceptance
STATUS: PLAN READY; no execution evidence yet
INPUT_HEAD: `1383f537ad4c1602e6586b6437c939dc80378f5c`
CHANGED_FILES: `docs/PHASE10-CLEAN-DEPLOYMENT-PLAN-20260823.md`
RESULT: Executable local plan prepared with isolated clone, exact SHA, random loopback port, unique Compose resources, synthetic secret handling, Store API-only acceptance, restart comparison, and mandatory teardown.
EVIDENCE: Required lifecycle, architecture, deployment, README/configuration, packaging, extension, Store contract, and frontend contract sources were reviewed read-only.
UNKNOWN: No runtime command in this plan has been executed. Local Docker/Compose availability and all runtime facts remain undiscovered. No live remote target evidence exists.
RISKS: A local fixture can prove projection behavior and persistence only; it cannot prove SSH discovery, remote ownership, private networking, published artifact provenance, or production non-mutation. The current Compose storage boundary is a unique bind mount, not a named volume.
NEXT: Obtain explicit authorization for the local-only run, execute Sections 3-9, retain sanitized results, and keep Phase 10 In Progress unless all separate acceptance gates are met.
