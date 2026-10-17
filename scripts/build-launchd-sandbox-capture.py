#!/usr/bin/env python3
"""Build a test-only query transport alongside the unchanged production launchd."""
from pathlib import Path
import fcntl, hashlib, json, re, runpy, shutil, subprocess
root=Path(__file__).resolve().parent.parent
p=runpy.run_path(str(root/'scripts/launchd-sandbox-source-profile.py'))['profile']()
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/launchd-sandbox-capture';build.mkdir(exist_ok=True)
source=root/'vendor/darling/src/sandbox'
sdk=root/'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource=Path(subprocess.check_output(['clang-19','-print-resource-dir'],text=True).strip())
section=re.search(r'set\(sandbox_sources\s+([^)]*)\)',(source/'CMakeLists.txt').read_text())[1]
sources=[source/n for n in section.split()]; assert len(sources)==3
sources.append(root/'fixtures/hello/launchd-sandbox-query-capture.c')
objects=[];commands=[]
for path in sources:
    obj=build/(path.stem+'.o');objects.append(str(obj))
    command=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc',
             '-I',str(source),'-isystem',str(sdk/'usr/include'),'-isystem',str(resource/'include'),
             '-DDARLING','-DDARWIN','-DPLATFORM_MacOSX','-DTARGET_OS_MAC=1','-D_DARWIN_C_SOURCE',
             '-D__DARWIN_UNIX03','-fPIC','-O2','-Wno-deprecated-declarations',
             *(['-D__mac_syscall=darling_test_mac_syscall'] if path.name=='check.c' else []),
             '-c',str(path),'-o',str(obj)]
    commands.append(command);subprocess.run(command,check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';library=build/'libsystem_sandbox.dylib'
command=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
         '-syslibroot',str(guest),'-L',str(guest/'usr/lib/system'),'-install_name',
         '/usr/lib/system/libsystem_sandbox.dylib','-compatibility_version','1.0.0',
         '-ldyld','-lsystem_c','-lsystem_kernel','-lsystem_malloc',*objects,'-o',str(library)]
commands.append(command);subprocess.run(command,check=True)
exports=lambda n:set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/n)],text=True),re.M))
assert exports(p['source_runtime']['LINUXCODE_SANDBOX']['path'])<=exports(library.relative_to(root))
selected={key:dict(item) for key,item in p['source_runtime'].items()}
base=(root/selected['LINUXCODE_LIBDYLD']['path']).parent/'darling-root';variant=build/'darling-root'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    staging=build/'darling-root.pending'
    if staging.exists():shutil.rmtree(staging)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(staging)],check=True)
    shutil.copy2(library,staging/'usr/lib/system/libsystem_sandbox.dylib')
    for key,item in selected.items():
        target=build/Path(item['path']).name
        if key!='LINUXCODE_SANDBOX':shutil.copy2(root/item['path'],target)
        item.update(path=str(target.relative_to(root)),sha256=digest(target.relative_to(root)))
    if variant.exists():shutil.rmtree(variant)
    staging.replace(variant)
report=dict(test_only=True,production_launchd_unchanged=True,commands=commands,
            source_files={str(f.relative_to(root)):digest(f.relative_to(root)) for f in sources},
            library=str(library.relative_to(root)),library_sha256=digest(library.relative_to(root)),
            previous_source_runtime=p['source_runtime'],source_runtime=selected,
            variant_root=str(variant.relative_to(root)),profile_application_implemented=False)
(root/'artifacts/launchd-sandbox-capture-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Test-only query transport built; production Sandbox library remains unchanged')
