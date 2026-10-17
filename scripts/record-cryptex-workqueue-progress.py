#!/usr/bin/env python3
"""Record real native crypto/loading and the source workqueue repair, not CI success."""

# Preserve the newer native cryptography and FileCoordination checkpoint.
from pathlib import Path as _nc_Path
import json as _nc_json
_nc_state = _nc_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _nc_state.exists() and _nc_json.loads(_nc_state.read_text()).get('primary_report') == 'artifacts/native-crypto-progress.json':
    print('Preserving the newer native cryptography checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer archive/crypto checkpoint.
from pathlib import Path as _ac_Path
import json as _ac_json
_ac_state = _ac_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _ac_state.exists() and _ac_json.loads(_ac_state.read_text()).get('primary_report') == 'artifacts/archive-crypto-progress.json':
    print('Preserving the newer archive/crypto checkpoint'); raise SystemExit(0)

# Historical recorders must preserve the newer dispatch/XPC checkpoint.
from pathlib import Path as _dx_Path
import json as _dx_json
_dx_state = _dx_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _dx_state.exists() and _dx_json.loads(_dx_state.read_text()).get('primary_report') == 'artifacts/dispatch-xpc-progress.json':
    print('Preserving the newer dispatch/XPC checkpoint'); raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
evidence={}
def add(n,sha=None):
    actual=digest(n)
    if sha is not None:assert actual==sha,n
    evidence[n]=actual
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pathkey in ['path','source']:
                    if pathkey=='source' and 'first_line' in value:continue  # This digest describes a literal slice, not the whole assembly file.
                    if isinstance(value.get(pathkey),str) and (root/value[pathkey]).is_file():add(value[pathkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(list,dict)):walk(item)
def report(n):
    d=read(n);add(n);walk(d);return d
p=runpy.run_path(str(root/'scripts/workqueue-stack-runtime-profile.py'))['profile']()
runtime=p['source_runtime']
for item in runtime.values():add(item['path'],item['sha256'])
kernel=report('artifacts/workqueue-stack-kernel-source-build.json')
assert kernel['full_libsystem_kernel_source_build'] and kernel['complete_source_files']==877
assert kernel['baseline_exports_preserved']==1362 and kernel['source_exports']==1364
report('artifacts/workqueue-stack-runtime-stage.json')
for n in ['vendor/darling/src/startup/mldr/elfcalls/dthreads.h','vendor/darling/src/startup/mldr/elfcalls/threads.c','vendor/darling/src/external/libpthread/src/pthread_asm.S','vendor/darling/src/external/libpthread/src/pthread.c','vendor/darling/src/external/xnu/libsyscall/CMakeLists.txt','vendor/darling/src/external/xnu/darling/src/libsystem_kernel/emulation/CMakeLists.txt']:add(n)
historical=read('runtime/source-input-history/manifest.json')
for original,entry in historical.items():add(entry['snapshot'],entry['sha256'])
add('runtime/source-input-history/manifest.json')
baseline=report('artifacts/workqueue-stack-baseline.json');fixed=report('artifacts/workqueue-stack-fixed.json')
assert baseline['exit_status']==42 and fixed['exit_status']==0 and fixed['source_runtime']==runtime
assert 'rounds=50 bytes=16464' in (root/baseline['log']).read_text()
assert 'WORKQUEUE_REAL_2048_SAME_THREAD_REUSES_STACK_SPAN=0' in (root/fixed['log']).read_text()
assert 'WORKQUEUE_REAL_IDLE_TIMEOUT_PTHREAD_DESTRUCTOR_OK' in (root/fixed['log']).read_text()
regression=report('artifacts/workqueue-stack-regression.json')
assert regression['source_runtime']==runtime and len(regression['checks'])==6
assert all(row['exit_status']==0 for row in regression['checks'])

stage=report('artifacts/cryptex-native-stage.json');assert len(stage['images'])==7
for name,target in stage['symlinks'].items():assert os.readlink(root/name)==target
for image in stage['images']:
    d=report(image['reconstruction'])
    assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports']
crypto=next(i for i in stage['images'] if i['target']=='crypto42-device-native');assert crypto['exports']==3447
literals=report('artifacts/crypto42-source-literal-test.json')
assert (literals['literal_regions'],literals['literal_bytes'],literals['native_data_readers'],literals['valid_native_data_symbols'])==(10,17696,48,4)
assert len(literals['rejections'])==9 and literals['all_emitted_literal_bytes_unchanged']
vectors=report('artifacts/crypto42-native-test.json')
assert vectors['cases']==196 and vectors['native_algorithms_verified'] and vectors['exit_status']==0
assert vectors['actual_CPU_test_features']=={'ssse3':True,'pclmulqdq':True}
assert 'checks=369361' in (root/vectors['log']).read_text()
assert not vectors['whole_3447_export_API_verified'] and not vectors['certificate_trust_verified']
report('artifacts/libressl-assembly-source-reference.json');report('artifacts/crypto42-source-literal-analysis.json')
for n in ['runtime/crypto42-assembly-literals/candidate-ranges.json','config/cache-image-pins.json','runtime/rebuilt-crypto42-device-native/unclassified-code-imports.json','runtime/rebuilt-crypto42-device-native/unsupported-code.json']:add(n)
assert read('runtime/rebuilt-crypto42-device-native/unclassified-code-imports.json')==[]
assert read('runtime/rebuilt-crypto42-device-native/unsupported-code.json')==[]
loads=report('artifacts/workqueue-cryptex-native-load.json')
assert loads['source_runtime']==runtime and loads['stage_sha256']==digest('artifacts/cryptex-native-stage.json')
assert len(loads['checks'])==7 and loads['all_selected_images_load']
assert not loads['trust_protocol_verified'] and not loads['cryptex_mounting_verified']
assets=report('artifacts/mobileasset-download-attributes-build.json')
assert assets['full_framework_source_build'] and assets['complete_source_files']==15
assert assets['original_exports_preserved']==82 and assets['source_exports']==84
asset_test=report('artifacts/mobileasset-download-attributes-test.json')
assert asset_test['actual_Pallas_client_transport_regression_verified']
assert not asset_test['actual_Apple_download_daemon_verified'] and not asset_test['asset_download_implemented']
assert len(asset_test['checks'])==2 and all(row['exit_status']==0 for row in asset_test['checks'])
report('artifacts/mobileasset-download-attributes-reference.json')

probes={}
for mode in ['version','showsdks','build']:
    names=list((root/'artifacts').glob('xcode-service-runtime-workqueue-*-'+mode+'.json'))
    if mode=='build':names=[n for n in names if '-extended-' in n.name]
    assert len(names)==1,(mode,names)
    name=str(names[0].relative_to(root));d=report(name);probes[mode]=name
    assert d['source_runtime']==runtime and d['UTI_preflight_verified'] and not d['diagnostic_without_UTI_preflight']
    assert d['xcode_process_started'] and d['xcode_process_returned']
    assert d['original_xcodebuild_sha256']=='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
    assert d['exit_status']==(70 if mode=='build' else 0)
    if mode=='build':
        text=(root/d['log']).read_text();assert 'Symbol not found: _DMNSError' in text and 'SERVICE_RUNTIME_XCODE_STATUS 70' in text
        assert '"LastExitStatus" = 139' in text
    for job in d['jobs']:add(job['path'],job['sha256'])
    for n,sha in d.get('service_logs',{}).items():add(n,sha)
crash=report('artifacts/lsd-workloop-crash-analysis.json');assert not crash['fixed']
for stem in ['cryptex-native-xcode-segv','workqueue-fixed-lsd-segv']:
    report('artifacts/'+stem+'-images.json')
    for suffix in ['gdb.log','maps.log','resolved.log']:add('logs/'+stem+'.'+suffix)
for stem in ['workqueue-fixed-xcode-initial','workqueue-fixed-xcode-late']:
    for suffix in ['gdb.log','maps.log','annotated.log']:add('logs/'+stem+'.'+suffix)

archives={}
manifests=['artifacts/device-identity-history/manifest.json','artifacts/cryptex-native-initial-history/manifest.json','artifacts/workqueue-stack-baseline-history/manifest.json','artifacts/cryptex-workqueue-recorder-history/manifest.json']
manifests += [str(n.relative_to(root)) for n in (root/'artifacts/xcode-service-probe-history').glob('*/manifest.json')]
for n in manifests:
    d=read(n)
    for original,item in d.items():
        stored=item.get('archived')
        if stored is None:stored=str((Path(n).parent/item['archive']))
        assert digest(stored)==item['sha256'],(n,original)
    add(n);archives[n]=dict(sha256=digest(n),verified_files=len(d))
for n in ['artifacts/xnu-workqueue-stack-source.patch','artifacts/darling-mobileasset-download-attributes-source.patch']:add(n)
subprocess.run(['git','-C',str(root/'vendor/darling/src/external/xnu'),'apply','--reverse','--check',str(root/'artifacts/xnu-workqueue-stack-source.patch')],check=True)
subprocess.run(['git','-C',str(root/'vendor/darling'),'apply','--reverse','--check',str(root/'artifacts/darling-mobileasset-download-attributes-source.patch')],check=True)
scripts=['scripts/'+n for n in ['verify-historical-source.py','quarantine-vfs-runtime-profile.py','pid-generation-source-profile.py','metadata-kernel-profile.py','source-assembly-literals.py','prepare-crypto42-source-literals.py','test-source-assembly-literals.py','rebuild-c-cache-image.py','build-libsystem-kernel-source.py','stage-cryptex-native.py','cryptex-native-profile.py','probe-cryptex-native.py','test-crypto42-native.py','build-mobileasset-download-attributes.py','test-mobileasset-download-attributes.py','workqueue-stack-runtime-profile.py','stage-workqueue-stack-runtime.py','test-workqueue-stack-reuse.py','test-workqueue-stack-regression.py','probe-xcode-service-runtime.py','capture-darling-stacks.py','annotate-macho-stack.py','record-cryptex-workqueue-progress.py']]
scripts+=read('artifacts/cryptex-workqueue-recorder-guards.json')
for n in scripts:add(n)
for n in ['fixtures/hello/workqueue-stack-reuse.c','fixtures/hello/crypto42-native.c','bin/darling','bin/xcodebuild','scripts/runtime-ns.sh','artifacts/cryptex-workqueue-recorder-guards.json']:add(n)
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'
sha='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5';add(original,sha)
add('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild',sha)
next_work=[
    'Reproduce and repair the lsd libdispatch workloop fallback execution context in source; build complete libdispatch and verify ordering, Mach replies, nested target queues and service lifetime.',
    'Resolve the actual DVTDownloads DiskManagement import _DMNSError and its complete required provider interfaces; do not fabricate disk-operation or service success.',
    'Continue the unchanged original project build through actual compilation, archive, signing and export, including Unity/CocoaPods integration; only promote the default CI entry after end-to-end execution.',
    'Keep actual Security attestation, trust evaluation, Cryptex mounts, asset downloads, Seatbelt profiles and earlier C++ chained replacement limitations explicit until verified.'
]
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,source_runtime=runtime,native_cryptex_stage='artifacts/cryptex-native-stage.json',native_image_count=7,native_crypto_exports=3447,source_literal_regions=10,source_literal_bytes=17696,negative_literal_controls=9,native_crypto_vector_cases=196,native_crypto_checks=369361,workqueue_same_thread_reuses=2048,workqueue_stack_span_bytes=0,real_idle_termination_verified=True,original_xcode_probes=probes,current_original_project_exit_status=70,current_loader_symbol='_DMNSError',current_loader_provider='DiskManagement.framework',lsd_exit_139_still_unfixed=True,lsd_crash_analysis='artifacts/lsd-workloop-crash-analysis.json',source_implementation='Complete 877-file Darling libsystem_kernel source rebuild with x86_64 stack reset on workqueue reuse; complete 15-file MobileAsset source framework. Original Apple Cryptex/LibreSSL machine code and Foundation reexport bridge retained, without call overrides or import redirects.',archives=archives,evidence=evidence,scripts={n:digest(n) for n in scripts},next_work=next_work)
destination='artifacts/cryptex-workqueue-progress.json';(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_original_xcode_blocker='DVTDownloads missing DiskManagement _DMNSError; lsd separately exits 139 in libdispatch workloop QoS access',latest_xcode_loader_blocker='_DMNSError',latest_staged_coreml_and_metal_blocker='Required Xcode plugin dependency closure',latest_xcode_failure_kind='DiskManagement_import_and_lsd_workloop_runtime',latest_xcode_runtime_failure='Original project returns 70 after strict UTI; separate live lsd SIGSEGV captured at anonymous workloop sentinel. Original Xcode stack overflow fixed by real source workqueue repair.',latest_implementation_form=record['source_implementation'],active_build=dict(task='Cryptex-native-crypto-and-source-workqueue-stack-repair',running=False,report=destination),next_work=next_work)
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded',len(evidence),'current file hashes and',len(scripts),'scripts; original build remains incomplete, goal active')
