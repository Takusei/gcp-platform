# Portfolio GCP deployment

One release process for the eight GCP backend repositories: manually run a deployment from `main` in GitHub Actions →
Docker build (`linux/amd64`) → Artifact Registry → update the existing Cloud Run
service/job by immutable image digest. Vercel deployments stay separate.

**Prepared locally on 2026-10-24. Nothing has been published, applied, or deployed.**
Follow [the rollout guide](docs/ROLLOUT.md) before pushing caller changes.

## Contents

| Path | Purpose |
| --- | --- |
| `.github/workflows/deploy-cloud-run.yml` | Shared `workflow_call` release pipeline |
| `targets.json` | Ten deployment targets across eight repositories |
| `terraform/bootstrap/` | Dedicated GitHub WIF provider, deployer, and IAM grants |
| `terraform/modules/cloud-run-service/` | Opt-in service infrastructure module |
| `terraform/modules/cloud-run-job/` | Opt-in batch job infrastructure module |
| `scripts/inventory.py` | Live, sanitized target inventory; never prints env values |
| `scripts/configure_github_secrets.py` | Preview/apply repository authentication settings |
| `scripts/validate.py` | Offline checks of caller wiring, paths, shell syntax, and exclusions |
| `docs/ROLLOUT.md` | Publishing, GCP setup, verification, rollback, and ownership migration |

## Ownership

- Application repositories own their code, Dockerfiles, and small caller workflows.
- This repository owns the shared release implementation and new IAM bootstrap.
- Releases update only existing container images. Runtime identities, environment,
  secret bindings, network settings, resource limits, and job schedules are retained.
- Infrastructure Terraform owns runtime configuration; Actions owns release images.
  Existing Terraform resources now ignore image changes made by Actions.
- Existing application Terraform/state remains in place until a reviewed state
  migration. New workload modules are not instantiated automatically. This prevents
  an incomplete import from replacing live configuration.
- No new `LLM_MODEL` convention or model API migration is included in this release
  automation change. Knowledge Search's Terraform default now matches its existing
  `gpt-6-luna` application default; other model choices are unchanged.

## Deployment targets

| Repository | Kind | Existing target |
| --- | --- | --- |
| `api-collections` | service | `fastapi-service` |
| `knowledge-search` | service | `knowledge-search-backend` |
| `line-webhook` | service | `line-webhook-service` |
| `line-poster` | job | `line-poster-job` |
| `marp-ppt-agent` | service | `marp-ppt-agent-service` |
| `marp-ppt-api` | service | `marp-ppt-api-service` |
| `pdm-agent-backend` | service | `pdf-agent-backend-service` |
| `realEstate` | service | `rec-demo` |
| `realEstate` | job | `suumo-scraper-job` |
| `realEstate` | job | `suumo-embed-job` |

These names come from local deployment documentation/Terraform, not a verified
live inventory. In particular the PDM backend's `pdf` spelling is intentional.

Excluded: Vercel frontends; PDM FastMCP hosting/ChatKit workflow; local stdio Agentic
Memory MCP. Moving those requires separate transport/hosting work.

## Authentication and scope

The new `portfolio-github` WIF pool accepts only the eight named repositories,
the numeric GitHub owner ID, `refs/heads/main`, and manual-dispatch events only.
One dedicated deployment service account is shared across these personal projects:
it has project-wide Cloud Run Developer, writer on the ten existing Artifact
Registry repositories, and Service Account User on explicitly listed runtime
identities. It cannot change project IAM or read Secret Manager payloads.
Any approved caller can deploy other Cloud Run workloads within that project;
use separate deployers and resource-scoped IAM if stronger isolation is needed.

The shared workflow builds before obtaining credentials; `.dockerignore` and
`.gitignore` also exclude generated WIF credentials and local `.env` files.

## References

- [GitHub reusable workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows)
- [GCP Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
- [Cloud Run image deployment](https://docs.cloud.google.com/run/docs/deploying)

## Validation status

See `docs/VALIDATION.md` for exact checks and limitations. Live deployment and
model behavior must not be inferred from static validation.
