#!/usr/bin/env python3
"""Link Apple's unchanged typed-malloc fallback to the leaf allocator only."""
from pathlib import Path
import fcntl,hashlib,json,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
source='vendor/darling/src/external/libmalloc/src/malloc_type_stubs.c'
assert (root/source).read_bytes()==(root/'vendor/apple-libmalloc/src/malloc_type_stubs.c').read_bytes()
build=root/'runtime/corecrypto-malloc-source';build.mkdir(exist_ok=True)
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
guest=root/'runtime/rootfs/usr/libexec/darling';obj=build/'malloc.o';library=build/'libraries/libDarlingCoreCryptoMalloc.dylib';library.parent.mkdir(exist_ok=True)
compile=['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-O2','-c',str(root/source),'-o',str(obj)];subprocess.run(compile,check=True)
link=['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(guest),'-L'+str(guest/'usr/lib/system'),'-lsystem_malloc','-ldyld','-install_name','/usr/lib/libDarlingCoreCryptoMalloc.dylib',str(obj),'-o',str(library.with_suffix('.pending'))]
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);subprocess.run(link,check=True);library.with_suffix('.pending').replace(library)
record=dict(source=source,source_sha256=digest(source),library=str(library.relative_to(root)),library_sha256=digest(library),object=str(obj.relative_to(root)),object_sha256=digest(obj),compile_command=compile,link_command=link,upstream_source_unchanged=True,system_framework_dependencies=False,typed_zone_isolation=False,runtime_execution_verified=False)
(root/'artifacts/corecrypto-malloc-source-build.json').write_text(json.dumps(record,indent=2)+'\n');print('Built leaf-only original malloc fallback')
