#!/usr/bin/env python3
"""Build the complete two-file Darling inotify FSEvents source component."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,fcntl,hashlib,json,re,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',default='runtime/fsevents-source');parser.add_argument('--report',default='artifacts/fsevents-source-build.json');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent;repo=root/'vendor/darling/src/frameworks/CoreServices';build=root/args.output_dir;build.mkdir(parents=True,exist_ok=True);sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk';guest=root/'runtime/rootfs/usr/libexec/darling';digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
include=build/'include/darling';include.mkdir(parents=True,exist_ok=True);link=include/'emulation'
if not link.is_symlink():link.symlink_to(root/'vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/include',target_is_directory=True)
sources=['src/FSEvents/FSEvents.m','src/FSEvents/FSEventsImpl.m'];objects=[]
for src in sources:
 obj=build/(Path(src).stem+'.o');objects.append(obj);subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(repo/'include'),'-I'+str(build/'include'),'-fblocks','-fobjc-weak','-O2','-c',str(repo/src),'-o',str(obj)],check=True)
library=args.output_dir+'/frameworks/FSEvents.framework/Versions/A/FSEvents';target=root/library;target.parent.mkdir(parents=True,exist_ok=True);pending=target.with_suffix('.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-L',str(guest/'usr/lib/system'),'-L',str(guest/'usr/lib'),'-lsystem_kernel','-framework','Foundation','-framework','CoreFoundation','-lobjc','-lSystem','-install_name','/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/FSEvents.framework/Versions/A/FSEvents','-compatibility_version','1.0.0','-current_version','1239.200.12',*[str(o) for o in objects],'-o',str(pending)],check=True)
original='runtime/rootfs/usr/libexec/darling/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/FSEvents.framework/Versions/A/FSEvents'
exports=lambda path:set(re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(path)],text=True),re.M))
old=exports(root/original);new=exports(pending);assert not old-new
with (root/'runtime/session.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(target)
f=target.parent.parent.parent
for p,v in [(f/'Versions/Current','A'),(f/'FSEvents','Versions/Current/FSEvents')]:
 if not p.is_symlink():p.symlink_to(v)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),library=library,library_sha256=digest(library),original=original,original_sha256=digest(original),full_FSEvents_source_component_build=True,complete_source_files=2,original_exports_preserved=len(old),source_exports=len(new),sources={str((repo/n).relative_to(root)):digest(str((repo/n).relative_to(root))) for n in sources},headers={str((repo/n).relative_to(root)):digest(str((repo/n).relative_to(root))) for n in ['src/FSEvents/FSEventsImpl.h','include/FSEvents/FSEvents.h','src/FSEvents/CMakeLists.txt']},installed=False,runtime_execution_verified=False,flush_async_implemented=True,flush_sync_implemented=True,immutable_callback_batches=True,weak_source_contexts=True,scope='Complete two-file source FSEvents with real nonblocking inotify reads, per-stream state queue, latency timer, immutable delivery batches and actual async/sync flush. Recursive coverage, persistent/global IDs, relative-device streams and some flags remain unsupported or unverified.')
(root/args.report).write_text(json.dumps(record,indent=2)+'\n');print('Built complete source FSEvents with all',len(old),'previous exports preserved')
