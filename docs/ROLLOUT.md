# Setup and rollout

Run the commands below yourself in your normal terminal, from
`/Users/jaycen/workspace/projects/gcp-platform`, unless another directory is shown.
Publishing caller workflows does not deploy anything. Deployments run only when
you choose **Actions → Deploy TARGET → Run workflow → main → Run workflow** in
the application repository. The workflow file must first be present on the
repository's default branch for GitHub to show the manual-run button.

## 1. Confirm live targets first

Prerequisites: Docker Desktop, Python 3, GitHub CLI, gcloud, Terraform >= 1.6 and
< 2.0. Terraform/actionlint were unavailable in the preparation environment.

```bash
gcloud auth login
gcloud auth application-default login
gh auth login
python3 scripts/inventory.py
gh api users/Takusei --jq .id
```

Inventory is read-only. It saves only allowlisted metadata to ignored
`inventory.local.json`, and exits with failure if any documented target is absent.
Confirm the current image registry/repository and runtime service accounts. If a
target or image repository differs, update `targets.json`, its caller workflow,
and `terraform/bootstrap/main.tf` registry list before proceeding. The inventory
does not certify that the documented registry names exist:

```bash
gcloud artifacts repositories list --project=dev-projects-476011 --location=asia-northeast1
```

Existing deployment guides use `latest`; this pipeline deliberately leaves that
tag alone and deploys commit-tagged images by digest. Check there are no external
systems relying on `latest` being updated by every release.

## 2. Validate the shared workflow revision first

```bash
python3 scripts/validate.py
actionlint .github/workflows/deploy-cloud-run.yml
terraform fmt -recursive terraform
terraform -chdir=terraform/bootstrap init -backend=false
terraform -chdir=terraform/bootstrap validate
terraform -chdir=terraform/modules/cloud-run-service init -backend=false
terraform -chdir=terraform/modules/cloud-run-service validate
terraform -chdir=terraform/modules/cloud-run-job init -backend=false
terraform -chdir=terraform/modules/cloud-run-job validate
```

`validate.py` needs PyYAML (`uv run --with pyyaml python scripts/validate.py` if
your interpreter does not already provide it). Review the generated files, then:

```bash
git add .
git commit -m "Add shared Cloud Run deployment workflows and GCP bootstrap"
gh repo create Takusei/gcp-platform --public --source=. --remote=origin --push
gh run list --workflow validate.yml --limit 5
```

Wait for `Validate shared deployment` to succeed (use `gh run watch RUN_ID`).
The application callers use `@main`; no release tag is needed.

The existing remote is **Takusei/gcp-platform** (the local folder is
`gcp-platform`). If that remote already exists, skip `gh repo create` above and
push your reviewed changes with your normal Git workflow.

Application callers use the latest shared workflow on `main`:

```text
Takusei/gcp-platform/.github/workflows/deploy-cloud-run.yml@main
```

No version tag or caller SHA update is required. Validate shared workflow changes
before merging them into `gcp-platform/main`; subsequent manually triggered
application deployments use that updated workflow. Deployment remains manual-only.

If using a private shared repository, explicitly enable workflow access in
Settings → Actions → General and confirm callers can access it.

## 3. Bootstrap GCP authentication

Enable the required APIs if they are not already enabled:

```bash
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com run.googleapis.com artifactregistry.googleapis.com --project=dev-projects-476011
```

Create a dedicated private state bucket if you do not already have an appropriate
one. The following name must be globally available; choose another if needed.

```bash
gcloud storage buckets create gs://dev-projects-476011-portfolio-tfstate --project=dev-projects-476011 --location=asia-northeast1 --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://dev-projects-476011-portfolio-tfstate --versioning
cp terraform/bootstrap/terraform.tfvars.example terraform/bootstrap/terraform.tfvars
```

Edit `terraform.tfvars`: set your numeric GitHub user ID and replace the example
runtime accounts with **all** identities printed by `inventory.py`. These inputs
are deliberately required rather than guessed.

```bash
terraform -chdir=terraform/bootstrap init -reconfigure -backend-config="bucket=dev-projects-476011-portfolio-tfstate" -backend-config="prefix=portfolio/bootstrap"
terraform -chdir=terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=terraform/bootstrap apply bootstrap.tfplan
terraform -chdir=terraform/bootstrap output github_secrets
```

Review the plan: it should create a dedicated WIF pool/provider, deployment
identity and IAM memberships. It should not replace existing Cloud Run workloads,
registries, runtime identities, application secrets, or databases. If the dedicated
pool/deployer already exists, import it rather than trying to create it again.
Commit `.terraform.lock.hcl` after successful initialization to pin providers.

## 4. Configure GitHub authentication settings

```bash
python3 scripts/configure_github_secrets.py
python3 scripts/configure_github_secrets.py --apply
```

The first command previews; the second writes these two repository secrets to the
nine caller repositories using Terraform's outputs:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

No OpenAI key, database password, or service-account JSON key belongs in this
workflow. Existing application secrets stay in GCP Secret Manager.

## 5. Pilot api-collections, then roll out the other callers

First review and commit the Terraform image-ignore change in `api-collections`
and `knowledge-search`; existing Terraform/state stays where it is. Do not run an
old Terraform checkout after enabling the image deployment pipeline.

In `api-collections`, review the diff and commit/push the new caller, removal of
the old build-only workflow, Docker exclusions, and Terraform lifecycle change:

