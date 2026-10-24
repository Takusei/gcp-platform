import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'scripts/check_model_settings.py'
spec = importlib.util.spec_from_file_location('check_model_settings', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ModelSettingsTests(unittest.TestCase):
    def test_reports_only_model_values_and_secret_references(self):
        container = {'image': 'fixture-image', 'env': [
            {'name': 'LLM_MODEL', 'value': 'gpt-6-luna'},
            {'name': 'OPENAI_API_KEY', 'value': 'do-not-print'},
            {'name': 'DB_PASSWORD', 'value': 'also-private'},
            {'name': 'ANOTHER_KEY', 'valueFrom': {'secretKeyRef': {'name': 'existing-secret', 'key': 'latest'}}},
        ]}
        resource = {'spec': {'template': {'spec': {'containers': [container]}}}}
        report = module.summarize(resource, 'service')
        self.assertEqual(report['containers'][0]['model_environment'], {'LLM_MODEL': 'gpt-6-luna'})
        self.assertNotIn('do-not-print', json.dumps(report))
        self.assertNotIn('also-private', json.dumps(report))
        self.assertEqual(report['containers'][0]['secret_references']['ANOTHER_KEY']['name'], 'existing-secret')
        job = {'spec': {'template': {'spec': {'template': resource['spec']['template']}}}}
        self.assertEqual(module.summarize(job, 'job')['containers'], report['containers'])


if __name__ == '__main__':
    unittest.main()
