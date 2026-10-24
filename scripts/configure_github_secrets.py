#!/usr/bin/env python3
"""Preview Actions secret setup; --apply writes secrets to the configured callers."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--repo", help="Configure one repository in owner/name form (default: all callers)")
    args = parser.parse_args()
    repos = sorted({t["repository"] for t in json.loads((ROOT / "targets.json").read_text())})
    if args.repo:
        if args.repo not in repos:
            parser.error("Repository is not in targets.json")
        repos = [args.repo]
    for repo in repos:
        print(f"{'Configure' if args.apply else 'Would configure'} {repo}: GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_SERVICE_ACCOUNT")
    if not args.apply:
        print("Run again with --apply after reviewing terraform/bootstrap outputs.")
        return
    values = json.loads(subprocess.check_output([
        "terraform", f"-chdir={ROOT / 'terraform/bootstrap'}", "output", "-json", "github_secrets",
    ], text=True))
    for repo in repos:
        for name in ("GCP_WORKLOAD_IDENTITY_PROVIDER", "GCP_SERVICE_ACCOUNT"):
            subprocess.run(["gh", "secret", "set", name, "--repo", repo], input=values[name], text=True, check=True)


if __name__ == "__main__":
    main()
