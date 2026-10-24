"""Exercise actual embedded workflow guards with local resource fixtures only."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'asia-northeast1-docker.pkg.dev/example/registry/app@sha256:' + 'a' * 64


def embedded_python(step_name):
    workflow = yaml.load((ROOT / '.github/workflows/deploy-cloud-run.yml').read_text(), Loader=yaml.BaseLoader)
    step = next(s for s in workflow['jobs']['deploy']['steps'] if s.get('name') == step_name)
    return step['run'].split("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]


def service():
    return {
        'metadata': {'generation': 2},
        'spec': {'template': {'spec': {'serviceAccountName': 'runtime@example.iam.gserviceaccount.com', 'containers': [{'image': IMAGE}]}}},
        'status': {
            'conditions': [{'type': 'Ready', 'status': 'True'}],
            'observedGeneration': 2,
            'latestCreatedRevisionName': 'app-00002',
            'latestReadyRevisionName': 'app-00002',
            'traffic': [{'revisionName': 'app-00002', 'percent': 100}],
        },
    }


class ReleaseGuards(unittest.TestCase):
    def run_guard(self, resource, kind='service', preflight=False):
        with tempfile.TemporaryDirectory() as tmp:
            name = 'preflight.json' if preflight else 'cloud-run.json'
            (Path(tmp) / name).write_text(json.dumps(resource))
            step = 'Confirm existing target' if preflight else 'Verify deployed image and service readiness'
            with patch.dict(os.environ, RUNNER_TEMP=tmp, KIND=kind, IMAGE_DIGEST=IMAGE):
                exec(compile(embedded_python(step), '<workflow-guard>', 'exec'), {})

    def test_accepts_ready_new_revision_serving_all_traffic(self):
        self.run_guard(service())

    def test_rejects_old_image(self):
        data = service()
        data['spec']['template']['spec']['containers'][0]['image'] = 'old-image'
        with self.assertRaisesRegex(AssertionError, 'Deployed image differs'):
            self.run_guard(data)

    def test_rejects_stale_observed_generation(self):
        data = service()
        data['status']['observedGeneration'] = 1
        with self.assertRaisesRegex(AssertionError, 'Revision not observed'):
            self.run_guard(data)

    def test_rejects_unready_service(self):
        data = service()
        data['status']['conditions'][0]['status'] = 'False'
        with self.assertRaisesRegex(AssertionError, 'Service not ready'):
            self.run_guard(data)

    def test_rejects_failed_new_revision_even_if_old_revision_ready(self):
        data = service()
        data['status']['latestReadyRevisionName'] = 'app-00001'
        with self.assertRaisesRegex(AssertionError, 'Newest revision not ready'):
            self.run_guard(data)

    def test_rejects_pinned_or_split_traffic(self):
        data = service()
        data['status']['traffic'] = [{'revisionName': 'app-00001', 'percent': 100}]
        with self.assertRaisesRegex(AssertionError, 'not serving 100%'):
            self.run_guard(data)

    def test_multiple_containers_rejected_before_release(self):
        data = service()
        data['spec']['template']['spec']['containers'].append({'image': 'sidecar'})
        with self.assertRaisesRegex(AssertionError, 'Multiple containers'):
            self.run_guard(data, preflight=True)

    def test_job_nested_spec_verified_without_execution(self):
        data = {'spec': {'template': {'spec': {'template': {'spec': {'containers': [{'image': IMAGE}]}}}}}}
        self.run_guard(data, kind='job')
        self.run_guard(data, kind='job', preflight=True)
        data['spec']['template']['spec']['template']['spec']['containers'][0]['image'] = 'old'
        with self.assertRaisesRegex(AssertionError, 'Deployed image differs'):
            self.run_guard(data, kind='job')

    def test_inventory_does_not_export_environment_values(self):
        module_spec = importlib.util.spec_from_file_location('inventory', ROOT / 'scripts/inventory.py')
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        data = service()
        data['spec']['template']['spec']['containers'][0]['env'] = [
            {'name': 'PLAIN_CONFIG', 'value': 'private-value'},
            {'name': 'API_KEY', 'valueFrom': {'secretKeyRef': {'name': 'private-secret', 'key': 'latest'}}},
        ]
        with patch.object(module.subprocess, 'check_output', return_value=json.dumps(data)):
            output = module.inventory({'kind': 'service', 'target': 'app'}, 'example', 'asia-northeast1')
        encoded = json.dumps(output)
        self.assertNotIn('private-value', encoded)
        self.assertNotIn('private-secret', encoded)
        self.assertEqual(output['environment_names'], ['API_KEY', 'PLAIN_CONFIG'])


if __name__ == '__main__':
    unittest.main()
