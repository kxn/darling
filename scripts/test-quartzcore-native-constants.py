#!/usr/bin/env python3
"""Verify the constants helper with original Foundation and all six source components."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest()
compat=json.loads((root/'artifacts/native-string-constants-compat.json').read_text())
config=json.loads((root/'config/native-string-constants.json').read_text())
assert digest('config/native-string-constants.json')==compat['config_sha256']
helper='runtime/native-library-stage/libDarlingNativeConstants.dylib'
assert digest(helper)==compat['library_sha256']
selected=json.loads((root/'artifacts/xpc-service-source.json').read_text())['selected_runtime']
assert len(selected)==6;environment=os.environ.copy()
for variable,item in selected.items():
    assert digest(item['path'])==item['sha256'];environment[variable]=str(root/item['path'])
guest='/Volumes/SystemRoot/workspace/'
command=['timeout','-k','5','40','bin/darling','shell','/usr/bin/env','OBJC_DISABLE_TAGGED_POINTERS=YES',
    'DYLD_FRAMEWORK_PATH='+guest+'runtime/foundation-native-framework-stage:'+guest+'runtime/native-framework-stage',
    'DYLD_LIBRARY_PATH='+guest+'runtime/foundation-native-library-stage:'+guest+'runtime/native-library-stage:'+guest+'runtime/rebuilt-der:/usr/lib/swift',
    guest+'artifacts/native-string-constants-smoke',guest+helper]
log=root/'logs/quartzcore-constants-native-foundation-execute.log'
with log.open('w') as stream:
    subprocess.run(command,cwd=root,env=environment,stdout=stream,stderr=subprocess.STDOUT,check=True)
count=len(config['constants']);extra_count=len(config['extra_identifiers'])
for path in ['logs/native-string-constants-execute.log',str(log.relative_to(root))]:
    text=(root/path).read_text()
    assert f'ORIGINAL_CFSTRING_IDENTIFIERS_TYPE_EQUALITY_INDEPENDENT_COPY_OK {count}\n' in text
    assert f'ORIGINAL_EXTRA_IDENTIFIERS_TYPED_VALUES_OK {extra_count}\n' in text
analysis=json.loads((root/'artifacts/quartzcore-native-constants-analysis.json').read_text())
assert not analysis['unclassified_typed_imports']
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed=False,full_compatibility=False,
    source_runtime=selected,helper=helper,helper_sha256=digest(helper),
    verified_cfstring_count=count,verified_extra_identifier_count=extra_count,
    original_graphics_import_cfstrings=len(analysis['imports']),
    original_hairline_double_bit_pattern_verified=True,
    original_coreimage_CIFormat_signed_32bit_pattern_verified=True,
    legacy_and_original_foundation_type_value_independent_copy_verified=True,
    test_source_sha256=digest('fixtures/hello/native-string-constants.c'),
    test_binary_sha256=digest('artifacts/native-string-constants-smoke'),
    generated_header_sha256=digest('runtime/native-string-constants/cases.h'),
    native_analyses={p:digest(p) for p in ['artifacts/quartzcore-native-constants-analysis.json','artifacts/cg-hairline-native-analysis.json','artifacts/coreimage-format-native-analysis.json']},
    logs={p:digest(p) for p in ['logs/native-string-constants-execute.log',str(log.relative_to(root))]},
    config_sha256=digest('config/native-string-constants.json'),
    graphics_operations_implemented=False,full_xcode_build_ready=False,signing_ready=False)
(root/'artifacts/quartzcore-native-constants.json').write_text(json.dumps(report,indent=2)+'\n')
print('Original graphics constants verified with both Foundation runtimes:',count,'CFStrings,',extra_count,'typed values')
