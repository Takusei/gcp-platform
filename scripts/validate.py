#!/usr/bin/env python3
"""Validate release wiring offline. Does not build images, deploy, or call APIs."""
import ast
import argparse
import json
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent


# GitHub uses YAML 1.2, where "on" is a string, unlike PyYAML's YAML 1.1 default.
class WorkflowLoader(yaml.BaseLoader):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shared-only', action='store_true', help='Validate shared workflow without sibling repositories (CI)')
    args = parser.parse_args()
    targets = json.loads((ROOT / "targets.json").read_text())
    shared_path = ROOT / ".github/workflows/deploy-cloud-run.yml"
    for path in (ROOT / '.github/workflows').glob('*.yml'):
        document = yaml.load(path.read_text(), Loader=WorkflowLoader)
        assert 'on' in document and 'jobs' in document, path
        for job in document['jobs'].values():
            assert job.get('runs-on') == 'ubuntu-24.04', (path, 'Pin the runner OS')
    shared = yaml.load(shared_path.read_text(), Loader=WorkflowLoader)
    assert shared["jobs"]["deploy"]["if"] == "github.ref == 'refs/heads/main' && github.event_name == 'workflow_dispatch'"
    declared = set(shared["on"]["workflow_call"]["inputs"])
    secrets = set(shared["on"]["workflow_call"]["secrets"])
    expected_secrets = {"workload_identity_provider", "deploy_service_account"}
    assert secrets == expected_secrets
    assert len(targets) == 10
    assert len({t["repository"] for t in targets}) == 8
    assert len({(t['kind'], t['target']) for t in targets}) == len(targets)
    for target in targets:
        if args.shared_only:
            continue
        repo = WORKSPACE / target["local_path"]
        path = repo / ".github/workflows" / target["workflow"]
        workflow = yaml.load(path.read_text(), Loader=WorkflowLoader)
        assert set(workflow["on"]) == {"workflow_dispatch"}, (path, "Deployment must be manual only")
        assert workflow["jobs"]["deploy"]["if"] == "github.ref == 'refs/heads/main'"
        job = workflow["jobs"]["deploy"]
        assert job["uses"] == "Takusei/gcp-platform/.github/workflows/deploy-cloud-run.yml@824dfd91ae9543423fb8669fb61d87cd3497d4c6"
        assert set(job["with"]) == declared
        assert set(job["secrets"]) == secrets
        for field in ("kind", "target", "registry_repository", "image_name", "build_context", "dockerfile"):
            assert job["with"][field] == target[field], (path, field)
        assert (repo / target["dockerfile"]).is_file()
        context = repo / target["build_context"]
        assert context.is_dir()
        ignores = (context / ".dockerignore").read_text().splitlines()
        for pattern in (".env", ".env.*", ".venv", "gha-creds-*.json"):
            assert pattern in ignores, (context, pattern)
        assert "gha-creds-*.json" in (repo / ".gitignore").read_text().splitlines()
        remote = subprocess.check_output(["git", "-C", str(repo), "remote", "get-url", "origin"], text=True).strip()
        assert target["repository"] in remote
        for step in workflow.get("jobs", {}).values():
            assert "secrets: inherit" not in str(step)
    if not args.shared_only:
        assert not (WORKSPACE / "api-collections/.github/workflows/docker-publish.yml").exists()
    steps = shared["jobs"]["deploy"]["steps"]
    uses = [s.get("uses", "") for s in steps]
    assert uses.index("docker/build-push-action@v7") < uses.index("google-github-actions/auth@v3")
    assert "jobs execute" not in shared_path.read_text()
    for step in steps:
        if "run" in step:
            subprocess.run(["bash", "-n"], input=step["run"], text=True, check=True)
            if "python3 - <<'PY'" in step["run"]:
                source = step["run"].split("python3 - <<'PY'\n", 1)[1].split("\nPY", 1)[0]
                ast.parse(source)
    for path in (ROOT / "scripts").glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))
    for path in ROOT.rglob("*.tf"):
        assert path.read_text().count("{") == path.read_text().count("}"), path
    print("PASS: " + ("shared workflow" if args.shared_only else "10 callers / 8 repositories, paths, remotes, credential exclusions") + ", shell/Python syntax")
    print("Terraform brace sanity only; run terraform fmt/validate and actionlint before publication.")


if __name__ == "__main__":
    main()
