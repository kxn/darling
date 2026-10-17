#!/usr/bin/env python3
"""Select the file-mutation query kernel, keeping test capture isolated."""
from pathlib import Path
import argparse,fcntl,hashlib,json,runpy,shutil
root=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--capture',action='store_true');args=parser.parse_args()
p=runpy.run_path(str(root/'scripts/launchd-sandbox-source-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
stem='sandbox-fs-mutations-'+('capture' if args.capture else 'source')
folder=root/'runtime'/stem
build_name='artifacts/sandbox-fs-mutations-'+('capture-' if args.capture else '')+'kernel-build.json'
build=json.loads((root/build_name).read_text());assert build['complete_source_files']==878
assert bool(build.get('test_only_source_overrides'))==args.capture
selected={key:dict(item) for key,item in p['source_runtime'].items()}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    for key,item in selected.items():
        target=folder/Path(item['path']).name
        if key=='LINUXCODE_LIBSYSTEM_KERNEL':assert digest(target.relative_to(root))==build['binary_sha256']
        else:shutil.copy2(root/item['path'],target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target.relative_to(root)))
    for key,relative in [('LINUXCODE_LAUNCHD','sbin/launchd'),('LINUXCODE_LIBXPC','usr/lib/system/libxpc.dylib'),
                         ('LINUXCODE_LIBSYSTEM_KERNEL','usr/lib/system/libsystem_kernel.dylib'),
                         ('LINUXCODE_QUARANTINE','usr/lib/system/libquarantine.dylib'),
                         ('LINUXCODE_SANDBOX','usr/lib/system/libsystem_sandbox.dylib'),('LINUXCODE_LIBDYLD','usr/lib/system/libdyld.dylib')]:
        assert digest(build['variant_root']+'/'+relative)==selected[key]['sha256']
    report=dict(test_only=args.capture,kernel_build=build_name,kernel_build_sha256=digest(build_name),
                previous_source_runtime=p['source_runtime'],source_runtime=selected,
                extra_source_headers={n:digest(n) for n in [
                    'vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include/xnu_syscall/bsd/helper/misc/sandbox_fs.h',
                    'vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/CMakeLists.txt']},
                profile_application_implemented=False,full_xcode_build_ready=False)
    (root/('artifacts/'+stem+'-stage.json')).write_text(json.dumps(report,indent=2)+'\n')
print('Staged',stem,'; default runtime unchanged')
