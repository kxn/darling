#!/usr/bin/env python3
"""Restore the guest /var symlink while retaining the entire old upper directory."""
from pathlib import Path
from datetime import datetime, timezone
import fcntl, hashlib, json, os, shutil, stat
root = Path(__file__).resolve().parent.parent
prefix = root / 'runtime/state/prefix'
source = prefix / 'var'; target = prefix / 'private/var'
report_path = root / 'artifacts/overlay-var-repair.json'
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    if source.is_symlink():
        assert os.readlink(source) == 'private/var'
        print('Guest /var already points at private/var; retained prior migration evidence')
        raise SystemExit(0)
    assert source.is_dir() and target.is_dir()
    baseline = root / 'runtime/libdyld-source/darling-root/var'
    assert baseline.is_symlink() and os.readlink(baseline) == 'private/var'
    entries = []; copy = []; directories = []
    for current, children, files in os.walk(source, followlinks=False):
        for name in children + files:
            path = Path(current) / name; relative = path.relative_to(source)
            info = path.lstat(); destination = target / relative
            item = dict(path=str(relative), mode=stat.S_IMODE(info.st_mode), file_type=stat.S_IFMT(info.st_mode))
            if stat.S_ISLNK(info.st_mode): item['link'] = os.readlink(path)
            elif stat.S_ISREG(info.st_mode): item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            entries.append(item)
            exists = destination.exists() or destination.is_symlink()
            if stat.S_ISDIR(info.st_mode):
                assert not exists or destination.is_dir(), relative
                directories.append((path, destination))
            elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                if exists:
                    assert stat.S_IFMT(destination.lstat().st_mode) == item['file_type'], relative
                    if stat.S_ISREG(info.st_mode): assert destination.read_bytes() == path.read_bytes(), relative
                    else: assert os.readlink(destination) == item['link'], relative
                else: copy.append((path, destination))
            # Stale sockets/FIFOs stay in the full backup. Live IPC endpoints
            # must be created by the next private session, never copied.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    backup = root / 'runtime/overlay-var-repair' / stamp / 'upper-var'
    backup.parent.mkdir(parents=True)
    for path, destination in directories:
        if not destination.exists(): destination.mkdir(mode=stat.S_IMODE(path.stat().st_mode), parents=True)
    for path, destination in copy:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink(): destination.symlink_to(os.readlink(path))
        else: shutil.copy2(path, destination)
    pending = prefix / '.var-symlink.pending'; assert not pending.exists() and not pending.is_symlink()
    pending.symlink_to('private/var')
    source.rename(backup); pending.rename(source)
    for item in entries:
        path = backup / item['path']
        if 'sha256' in item: assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
        if 'link' in item: assert os.readlink(path) == item['link']
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), guest_link='/var -> private/var',
        original_upper_tree=str(backup.relative_to(root)), original_entries=entries,
        merged_missing_files=[str(p.relative_to(target)) for _, p in copy],
        baseline_link_matches=True, host_system_directories_changed=False,
        scope='Only the private guest overlay. Every original entry remains in a full backup; no conflicting files were overwritten.')
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Restored guest /var symlink; retained full upper-var backup:', backup)
