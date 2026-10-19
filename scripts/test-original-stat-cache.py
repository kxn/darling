#!/usr/bin/env python3
"""Run original stat-cache generation/reuse/invalidation and its original Clang reader."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,runpy,subprocess
parser=argparse.ArgumentParser();parser.add_argument('--vchroot-links',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
suffix='-vchroot-links' if args.vchroot_links else ''
m=runpy.run_path(str(root/('scripts/vchroot-links-runtime-profile.py' if args.vchroot_links else 'scripts/global-fsevents-runtime-profile.py')));p=m['profile']()
build=root/'runtime/global-fsevents-tests';build.mkdir(exist_ok=True)
script=build/('stat-cache'+suffix+'.sh')
script.write_text('''#!/bin/bash
set -euo pipefail
work=$(mktemp -d /tmp/original-stat-cache.XXXXXX)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/parent/SDK"
sdk="$work/parent/SDK"
printf '#define FIRST 11\\n' > "$sdk/First.h"
tool=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache
clang=/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/first.log" 2>&1
cat "$work/first.log"
echo ORIGINAL_CACHE_FIRST_GENERATION_OK
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/reuse.log" 2>&1
cat "$work/reuse.log"
grep -q 'Cache up-to-date' "$work/reuse.log"
echo ORIGINAL_CACHE_REAL_UNCHANGED_REUSE_OK
printf '#define ADDED 37\\n' > "$sdk/Added.h"
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/changed.log" 2>&1
cat "$work/changed.log"
if grep -q 'Cache up-to-date' "$work/changed.log"; then exit 3; fi
printf '#include "Added.h"\\n_Static_assert(ADDED == 37, "real header");\\nint value = ADDED;\\n' > "$work/test.c"
"$clang" -fsyntax-only -x c -I "$sdk" -ivfsstatcache "$work/stat.cache" "$work/test.c"
echo ORIGINAL_CACHE_MUTATION_INVALIDATED_AND_ORIGINAL_CLANG_READ_ADDED_HEADER_OK
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/reuse-after-change.log" 2>&1
cat "$work/reuse-after-change.log"
grep -q 'Cache up-to-date' "$work/reuse-after-change.log"
printf '#define ADDED 58\\n' > "$sdk/Added.h"
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/in-place.log" 2>&1
cat "$work/in-place.log"
if grep -q 'Cache up-to-date' "$work/in-place.log"; then exit 5; fi
printf '#include "Added.h"\\n_Static_assert(ADDED == 58, "modified in place");\\n' > "$work/in-place.c"
"$clang" -fsyntax-only -x c -I "$sdk" -ivfsstatcache "$work/stat.cache" "$work/in-place.c"
echo ORIGINAL_CACHE_IN_PLACE_HEADER_WRITE_INVALIDATES_OK
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/reuse-in-place.log" 2>&1
cat "$work/reuse-in-place.log"
grep -q 'Cache up-to-date' "$work/reuse-in-place.log"
mv "$work/parent" "$work/previous-parent"
mkdir -p "$sdk"
printf '#define REPLACEMENT 91\\n' > "$sdk/Replacement.h"
"$tool" -v "$sdk" -o "$work/stat.cache" > "$work/replaced.log" 2>&1
cat "$work/replaced.log"
if grep -q 'Cache up-to-date' "$work/replaced.log"; then exit 4; fi
printf '#include "Replacement.h"\\n_Static_assert(REPLACEMENT == 91, "replacement tree");\\n' > "$work/replacement.c"
"$clang" -fsyntax-only -x c -I "$sdk" -ivfsstatcache "$work/stat.cache" "$work/replacement.c"
echo ORIGINAL_CACHE_ANCESTOR_REPLACEMENT_INVALIDATES_OLD_TREE_OK
echo ORIGINAL_STAT_CACHE_FULL_REUSE_MUTATION_CONSUMER_OK
''')
command=p['command'][:-2]+['/bin/bash','/Volumes/SystemRoot/workspace/'+str(script.relative_to(root))];command[3]='180'
log='logs/original-stat-cache-global-fsevents'+suffix+'.log'
with (root/log).open('w') as stream:r=subprocess.run(command,cwd=root,env=m['environment'](p),stdout=stream,stderr=subprocess.STDOUT)
text=(root/log).read_text();print(text[-6000:],end='');digest=lambda name:hashlib.sha256((root/name).read_bytes()).hexdigest()
tool='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang-stat-cache'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),command=command,script=str(script.relative_to(root)),script_sha256=digest(script),original_tool=tool,original_tool_sha256=digest(tool),source_runtime=p['source_runtime'],source_global_fsevents=p['source_global_fsevents'],source_fsevents=p['source_global_fsevents_framework'],log=log,log_sha256=digest(log),exit_status=r.returncode,verified=r.returncode==0 and 'ORIGINAL_STAT_CACHE_FULL_REUSE_MUTATION_CONSUMER_OK' in text,original_Xcode_or_CI_arguments_modified=False,full_xcode_build_ready=False)
(root/('artifacts/original-stat-cache-global-fsevents-test'+suffix+'.json')).write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(0 if record['verified'] else 1)
