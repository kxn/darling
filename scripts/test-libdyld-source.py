#!/usr/bin/env python3
"""Verify the actual source libdyld API against real loader objects and lifetimes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess
root=Path(__file__).resolve().parent.parent;build=root/'runtime/libdyld-source/fixtures';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling'
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
guestpath=lambda p:'/Volumes/SystemRoot/workspace/'+str(p.relative_to(root))
sources={'empty':'static int unused;\n','dependency':
    '#include <mach-o/loader.h>\n#include <dlfcn.h>\nextern const struct mach_header* _dyld_get_dlopen_image_header(void*);\n'
    'int fixture_value(void){return 7;}\n'
    '__attribute__((noinline)) const struct mach_header* fixture_self_header(void){const struct mach_header* p=_dyld_get_dlopen_image_header(RTLD_SELF);__asm__ volatile("":::"memory");return p;}\n'}
for name,text in sources.items():
    src=build/(name+'.c');src.write_text(text)
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(src),'-o',str(build/(name+'.o'))],check=True)
(build/'empty.exp').write_text('')
common=['ld64.lld-19','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),
    '-L',str(root/'runtime/libdyld-source'),'-ldyld','-lSystem']
subprocess.run([*common,'-dylib','-install_name',guestpath(build/'empty.dylib'),'-exported_symbols_list',str(build/'empty.exp'),str(build/'empty.o'),'-o',str(build/'empty.dylib')],check=True)
subprocess.run([*common,'-dylib','-install_name',guestpath(build/'dependency.dylib'),str(build/'dependency.o'),'-o',str(build/'dependency.dylib')],check=True)
subprocess.run([*common,'-dylib','-install_name',guestpath(build/'reexport.dylib'),'-reexport_library',str(build/'dependency.dylib'),'-o',str(build/'reexport.dylib')],check=True)
subprocess.run([*common,'-bundle',str(build/'empty.o'),'-o',str(build/'empty.bundle')],check=True)
subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-Wno-deprecated-declarations',
    '-c',str(root/'fixtures/hello/dyld-dlopen-header.c'),'-o',str(build/'test.o')],check=True)
binary=root/'artifacts/dyld-dlopen-header';subprocess.run([*common,str(build/'test.o'),'-o',str(binary)],check=True)
environment=os.environ.copy();selected=json.loads((root/'artifacts/xpc-service-source.json').read_text())['selected_runtime']
for variable,item in selected.items():
    assert digest(item['path'])==item['sha256'];environment[variable]=str(root/item['path'])
relative='runtime/libdyld-source/libdyld.dylib';environment['LINUXCODE_LIBDYLD']=str(root/relative)
selected={**selected,'LINUXCODE_LIBDYLD':dict(path=relative,sha256=digest(relative))}
command=['timeout','-k','5','90','bin/darling','shell',guestpath(binary),guestpath(build/'empty.dylib'),guestpath(build/'reexport.dylib'),guestpath(build/'empty.bundle')]
log=root/'logs/dyld-dlopen-header-source.log'
with log.open('w') as stream:result=subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT)
markers=['DYLD_DLOPEN_HEADER_API_OWNED_BY_ACTUAL_LIBDYLD_OK',
    'DYLD_DLOPEN_HEADER_REAL_NO_EXPORTS_FIRST_MULTIPLE_REFERENCES_UNLOAD_INVALID_HANDLES_AND_DLERROR_OK',
    'DYLD_DLOPEN_HEADER_REAL_REEXPORT_OWNER_AND_DYLIB_RTLD_SELF_CALLER_OK',
    'DYLD_DLOPEN_HEADER_REAL_DUPLICATE_MODULE_NAMES_AND_UNLINK_INVALIDATION_OK',
    'DYLD_DLOPEN_HEADER_REAL_EIGHT_THREADS_512_DLOPEN_QUERY_DLCLOSE_CYCLES_OK']
success=result.returncode==0 and all(marker+'\n' in log.read_text() for marker in markers)
abi_rejected=False
if success:
    bad=root/'runtime/libdyld-source/bad-loader';bad.mkdir(exist_ok=True)
    badroot=bad/'darling-root'
    if badroot.exists():shutil.rmtree(badroot)
    subprocess.run(['cp','-a','--reflink=auto',str(root/'runtime/libdyld-source/darling-root'),str(badroot)],check=True)
    shutil.copyfile(root/relative,bad/'libdyld.dylib')
    loader=badroot/'usr/lib/dyld';data=bytearray(loader.read_bytes());data[0]^=1
    pending=loader.with_name('dyld.bad.pending');pending.write_bytes(data);pending.replace(loader)
    bad_environment=environment.copy();bad_environment['LINUXCODE_LIBDYLD']=str(bad/'libdyld.dylib')
    bad_log=root/'logs/dyld-source-bad-loader-abi.log'
    with bad_log.open('w') as stream:
        rejected=subprocess.run(['timeout','-k','5','20','bin/darling','shell','/bin/echo','BAD_LOADER_MUST_NOT_RUN'],cwd=root,env=bad_environment,stdout=stream,stderr=subprocess.STDOUT)
    abi_rejected=rejected.returncode!=0 and 'requires the pinned Darling dyld2 loader ABI' in bad_log.read_text() and 'BAD_LOADER_MUST_NOT_RUN' not in bad_log.read_text()
    assert abi_rejected
    shutil.rmtree(bad)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_libdyld_source_build=True,
    runtime_execution_verified=success and abi_rejected,exit_status=result.returncode,selected_runtime=selected,
    command=command,test_source_sha256=digest('fixtures/hello/dyld-dlopen-header.c'),test_binary_sha256=digest(binary),
    log=str(log.relative_to(root)),log_sha256=digest(log),diagnostic=log.read_text(),
    all_real_lifecycle_markers_verified=success,wrong_loader_abi_rejected_before_execution=abi_rejected,
    test_driver_sha256=digest('scripts/test-libdyld-source.py'),
    tested_fixture_files={str(p.relative_to(root)):digest(p) for p in build.iterdir() if p.is_file()},
    full_loader_source_rebuild=False,full_compatibility=False,full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/dyld-dlopen-header-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('Actual source libdyld handle/header tests:',result.returncode)
raise SystemExit(0 if success and abi_rejected else result.returncode or 1)
