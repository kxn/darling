#!/usr/bin/env python3
"""Stage only original C dependency libraries for independent API tests.

Does not select the full native Foundation or the libFND facade. System's
original coreservices/sandbox/quarantine install names stay on the base backend.
"""
from pathlib import Path
import hashlib
import json
import shutil

project=Path(__file__).resolve().parent.parent
config=json.loads((project/'config/foundation-native-experiment.json').read_text())
entries={e['target']:e for e in config['targets']}
pins=json.loads((project/'config/cache-image-pins.json').read_text())
stage=project/'runtime/native-c-test-stage';stage.mkdir(exist_ok=True)
for target in ['dirhelper-native','containermanager-native','system-collections-native',
               'sandbox-native','quarantine-native']:
    entry=entries[target];name=Path(pins[target]['path']).name
    source=project/('runtime/rebuilt-'+target)/name
    report=json.loads((source.parent/'reconstruction.json').read_text())
    if pins[target]['objc_classes'] or report.get('objc_metadata') or report.get('swift_metadata'):
        raise ValueError('C test stage must not introduce Objective-C/Swift metadata')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=report['staged_image_sha256']:
        raise ValueError('Changed original C reconstruction: '+target)
    destination=stage/entry.get('stage_name',name)
    if destination.name in ['libsystem_coreservices.dylib','libsystem_sandbox.dylib','libquarantine.dylib']:
        raise ValueError('Do not replace base system bootstrap components in this test stage')
    temporary=destination.with_name(destination.name+'.pending')
    shutil.copyfile(source,temporary);shutil.copymode(source,temporary);temporary.replace(destination)
    print(target,destination.name)
