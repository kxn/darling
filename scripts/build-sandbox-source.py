#!/usr/bin/env python3
"""Build complete Darling libsystem_sandbox with modern user-space wrappers.

This does not implement the absent Sandbox MAC policy in darlingserver.
"""
from pathlib import Path
import fcntl,hashlib,json,re,shutil,subprocess
root=Path(__file__).resolve().parent.parent
source=root/'vendor/darling/src/sandbox';build=root/'runtime/sandbox-source';build.mkdir(exist_ok=True)
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config=json.loads((root/'config/sandbox-source-build.json').read_text())
for relative,commit in config['source_repositories'].items():
    if subprocess.check_output(['git','-C',str(root/relative),'rev-parse','HEAD'],text=True).strip()!=commit:
        raise ValueError('Changed sandbox source/header revision: '+relative)
baseline=root/config['baseline']
if digest(baseline)!=config['baseline_sha256']:raise ValueError('Changed baseline sandbox')
sdk=root/'vendor/darling/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
resource=Path(subprocess.check_output(['clang-19','-print-resource-dir'],text=True).strip())
section=re.search(r'set\(sandbox_sources\s+([^)]*)\)',(source/'CMakeLists.txt').read_text())[1]
sources=[source/p for p in section.split()]
if len(sources)!=3 or any(not p.is_file() for p in sources):raise ValueError('Incomplete sandbox source list')
objects=[]
for path in sources:
    obj=build/(path.stem+'.o');objects.append(obj)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-nostdinc',
        '-I',str(source),'-isystem',str(sdk/'usr/include'),'-isystem',str(resource/'include'),
        '-DDARLING','-DDARWIN','-DPLATFORM_MacOSX','-DTARGET_OS_MAC=1','-D_DARWIN_C_SOURCE',
        '-D__DARWIN_UNIX03','-fPIC','-O2','-Wno-deprecated-declarations','-c',str(path),'-o',str(obj)],check=True)
guest=root/'runtime/rootfs/usr/libexec/darling';output=build/'libsystem_sandbox.dylib'
pending=output.with_name(output.name+'.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11',
    '-syslibroot',str(guest),'-L',str(guest/'usr/lib/system'),
    '-install_name','/usr/lib/system/libsystem_sandbox.dylib','-compatibility_version','1.0.0',
    '-ldyld','-lsystem_c','-lsystem_kernel','-lsystem_malloc',*[str(p) for p in objects],'-o',str(pending)],check=True)
def exports(path):
    listing=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True)
    return set(re.findall(r'^0x[\da-fA-F]+\s+(\S+)',listing,re.M))
missing=exports(baseline)-exports(pending)
if missing:raise ValueError('Missing sandbox exports: '+repr(sorted(missing)))
pending.replace(output)
base=root/'runtime/quarantine-source/darling-root';variant=build/'darling-root'
for path,relative in [('runtime/quarantine-source/libquarantine.dylib','usr/lib/system/libquarantine.dylib'),
                       ('runtime/libsystem-kernel-source/libsystem_kernel.dylib','usr/lib/system/libsystem_kernel.dylib')]:
    if digest(base/relative)!=digest(root/path):raise ValueError('Stale prerequisite source runtime: '+path)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    pending_root=build/'darling-root.pending';previous=build/'darling-root.previous'
    for owned in (pending_root,previous):
        if owned.exists():shutil.rmtree(owned)
    subprocess.run(['cp','-a','--reflink=auto',str(base),str(pending_root)],check=True)
    shutil.copy2(output,pending_root/'usr/lib/system/libsystem_sandbox.dylib')
    if variant.exists():variant.replace(previous)
    pending_root.replace(variant)
    if previous.exists():shutil.rmtree(previous)
report=dict(installed=False,full_darling_rebuild=False,full_sandbox_library_source_build=True,
    source_configuration=config,source_files={str(p.relative_to(root)):digest(p) for p in [*sources,source/'extension.h',source/'sandbox.h',source/'CMakeLists.txt']},
    library_sha256=digest(output),original_export_names_preserved=len(exports(baseline)),source_exports=len(exports(output)),
    runtime_execution_verified=False,variant_root=str(variant.relative_to(root)),
    sandbox_mac_policy_implemented=False,real_extension_grants_implemented=False,
    data_abi_corrections=['Four APP_SANDBOX objects are const char pointers, not character arrays.',
                          'DEFAULT/CANONICAL/NO_REPORT/PREFIXMATCH are uint32_t, not neighboring uint32 values joined into uint64.'],
    scope='Native issue/consume/release user-space MAC syscall ABI and actual missing-policy errors. Legacy sandbox_init stubs remain; check queries use the native MAC operation 2 ABI. No sandbox policy enforcement or real positive token issuance claim.')
(root/'artifacts/sandbox-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built complete source libsystem_sandbox:',output)
