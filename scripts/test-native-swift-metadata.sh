#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
sdk=runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk
clang-19 -target x86_64-apple-macos11 -isysroot "$sdk" \
    -c fixtures/hello/native-swift-metadata.c -o artifacts/native-swift-metadata.o
ld64.lld-19 -arch x86_64 -platform_version macos 11 11 \
    -syslibroot runtime/rootfs/usr/libexec/darling -L runtime/rootfs/usr/libexec/darling/usr/lib \
    -lSystem artifacts/native-swift-metadata.o -o artifacts/native-swift-metadata
python3 - <<'PY'
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess
workspace='/Volumes/SystemRoot/workspace'
cases={
 'swift-metal':('runtime/native-library-stage/libswiftMetal.dylib',[
  ('$s5Metal15MTLLogContainerV','Metal.MTLLogContainer'),
  ('$s5Metal15MTLLogContainerV8IteratorV','Metal.MTLLogContainer.Iterator')]),
 'ml-model-asset':('runtime/native-framework-stage/MLModelAsset.framework/MLModelAsset',[
  ('$s12MLModelAsset05ModelB0V','MLModelAsset.ModelAsset'),
  ('$s12MLModelAsset8MetadataV','MLModelAsset.Metadata')]),
 'odie':('runtime/native-framework-stage/ODIE.framework/ODIE',[
  ('$s4ODIE11OperandTypeO','ODIE.OperandType'),
  ('$s4ODIE13EmptyProfilerV','ODIE.EmptyProfiler')])}
reports={};failed=False
for target,(path,types) in cases.items():
 original=json.loads(Path('runtime/rebuilt-'+target+'/reconstruction.json').read_text())
 actual=hashlib.sha256(Path(path).read_bytes()).hexdigest()
 if actual!=original['staged_image_sha256']:raise ValueError('Stage differs from reconstruction: '+target)
 command=['timeout','-k','5','30','bin/darling','shell','/usr/bin/env',
  'DYLD_FRAMEWORK_PATH='+workspace+'/runtime/native-framework-stage',
  'DYLD_LIBRARY_PATH='+workspace+'/runtime/native-library-stage:'+workspace+'/runtime/rebuilt-der:/usr/lib/swift',
  workspace+'/artifacts/native-swift-metadata',workspace+'/'+path,
  *[part for pair in types for part in pair]]
 log=Path('logs/'+target+'-metadata-execute.log')
 with log.open('w') as output:result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
 verified=result.returncode==0 and 'ORIGINAL_SWIFT_COMPLETE_METADATA_DESCRIPTOR_NAME_IDENTITY_OK' in log.read_text()
 reports[target]={'original_image_sha256':original['original_image_sha256'],
  'staged_image_sha256':actual,'selected_metadata_api_execution_verified':verified,
  'types':[pair[1] for pair in types],'exit_status':result.returncode,'log':str(log)}
 failed|=not verified
 print(target,'PASS' if verified else 'FAIL',result.returncode,flush=True)
report={'checked_at':datetime.now(timezone.utc).isoformat(),'installed':False,
 'images':reports,'full_compatibility':False,
 'scope':'Original nongeneric complete metadata accessors, exact descriptors, qualified type names and repeat identity. No model execution, GPU operations or general Swift ABI compatibility claim.'}
Path('artifacts/native-swift-metadata-compat.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(1 if failed else 0)
PY
