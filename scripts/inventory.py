#!/usr/bin/env python3
"""Read existing Cloud Run targets without printing environment/secret values."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory(target, project, region):
    resource = json.loads(subprocess.check_output([
        "gcloud", "run", "services" if target["kind"] == "service" else "jobs",
        "describe", target["target"], f"--project={project}", f"--region={region}",
        "--format=json",
    ], text=True))
    spec = resource["spec"]["template"]["spec"]
    if target["kind"] == "job":
        spec = spec["template"]["spec"]
    containers = spec["containers"]
    if len(containers) != 1:
        raise ValueError(f"{target['target']}: multiple containers require explicit release support")
    container = containers[0]
    # Only allowlisted fields leave this process. No env values or credentials.
    return {
        **target,
        "runtime_service_account": spec.get("serviceAccountName", ""),
        "current_image": container["image"],
        "environment_names": sorted(e["name"] for e in container.get("env", [])),
        "url": resource.get("status", {}).get("url"),
        "traffic": resource.get("status", {}).get("traffic", []),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="dev-projects-476011")
    parser.add_argument("--region", default="asia-northeast1")
    parser.add_argument("--output", type=Path, default=ROOT / "inventory.local.json")
    args = parser.parse_args()
    targets = json.loads((ROOT / "targets.json").read_text())
    results = []
    failed = []
    for target in targets:
        try:
            result = inventory(target, args.project, args.region)
            results.append(result)
            print(f"OK {target['kind']:7} {target['target']}: {result['runtime_service_account']}")
        except (subprocess.CalledProcessError, KeyError, ValueError) as exc:
            failed.append(target["target"])
            print(f"FAILED {target['target']}: {type(exc).__name__}")
    output = {
        "project_id": args.project,
        "region": args.region,
        "targets": results,
        "failed": failed,
        "runtime_service_accounts": sorted({t["runtime_service_account"] for t in results if t["runtime_service_account"]}),
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(f"Saved sanitized inventory to {args.output}")
    print("Runtime identities: " + json.dumps(output["runtime_service_accounts"]))
    if failed:
        raise SystemExit("Resolve missing/renamed targets before enabling deployment.")


if __name__ == "__main__":
    main()
