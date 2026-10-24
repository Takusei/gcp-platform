# Validation record — 2026-10-24

## Passed locally

- `scripts/validate.py`: eleven caller workflows across nine repositories; caller
  inputs/secrets match the reusable interface; manual-only triggers restricted to main; Dockerfile
  and context paths exist; GitHub remotes match the target inventory; credential
  exclusions exist at the actual Docker build-context roots; legacy API image-only
  workflow is removed; build precedes GCP authentication; embedded shell and
  Python syntax parse; central workflows parse as YAML and pin `ubuntu-24.04`.
- `scripts/validate.py --shared-only`: portable shared-repository checks pass
  without requiring sibling repositories (used by CI).
- `python -m unittest discover -s tests -v`: **9 tests passed**, exercising the
  actual embedded release guards with local fixture metadata. Covers ready
  service, stale image, stale observed generation, unready service, failed latest
  revision, traffic pinned to an old revision, multi-container rejection, nested
  job specs, and sanitized inventory output.
- `scripts/configure_github_secrets.py` preview lists precisely nine repositories
  and the two expected authentication secret names. `--apply` was not run.
- `git diff --check` passes across the nine application repositories; all were
  clean before this task. New files were checked separately for trailing whitespace.
- Terraform files have balanced braces. This is a basic sanity check, not HCL or
  provider-schema validation.

Local Python checks used the already-installed Python/PyYAML from
`agents/agentic-memory-mcp/.venv`; no dependencies in that project were changed.

## Not run / environment limits

- `terraform fmt`, initialization, and provider validation: Terraform unavailable;
  downloading its binary failed because shell network DNS is restricted.
- `actionlint`: unavailable; downloading its binary failed for the same reason.
- Container builds: Docker socket access is denied in this session. Build success
  and runtime startup are not established by the static checks.
- Live inventory: gcloud could not open/write its credential database under the
  restricted filesystem. Existing service/job names and registries remain based
  on local deployment guides/Terraform until `scripts/inventory.py` is run in the
  user's terminal.
- No GitHub repository was created remotely; no commits, pushes, Actions secret
  writes, Terraform plans/applies, cloud deployments, job executions, LINE
  messages, or live model requests were performed.

`validate.yml` runs the offline tests plus real Terraform provider validation in
GitHub. Run the rollout guide's local Terraform/actionlint checks first, and let
that validation workflow pass before merging shared workflow changes into main.

## Actions runtime maintenance

Updated both central workflows to `ubuntu-24.04` and Node.js 24 action releases:
checkout v6, setup-python v6, setup-terraform v4, setup-buildx-action v4, and
build-push-action v7. Verified the upstream action manifests declare `node24`.
Google auth/setup-gcloud remain on their existing Node.js 24 v3 releases.
The build-order validator now follows build-push-action v7 and checks OS pinning.
Manual-only deployment guards are retained. The Terraform CLI stays at 1.9.8.

These changes address the Node.js 20 annotations and avoid the automatic
ubuntu-latest OS migration. They require a new GitHub run to verify remotely;
local YAML/shell checks and all nine fixture tests pass.

## Caller reference update

All eleven application deployment callers reference
`Takusei/gcp-platform/.github/workflows/deploy-cloud-run.yml@main`.
The local validator checks this same reference. Future shared workflow changes
on main take effect for subsequent manual application deployments without
updating each caller. Deployment triggers remain manual-only.

## PDM frontend onboarding

Added pdm-agent-chatkit-service as an eleventh target and ninth caller repository.
Updated WIF repository allowlist, impersonation membership, registry IAM, and
validation counts. The secret configuration script supports `--repo` for adding
only the new caller. Offline wiring checks, actionlint, Terraform formatting,
and central fixture tests pass. Terraform provider validation cannot complete in
this sandbox because the provider plugin fails its handshake. No apply was run.
The frontend's seven runtime/session tests, production Vite build without build
configuration, TypeScript, and full frontend ESLint checks pass. A full Docker/Nginx container build
and live Cloud Run/session checks were not performed.
