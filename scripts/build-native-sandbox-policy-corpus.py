#!/usr/bin/env python3
"""Compile semantic test policies with the unchanged original Apple compiler."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,runpy,subprocess
root=Path(__file__).resolve().parent.parent
m=runpy.run_path(str(root/'scripts/sandbox-compiler-resources-profile.py'));p=m['profile']()
build=root/'runtime/sandbox-policy-corpus';build.mkdir(exist_ok=True)
policies={
'allow-all':'(version 1)(allow default)',
'deny-all':'(version 1)(deny default)',
'subpath-read':'(version 1)(deny default)(allow file-read* (subpath (param "DARLING_TEST_ROOT")))',
'literal-read':'(version 1)(deny default)(allow file-read-data (literal "/tmp/darling-sandbox-policy/file"))',
'regex-read':'(version 1)(deny default)(allow file-read-data (regex #"^/tmp/darling-policy/.*$"))',
'mach-service':'(version 1)(deny default)(allow mach-lookup (global-name "com.apple.DiskArbitration.diskarbitrationd"))',
'write-temp':'(version 1)(allow default)(deny file-write*)(allow file-write* (subpath (param "DARLING_TEST_ROOT")))',
'negated-path':'(version 1)(allow default)(deny file-write-data (require-not (subpath "/tmp/allowed")))',
'disjunction':'(version 1)(deny default)(allow file-read-data (require-any (literal "/tmp/alpha") (literal "/tmp/alphabet") (literal "/tmp/beta")))',
'ranges':'(version 1)(deny default)(allow file-read-data (regex #"^/tmp/item-[a-c][0-9]+$"))',
'alternation':'(version 1)(deny default)(allow file-read-data (regex #"^/tmp/(abc|abd|z)[0-9]*$"))',
'seek':'(version 1)(deny default)(allow file-read-data (regex #"darling-[0-9]+$"))',
'long-literal':'(version 1)(deny default)(allow file-read-data (literal "/tmp/'+('abcdefghij'*29)+'"))',
'long-alternation':'(version 1)(deny default)(allow file-read-data (require-any '+''.join('(literal "/tmp/group/'+str(i)+'-'+('x'*36)+'")' for i in range(20))+'))',
'global-and-debug':'(version 1)(deny default)(allow mach-lookup (require-all (global-name "org.example.debug") (debug-mode)))',
'platform-only':'(version 1)(deny default)(allow mach-lookup (require-all (global-name "org.example.platform") (process-attribute is-platform-binary)))',
'installer-only':'(version 1)(deny default)(allow mach-lookup (require-all (global-name "org.example.installer") (process-attribute is-installer)))',
'initproc-only':'(version 1)(deny default)(allow mach-lookup (require-all (global-name "org.example.initproc") (process-attribute is-initproc)))',
'self-only':'(version 1)(allow default)(deny mach-task-name)(allow mach-task-name (target self))',
'other-only':'(version 1)(allow default)(deny mach-task-name)(allow mach-task-name (target others))',
'signal-other-only':'(version 1)(allow default)(deny signal)(allow signal (target others))',
'regular-file-only':'(version 1)(deny default)(allow file-write-create (require-all (subpath "/tmp/files") (vnode-type REGULAR-FILE)))',
'posix-name':'(version 1)(deny default)(allow ipc-posix-shm-write-create (ipc-posix-name-regex #"^/tmp/com.apple.csseed.[0-9]+$"))',
'io-property':'(version 1)(deny default)(deny iokit-get-properties)(allow iokit-get-properties (require-any (iokit-property "Protocol Characteristics") (iokit-property "CaseSensitive")))',
'preference':'(version 1)(deny default)(allow user-preference-read (preference-domain "org.example.preferences"))',
}
inputs='static const struct input inputs[]={\n'+''.join(' {'+json.dumps(n)+','+json.dumps(source)+',0},\n' for n,source in policies.items())+' {"coreservicesd","com.apple.coreservicesd",1}\n};\n'
include=build/'sandbox-policy-corpus.inc';include.write_text(inputs)
source='fixtures/hello/sandbox-policy-corpus.c';obj=build/'test.o';binary=build/'test'
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
subprocess.run(['clang-19','-target','x86_64-apple-macos14','-isysroot',str(sdk),'-I',str(build),'-O0','-c',str(root/source),'-o',str(obj)],check=True)
subprocess.run(['ld64.lld-19','-arch','x86_64','-platform_version','macos','14','14','-syslibroot',str(sdk),'-lSystem',str(obj),'-o',str(binary)],check=True)
command=p['command'][:-2]+['/Volumes/SystemRoot/workspace/'+str(binary.relative_to(root)),'/Volumes/SystemRoot/workspace/'+str(build.relative_to(root))]
r=subprocess.run(command,env=m['environment'](p),capture_output=True,text=True);text=r.stdout+r.stderr
log='logs/native-sandbox-policy-corpus.log';(root/log).write_text(text);digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
assert r.returncode==0 and 'POLICY_CORPUS_RETURNED' in text,text
manifest={}
for name,recipe in {**policies,'coreservicesd':None}.items():
    path=str((build/(name+'.bin')).relative_to(root));manifest[name]=dict(source=recipe,binary=path,sha256=digest(path),size=(root/path).stat().st_size)
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),exit_status=r.returncode,command=command,log=log,log_sha256=digest(log),source=source,source_sha256=digest(source),generated_include=str(include.relative_to(root)),generated_include_sha256=digest(include),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),native_sandbox_compiler=p['native_sandbox_compiler'],original_sandbox_resources=p['original_sandbox_resources'],policies=manifest,policy_applied=False)
(root/'artifacts/native-sandbox-policy-corpus.json').write_text(json.dumps(record,indent=2)+'\n');print('Compiled',len(manifest),'original policies')