```bash
cd /Users/jaycen/workspace/projects/api-collections
git diff --check
git status --short
git add .github/workflows .dockerignore .gitignore terraform/cloudrun.tf deployment.md
git commit -m "Deploy Cloud Run images through shared GitHub workflow"
git push origin main
gh run list --workflow deploy-fastapi-service.yml --limit 5
```

If your current branch is not `main`, use your normal PR/merge process instead
of the last push command. After merging/pushing, open **Actions → Deploy
fastapi-service → Run workflow**, select **main**, and click **Run workflow**.
The push itself does not deploy.

The workflow summary shows the exact image digest. Service readiness is checked
without sending application requests or consuming model tokens. Check the UI/login
and a non-LLM health endpoint manually, where available. LLM functionality checks
consume live APIs and require your explicit decision to run them.

Roll out LINE, PPT, Real Estate, Knowledge Search, then the PDM backend and its Cloud Run ChatKit frontend, committing
only the files listed by `git status` for this task in each repository. Run
`actionlint` in each repository before publishing. Then manually run the desired
deployment workflow from **main** in each repository's Actions tab. Real Estate
has separate workflows for its agent, scraper, and embedding targets. Releases
use the main-branch commit selected when dispatched; other branches are rejected
by the deployment guard and GCP identity condition. Code pushes never trigger
these deployments.

For jobs, confirm the updated digest and existing Cloud Scheduler linkage. The
deployment never executes them; do not run the news-poster job just to test CI
because it can send LINE messages and consume model tokens.

## 6. Centralize infrastructure only after live inventory/state review

**Release automation is ready for setup; infrastructure consolidation is staged.**
The prepared central service/job modules are opt-in and are not instantiated by
bootstrap. Keeping existing state in place avoids recreating resources based on
incomplete deployment guides.

For existing Terraform-managed Knowledge Search and API resources:

1. Back up state with `terraform state pull` to a private ignored location.
2. First migrate each existing root configuration unchanged to a separate central
   directory/state prefix. Move its entire existing state/backend; do not import
   the same resources into a second active state.
3. Retire the old root configuration after the central plan shows no unintended
   changes. Keep database/secret resources intact; never run destroy.
4. Refactor into shared modules as a separate reviewed change using moved blocks
   or state moves where resource types permit. The API currently uses the v1
   Cloud Run resource; a move to the v2 module needs a supported migration/import,
   not an unreviewed address rename.

For manually managed services/jobs, first reproduce their full runtime config:
environment, secret references, identity, CPU/memory, concurrency/timeouts,
networking, ingress, mounts, commands, traffic, and schedules. The minimal modules
here cover basic single-container workloads; extend them for any extra live
features before importing. Never apply their defaults to an existing workload.

Example import addresses, **after** defining modules with the exact live config:

```bash
terraform import 'module.line_webhook.google_cloud_run_v2_service.this' projects/dev-projects-476011/locations/asia-northeast1/services/line-webhook-service
terraform import 'module.line_poster.google_cloud_run_v2_job.this' projects/dev-projects-476011/locations/asia-northeast1/jobs/line-poster-job
```

Do not apply a plan with unexpected replacements or runtime configuration changes.
The local stdio memory server and FastMCP-hosted PDM component remain outside this
rollout. All existing frontends keep their current hosting.

## Rollback

Read the previous image digest from the previous successful Actions summary or
the target's revision history. Redeploy it explicitly; do not rely on `latest`.

```bash
gcloud run services update SERVICE_NAME --image=PREVIOUS_IMAGE_DIGEST --project=dev-projects-476011 --region=asia-northeast1
gcloud run jobs update JOB_NAME --image=PREVIOUS_IMAGE_DIGEST --project=dev-projects-476011 --region=asia-northeast1
```

These are alternative commands for the relevant target. Job rollback changes its
next execution; it does not undo completed runs. For services using explicitly
pinned revision traffic, image updates may not move live traffic. The pipeline
fails verification if the new revision is not serving 100%; review and change
traffic intentionally rather than silently overwriting an existing canary split.

## Add the existing PDM ChatKit frontend

The `pdm-agent-chatkit-service` frontend is now the eleventh target (ninth caller
repository). Its lowercase `dockerfile` builds static assets without local `.env`
files. Nginx startup generates runtime-config.js from exactly two existing Cloud
Run settings: VITE_CHATKIT_WORKFLOW_ID and VITE_API_URL. These browser-visible
identifiers are not OpenAI API credentials. No additional GitHub build secrets
are required, and the backend keeps the OpenAI API key.

For an already-bootstrapped setup:

1. Run `python3 scripts/inventory.py` and confirm the frontend runtime identity is
   in `terraform/bootstrap/terraform.tfvars`'s runtime_service_accounts set.
2. Review/apply the updated bootstrap plan to add this repository to the WIF
   condition, grant its impersonation binding, and grant Artifact Registry writer
   on the existing pdm-agent-chatkit registry. With an unchanged runtime-account
   set, expect two IAM additions and one provider condition update, no destroys.
3. Run `python3 scripts/configure_github_secrets.py --repo Takusei/pdm-agent-chatkit --apply`.
4. Commit/push gcp-platform and the pdm-agent-chatkit changes to their main branches.
5. In pdm-agent-chatkit, manually run **Deploy pdm-agent-chatkit-service** on main.
6. Confirm runtime-config.js is served and the page loads. Test a real conversation
   only when you intend to consume OpenAI API tokens.

The image-only release retains both existing Secret Manager environment bindings.
If either setting is missing, container startup now fails clearly instead of
serving an unusable frontend. The session backend URL must already allow requests
from the frontend origin; no backend or ChatKit workflow configuration is changed.
