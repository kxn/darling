#!/usr/bin/env python3
"""Restore exact source bytes while retaining the base HEADs required by old scripts.

Use --clone to create missing source checkouts, or --verify to check restored files.
Never resets an existing checkout or overwrites unrelated edits.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--clone', action='store_true', help='download missing upstream source trees and submodules')
parser.add_argument('--verify', action='store_true', help='only verify base revisions and restored file bytes')
args = parser.parse_args()
manifest = json.loads((ROOT / 'checkpoint/source-manifest.json').read_text())
entries = sorted(manifest['repositories'], key=lambda r: len(Path(r['path']).parts))

def git(repo, *arguments, capture=False):
    command = ['git', '-C', str(repo), *arguments]
    if capture:
        return subprocess.check_output(command).decode().strip()
    subprocess.run(command, check=True)

def restored(entry):
    repo = ROOT / entry['path']
    for name, expected in entry['files'].items():
        path = repo / name
        if expected is None:
            if path.exists():
                return False
        elif (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']
              or bool(path.stat().st_mode & 0o111) != expected['executable']):
            return False
    return True

if args.clone and args.verify:
    parser.error('--clone and --verify are separate operations')

if args.clone:
    for entry in entries:
        repo = ROOT / entry['path']
        if (repo / '.git').exists():
            continue
        if repo.exists() and any(repo.iterdir()):
            raise SystemExit(f'Refusing to replace nonempty directory: {repo}')
        repo.mkdir(parents=True, exist_ok=True)
        git(repo, 'init')
        git(repo, 'remote', 'add', 'origin', entry['upstream_url'])
        git(repo, 'fetch', '--depth=1', 'origin', entry['base_commit'])
        git(repo, 'checkout', '--detach', 'FETCH_HEAD')
        if (repo / '.gitmodules').exists():
            git(repo, 'submodule', 'update', '--init', '--recursive', '--depth=1')

# Preflight every repository before changing any files.
pending = []
for entry in entries:
    repo = ROOT / entry['path']
    patch = ROOT / entry['patch']
    if not (repo / '.git').exists():
        raise SystemExit(f'Missing sources: {repo}; use --clone in a fresh workspace')
    if git(repo, 'rev-parse', 'HEAD', capture=True) != entry['base_commit']:
        raise SystemExit(f'Unexpected base revision: {repo}; no checkout/reset was attempted')
    if hashlib.sha256(patch.read_bytes()).hexdigest() != entry['patch_sha256']:
        raise SystemExit(f'Patch checksum mismatch: {patch}')
    if restored(entry):
        continue
    if args.verify:
        raise SystemExit(f'Source bytes differ: {repo}')
    git(repo, 'apply', '--check', str(patch))
    pending.append(entry)
for entry in pending:
    git(ROOT / entry['path'], 'apply', str(ROOT / entry['patch']))
    if not restored(entry):
        raise SystemExit(f'Post-apply verification failed: {entry["path"]}')
print(f'Verified exact checkpoint sources in {len(entries)} repositories; upstream base HEADs retained.')
