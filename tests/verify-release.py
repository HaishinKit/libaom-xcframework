"""Release checks without network access, pushes, or GitHub publication."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parent.parent


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.previous = Path.cwd()
        os.chdir(self.directory)
        for name in ['scripts', 'support']:
            shutil.copytree(ROOT/name, self.directory/name)
        shutil.copy2(ROOT/'Package.swift', 'Package.swift')
        # Both local checkouts and release-tag checkouts can run these tests.
        shutil.copy2('support/Package.swift', 'Package.swift')
        self.archive = Path('libaom.xcframework.zip')
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name in ['LICENSE', 'PATENTS', 'AUTHORS', 'SOURCES.json', 'fastfeat-LICENSE', 'vector-LICENSE']:
                archive.writestr('libaom.xcframework/Licenses/'+name, 'test fixture')
        self.head = 'a'*40

    def tearDown(self):
        os.chdir(self.previous)
        self.temp.cleanup()

    def script(self, name, *args):
        with patch.object(sys, 'argv', [name, *args]), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(self.directory/'scripts'/name), run_name='__main__')

    def prepare(self):
        self.script('release-manifest.py', 'release', 'v3.15.3')

    def test_manifest_and_checksum(self):
        self.prepare()
        self.script('release-manifest.py', 'check', 'v3.15.3')
        manifest = Path('Package.swift').read_text()
        self.assertIn('/releases/download/v3.15.3/libaom.xcframework.zip', manifest)
        self.assertIn(hashlib.sha256(self.archive.read_bytes()).hexdigest(), manifest)
        self.assertEqual(manifest, Path('dist/Package.swift').read_text())
        with self.assertRaises(SystemExit):
            self.script('release-manifest.py', 'check', 'v1.17.1')
        self.archive.write_bytes(b'changed artifact')
        with self.assertRaises(SystemExit):
            self.script('release-manifest.py', 'check', 'v3.15.3')
        self.script('release-manifest.py', 'local')
        self.script('release-manifest.py', 'check-local')

    def test_checksum_file_and_template_fail_closed(self):
        self.prepare()
        Path('libaom.xcframework.zip.sha256').write_text('incorrect')
        with self.assertRaises(SystemExit):
            self.script('release-manifest.py', 'check', 'v3.15.3')
        Path('support/Package.swift').write_text('unexpected template')
        with self.assertRaises(SystemExit):
            self.prepare()

    def test_invalid_tags(self):
        for tag in ['', '../bad', 'v01.2.3', 'v1.2.3-rc1', 'v1.2.3\n', '$(bad)']:
            with self.subTest(tag=tag), self.assertRaises(SystemExit):
                self.script('release-manifest.py', 'release', tag)

    def ci(self, version, results):
        with patch.dict(os.environ, RELEASE_VERSION=version, GITHUB_OUTPUT=str(self.directory/'output')):
            with patch('subprocess.check_output', side_effect=results):
                self.script('ci-release.py')

    def test_ci_normalization_and_duplicate_rejection(self):
        self.ci('3.15.3', ['', '[[]]'])
        self.assertEqual(Path('output').read_text(), 'tag=v3.15.3\n')
        for results in [['existing tag'], ['', '[[{"tag_name":"v3.15.3"}]]'],
                        [subprocess.CalledProcessError(1, ['git'])]]:
            with self.subTest(results=results), self.assertRaises((SystemExit, subprocess.CalledProcessError)):
                self.ci('v3.15.3', results)
        for version in ['v01.2.3', '1.2.3-rc', '1.2.3\n', 'bad']:
            with self.subTest(version=version), self.assertRaises(SystemExit):
                self.ci(version, [])

    def publish(self, values):
        with patch('subprocess.check_output', side_effect=values), patch('subprocess.run') as run:
            self.script('publish.py', 'v3.15.3')
            return run.call_args_list

    def test_publish_checks_git_and_remote_tag(self):
        self.prepare()
        calls = self.publish(['', self.head, self.head, self.head+'\trefs/tags/v3.15.3'])
        self.assertEqual(calls[-1].args[0][:4], ['gh', 'release', 'create', 'v3.15.3'])
        for values in [[' M Package.swift'], ['', self.head, 'b'*40],
                       ['', self.head, self.head, ''],
                       ['', self.head, self.head, 'b'*40+'\trefs/tags/v3.15.3']]:
            with self.subTest(values=values), self.assertRaises(SystemExit):
                self.publish(values)
        # Annotated tags must resolve to the exact release commit too.
        self.publish(['', self.head, self.head, 'b'*40+'\trefs/tags/v3.15.3\n'+self.head+'\trefs/tags/v3.15.3^{}'])

    def test_publish_rejects_missing_notices(self):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('unrelated', 'not a release')
        self.prepare()
        with self.assertRaises(KeyError):
            self.publish(['', self.head, self.head, self.head+'\trefs/tags/v3.15.3'])

    def git(self, *args):
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.STDOUT).strip()

    def test_release_commit_contains_remote_manifest(self):
        Path('.gitignore').write_text('/dist/\n/*.zip\n/*.sha256\n')
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Release Test')
        self.git('add', '.')
        self.git('commit', '-m', 'Initial fixture')
        original = self.git('rev-parse', 'HEAD')
        self.prepare()
        # An unexpected staged change must not become part of a release commit.
        Path('unexpected.txt').write_text('unexpected')
        self.git('add', 'unexpected.txt')
        failed = subprocess.run(['bash', 'scripts/commit-release.sh', 'v3.15.3'], capture_output=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(self.git('rev-parse', 'HEAD'), original)
        self.git('reset', '--', 'unexpected.txt')
        Path('unexpected.txt').unlink()
        subprocess.run(['bash', 'scripts/commit-release.sh', 'v3.15.3'], check=True, stdout=subprocess.DEVNULL)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'refs/tags/v3.15.3'))
        self.assertIn('/releases/download/v3.15.3/', self.git('show', 'v3.15.3:Package.swift'))
        self.assertEqual(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'), 'Package.swift')
        failed = subprocess.run(['bash', 'scripts/commit-release.sh', 'v3.15.3'], capture_output=True)
        self.assertNotEqual(failed.returncode, 0)


if __name__ == '__main__':
    unittest.main()
