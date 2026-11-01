"""Publish an already committed and remotely tagged release, without replacing assets."""
from pathlib import Path
import subprocess
import sys
import zipfile


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: publish.py TAG')
    tag = sys.argv[1]
    subprocess.run([sys.executable, 'scripts/release-manifest.py', 'check', tag], check=True)
    if output('git', 'status', '--porcelain'):
        raise SystemExit('Commit changes before publishing.')
    head = output('git', 'rev-parse', 'HEAD')
    if output('git', 'rev-parse', f'refs/tags/{tag}^{{commit}}') != head:
        raise SystemExit('Release tag must point to HEAD.')
    repository = 'HaishinKit/libaom-xcframework'
    remote = output('git', 'ls-remote', f'https://github.com/{repository}.git',
                    f'refs/tags/{tag}', f'refs/tags/{tag}^{{}}')
    refs = dict(line.split()[::-1] for line in remote.splitlines())
    if refs.get(f'refs/tags/{tag}^{{}}', refs.get(f'refs/tags/{tag}')) != head:
        raise SystemExit('Push the release tag to GitHub before publishing.')
    # Check that the ZIP carries notices, even when recovering without build outputs.
    with zipfile.ZipFile('libaom.xcframework.zip') as archive:
        for name in ['LICENSE', 'PATENTS', 'AUTHORS', 'SOURCES.json', 'fastfeat-LICENSE', 'vector-LICENSE']:
            if not archive.read('libaom.xcframework/Licenses/' + name):
                raise SystemExit(f'Missing license/provenance file: {name}')
    subprocess.run(['gh', 'release', 'create', tag, '--repo', repository,
                    '--verify-tag', '--title', tag, '--generate-notes',
                    'libaom.xcframework.zip', 'libaom.xcframework.zip.sha256'], check=True)


if __name__ == '__main__':
    main()
