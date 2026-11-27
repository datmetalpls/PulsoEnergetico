"""Host-side checks: python3 -m unittest discover -s backend -p test_deployment.py."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless((ROOT / 'scripts/deploy-ec2.sh').exists(), 'Deployment sources excluded from runtime image')
class DeploymentTests(unittest.TestCase):
    def test_ec2_requires_every_private_credential(self):
        script = (ROOT / 'scripts/deploy-ec2.sh').read_text().split('\ncmd=')[0]
        script += '\npublic_host() { return 0; }\nset_env_var() { :; }\nlog() { :; }\nconfigure_env\n'
        keys = ['DJANGO_SECRET_KEY', 'POSTGRES_PASSWORD', 'DEMO_CUENCA_PASSWORD',
                'DEMO_PUENTE_PASSWORD', 'DEMO_OBSERVER_PASSWORD', 'DEMO_OPERATOR_PASSWORD']
        example_text = (ROOT / '.env.example').read_text()
        examples = dict(line.split('=', 1) for line in example_text.splitlines()
                        if '=' in line and not line.startswith('#'))
        private = {key: 'private-test-' + key for key in keys}
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / '.env.example').write_text(example_text)

            def run(values):
                (app / '.env').write_text('\n'.join(f'{k}={v}' for k, v in values.items()))
                return subprocess.run(['bash', '-c', script], env={**os.environ, 'APP_DIR': directory},
                                      capture_output=True, text=True)

            valid = run(private)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            for key in keys:
                for value in [None, '', examples[key], '"' + examples[key] + '"',
                              examples[key] + ' # public', '"' + examples[key] + '" # public']:
                    values = dict(private)
                    if value is None:
                        del values[key]
                    else:
                        values[key] = value
                    with self.subTest(key=key, value_kind='missing' if value is None else 'invalid'):
                        result = run(values)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(key, result.stderr)
                        self.assertNotIn(examples[key], result.stderr)

    def test_angular_failures_abort_build_commands(self):
        commands = [line[4:] for line in (ROOT / 'Dockerfile').read_text().splitlines()
                    if line.startswith('RUN npm')]
        self.assertEqual(len(commands), 2)
        for command in commands:
            with self.subTest(command=command):
                result = subprocess.run(['sh', '-c', 'npm() { return 71; }; ' + command],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 71)
        ignored = (ROOT / '.dockerignore').read_text().splitlines()
        for path in ['docs/', 'audits/', 'design/', 'scripts/', '**/*.md', '**/node_modules', '**/dist']:
            self.assertIn(path, ignored)


if __name__ == '__main__':
    unittest.main()
