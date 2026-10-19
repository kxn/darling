#!/usr/bin/env python3
"""Scope Xcode's library environment to xcrun in a private runtime root."""
from pathlib import Path
import fcntl, hashlib, json, runpy, shlex, shutil, subprocess

root = Path(__file__).resolve().parent.parent
parent = runpy.run_path(str(root / 'scripts/metadata-root-name-runtime-profile.py'))
digest = lambda name: hashlib.sha256((root / name).read_bytes()).hexdigest()
runtimes = {}
with (root / 'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    for diagnostic in [False, True]:
        p = parent['profile'](diagnostic=diagnostic)
        label = 'diagnostic' if diagnostic else 'normal'
        folder = root / ('runtime/xcode-tool-dispatch-v2-' + label)
        folder.mkdir(exist_ok=True)
        variant = folder / 'darling-root'
        assert not variant.exists(), 'Keep existing tested variants immutable'
        base = root / p['metadata_root_name_selected_runtime']['variant_root']
        subprocess.run(['cp', '-a', '--reflink=auto', str(base), str(variant)], check=True)
        original = folder / 'original-tools/xcrun'
        original.parent.mkdir(exist_ok=True)
        shutil.copy2(base / 'usr/bin/xcrun', original)
        environment = [arg for arg in p['command'] if arg.startswith(('DYLD_LIBRARY_PATH=', 'DYLD_FRAMEWORK_PATH='))]
        wrapper = variant / 'usr/bin/xcrun'
        wrapper.unlink()
        wrapper.write_text('#!/bin/sh\n' + '\n'.join('export ' + shlex.quote(arg) for arg in environment) +
                           '\nexec ' + shlex.quote('/Volumes/SystemRoot/workspace/' + str(original.relative_to(root))) + ' "$@"\n')
        wrapper.chmod(0o755)
        selected = {key: dict(value) for key, value in p['source_runtime'].items()}
        for item in selected.values():
            target = folder / Path(item['path']).name
            shutil.copy2(root / item['path'], target)
            item.update(path=str(target.relative_to(root)), sha256=digest(target))
        binding = str((variant / 'System/Library/CoreServices/SystemVersion.plist').relative_to(root))
        runtimes[label] = dict(previous_source_runtime=p['source_runtime'], source_runtime=selected,
            variant_root=str(variant.relative_to(root)), system_version_binding=binding,
            system_version_binding_sha256=digest(binding),
            files={str(path.relative_to(root)): digest(path) for path in [wrapper, original]},
            test_only_permissive_coreservices_policy=diagnostic)
(root / 'artifacts/xcode-tool-dispatch-stage-v2.json').write_text(json.dumps(dict(runtimes=runtimes,
    persistent_prefix_modified=False, original_xcrun_shim_preserved=True, default_entry_promoted=False), indent=2) + '\n')
