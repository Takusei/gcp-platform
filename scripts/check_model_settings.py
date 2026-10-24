#!/usr/bin/env python3
"""Read live Cloud Run model settings; never read Secret Manager payloads."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_VARIABLES = {
    "LLM_MODEL", "OPENAI_MODEL", "OPENAI_CHAT_MODEL", "OPENAI_EMBEDDINGS_MODEL",
    "AZURE_OPENAI_DEPLOYMENT_NAME", "EMBED_MODEL", "EMBEDDING_MODEL",
    "DISTILL_MODEL", "RERANKER_MODEL", "JEV_MODEL",
}


def summarize(resource, kind):
    spec = resource["spec"]["template"]["spec"]
    if kind == "job":
        spec = spec["template"]["spec"]
    return {
        "runtime_service_account": spec.get("serviceAccountName"),
        "containers": [
            {
                "image": container["image"],
                "model_environment": {
                    env["name"]: env.get("value", "[secret reference; value not read]")
                    for env in container.get("env", []) if env["name"] in MODEL_VARIABLES
                },
                "environment_names": sorted(env["name"] for env in container.get("env", [])),
                "secret_references": {
                    env["name"]: env["valueFrom"]["secretKeyRef"]
                    for env in container.get("env", [])
                    if "secretKeyRef" in env.get("valueFrom", {})
                },
                "resources": container.get("resources", {}),
            }
            for container in spec["containers"]
        ],
        "traffic": resource.get("status", {}).get("traffic", []),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="dev-projects-476011")
    parser.add_argument("--region", default="asia-northeast1")
    parser.add_argument("--target", help="Optional service/job name; default: all configured targets")
    args = parser.parse_args()
    targets = json.loads((ROOT / "targets.json").read_text())
    if args.target:
        targets = [target for target in targets if target["target"] == args.target]
        if not targets:
            parser.error("Target not found in targets.json")
    failed = []
    for target in targets:
        command = [
            "gcloud", "run", "services" if target["kind"] == "service" else "jobs",
            "describe", target["target"], f"--project={args.project}",
            f"--region={args.region}", "--format=json",
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            failed.append(target["target"])
            print(f"FAILED {target['target']}: gcloud could not describe target", flush=True)
            continue
        report = summarize(json.loads(result.stdout), target["kind"])
        print(json.dumps({"target": target["target"], "kind": target["kind"], **report}, indent=2), flush=True)
    print("Absent model variables mean no Cloud Run model override; the deployed image's code chooses the default.")
    if failed:
        raise SystemExit("Could not inspect: " + ", ".join(failed))


if __name__ == "__main__":
    main()
