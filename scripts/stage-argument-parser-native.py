#!/usr/bin/env python3
"""Privately stage the pinned complete original XCBuild parser dependency."""
from pathlib import Path
import fcntl,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
target='argument-parser-internal-native';pin=json.loads((root/'config/cache-image-pins.json').read_text())[target]
original='runtime/fullsystem-libraries'+pin['path'];source='runtime/rebuilt-'+target+'/ArgumentParserInternal';report='runtime/rebuilt-'+target+'/reconstruction.json';d=json.loads((root/report).read_text())
assert digest(original)==pin['sha256']==d['original_image_sha256'];assert digest(source)==d['staged_image_sha256']
assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports']
base=root/'runtime/argument-parser-native';output=base/'frameworks/ArgumentParserInternal.framework/Versions/A/ArgumentParserInternal'
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(root/source,output.with_suffix('.pending'));output.with_suffix('.pending').replace(output)
    framework=output.parents[2]
    for path,destination in [(framework/'Versions/Current','A'),(framework/'ArgumentParserInternal','Versions/Current/ArgumentParserInternal')]:
        if not path.is_symlink():path.symlink_to(destination)
record=dict(target=target,original=original,original_sha256=digest(original),source=source,source_sha256=digest(source),reconstruction=report,reconstruction_sha256=digest(report),framework=str(output.relative_to(root)),framework_sha256=digest(output),exports=d['exports'],installed=False,backend_overrides=False,runtime_execution_verified=False,full_xcode_build_ready=False)
(root/'artifacts/argument-parser-native-stage.json').write_text(json.dumps(record,indent=2)+'\n')
print('Staged original parser:',d['exports'],'exports')
