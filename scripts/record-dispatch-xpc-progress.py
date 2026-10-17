#!/usr/bin/env python3
"""Record source workloop/send-ownership repairs and the actual remaining build failure."""

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
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
evidence={};historical={};frozen=read('runtime/source-input-history/manifest.json')
def add(n,sha=None):
    actual=digest(n)
    if sha is not None and actual!=sha:
        entry=frozen.get(n);assert entry and entry['sha256']==sha and digest(entry['snapshot'])==sha,n
        historical[n]=entry;evidence[entry['snapshot']]=sha;return
    evidence[n]=actual
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pathkey in ['path','source','file']:
                    if pathkey=='source' and 'first_line' in value:continue
                    if isinstance(value.get(pathkey),str) and (root/value[pathkey]).is_file():add(value[pathkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(list,dict)):walk(item)
def report(n):
    d=read(n);add(n);walk(d);return d
p=runpy.run_path(str(root/'scripts/xpc-sent-message-runtime-profile.py'))['profile']()
runtime=p['source_runtime']
for item in runtime.values():add(item['path'],item['sha256'])
dispatch=report('artifacts/dispatch-workloop-source-build.json')
assert dispatch['full_libdispatch_source_build'] and dispatch['complete_source_files']==32
assert dispatch['original_exports_preserved']==dispatch['source_exports']==654
assert not dispatch['kernel_workloop_backend_enabled']
for entry in dispatch['sources']:assert digest(entry['source'])==entry['sha256']
baseline=report('artifacts/dispatch-workloop-baseline.json');fixed=report('artifacts/dispatch-workloop-fixed.json')
assert baseline['exit_status']!=0 and fixed['exit_status']==0 and fixed['expected_result_verified']
assert 'completed=1024 errors=0' in (root/fixed['log']).read_text()
assert 'WORKLOOP_REAL_NESTED_TARGET_FIFO_SYNC_RESTORE_AND_INDEPENDENT_ROOT_CONTEXT_OK' in (root/fixed['log']).read_text()
add('vendor/darling/src/external/libdispatch/private/workloop_private.h')
assert 'but that is not the case when using dispatch_sync()' in (root/'vendor/darling/src/external/libdispatch/private/workloop_private.h').read_text()

xpc=report('artifacts/xpc-sent-message-source-build.json')
assert xpc['full_libxpc_source_build'] and xpc['complete_source_files']==39
for n,sha in {**xpc['source_files'],**xpc['modified_files']}.items():
    path='vendor/darling/src/external/libxpc/'+n;assert digest(path)==sha,path;add(path,sha)
stage=report('artifacts/xpc-sent-message-runtime-stage.json');assert stage['source_runtime']==runtime
exports=lambda n:set(re.findall(r'^(?:0x[\da-fA-F]+|\[re-export\])\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(root/n)],text=True),re.M))
old=exports(stage['previous_source_runtime']['LINUXCODE_LIBXPC']['path']);new=exports(runtime['LINUXCODE_LIBXPC']['path']);assert old<=new and len(old)==len(new)==640
loopback_baseline=report('artifacts/xpc-loopback-sent-baseline.json');loopback=report('artifacts/xpc-loopback-sent-fixed.json')
assert loopback_baseline['exit_status']!=0 and loopback['exit_status']==0 and loopback['source_runtime']==runtime
assert loopback_baseline['source_sha256']==loopback['source_sha256'] and loopback_baseline['binary_sha256']==loopback['binary_sha256']
assert 'XPC_REAL_16_LOOPBACK_CHECKINS_256_REPLY_PAYLOADS_AND_CANCELLATION_OK' in (root/loopback['log']).read_text()
ownership=report('artifacts/xpc-sent-message-ownership-analysis.json')
assert ownership['observed_receive_right_release_port']==ownership['subsequent_vanished_port']==7683
assert ownership['ordinary_registration_flag_echo_hypothesis_rejected'] and not ownership['universal_lsd_lifetime_proven']
for stem in ['lsd-port-lifetime','dispatch-fixed-lsd-sigill']:
    for suffix in ['gdb.log','maps.log','resolved.log']:add('logs/'+stem+'.'+suffix)
    report('artifacts/'+stem+'-images.json')
for n in ['vendor/darling/src/external/xnu/libsyscall/mach/mach_msg.c','vendor/darling/src/external/libkqueue/src/common/kevent.c','vendor/darling/src/external/libkqueue/src/linux/machport.c','vendor/darlingserver/duct-tape/src/kqchan.c']:add(n)
assert subprocess.check_output(['git','-C',str(root/'vendor/darling/src/external/libkqueue'),'rev-parse','HEAD'],text=True).strip()=='b0795a2e1dab5331116770139bfea8d832478f5f'

disk=report('artifacts/diskmanagement-nserror-source-build.json');native=report('artifacts/diskmanagement-nserror-native-reference.json')
assert disk['full_framework_source_build'] and disk['complete_source_files']==23 and disk['complete_DMNSError_instructions_identical_to_native']
assert native['machine_code']=='554889e531c05dc3' and native['independently_read_from_actual_dyld_cache']
assert not disk['disk_operations_implemented'] and not disk['generic_disk_manager_stubs_implemented']
regression=report('artifacts/xpc-sent-message-regression.json')
assert regression['source_runtime']==runtime and len(regression['checks'])==6 and all(i['exit_status']==0 for i in regression['checks'])
pallas=report('artifacts/xpc-sent-mobileasset-test.json');assert pallas['source_runtime']==runtime and pallas['actual_Pallas_client_transport_regression_verified']
assert not pallas['actual_Apple_download_daemon_verified'] and not pallas['asset_download_implemented']

probes={};symbol='_$s12AppleArchive0B10ByteStreamC010decryptionD011readingFrom17encryptionContext5flags11threadCountACSgAC_AA0b10EncryptionI0CAA0B5FlagsVSitFZ'
for mode in ['version','showsdks','build']:
    names=list((root/'artifacts').glob('xcode-service-runtime-sent-*-'+mode+'.json'));assert len(names)==1,(mode,names)
    name=str(names[0].relative_to(root));d=report(name);probes[mode]=name
    assert d['source_runtime']==runtime and d['UTI_preflight_verified'] and not d['diagnostic_without_UTI_preflight']
    assert d['xcode_process_started'] and d['xcode_process_returned']
    assert d['exit_status']==(70 if mode=='build' else 0)
    for job in d['jobs']:add(job['path'],job['sha256'])
    for n,sha in d['service_logs'].items():add(n,sha)
    if mode=='build':
        text=(root/d['log']).read_text();assert 'Symbol not found: '+symbol in text and 'SERVICE_RUNTIME_XCODE_STATUS 70' in text
        lsd=text.rsplit('+ launchctl list com.apple.lsd\n',1)[1]
        assert '"LastExitStatus" = 0;' in lsd and re.search(r'"PID" = [1-9][0-9]*;',lsd)
        assert 'Symbol not found: _DMNSError' not in text
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';sha='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5';add(original,sha);add('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild',sha)
archives={}
manifests=['artifacts/cryptex-workqueue-history/manifest.json','artifacts/dispatch-xpc-recorder-history/manifest.json','artifacts/xpc-sent-message-baseline-history/manifest.json']
manifests += [str(n.relative_to(root)) for n in (root/'artifacts/xcode-service-probe-history').glob('*/manifest.json')]
for n in manifests:
    data=read(n)
    for original,item in data.items():assert digest(item['archived'])==item['sha256'],(n,original)
    add(n);archives[n]=dict(sha256=digest(n),verified_files=len(data))
add('runtime/source-input-history/manifest.json')
for entry in frozen.values():add(entry['snapshot'],entry['sha256'])
for n in ['artifacts/darling-libdispatch-workloop-context-source.patch','artifacts/darling-diskmanagement-nserror-source.patch','artifacts/darling-libxpc-sent-message-source.patch']:add(n)
for repo,patch in [('vendor/darling/src/external/libdispatch','artifacts/darling-libdispatch-workloop-context-source.patch'),('vendor/darling','artifacts/darling-diskmanagement-nserror-source.patch'),('vendor/darling/src/external/libxpc','artifacts/darling-libxpc-sent-message-source.patch')]:subprocess.run(['git','-C',str(root/repo),'apply','--reverse','--check',str(root/patch)],check=True)
scripts=['scripts/'+n for n in ['build-dispatch-workloop-source.py','dispatch-workloop-runtime-profile.py','test-dispatch-workloop-context.py','build-diskmanagement-nserror-source.py','diskmanagement-nserror-runtime-profile.py','build-libxpc-source.py','stage-xpc-sent-message-runtime.py','xpc-sent-message-runtime-profile.py','test-xpc-loopback-sent.py','test-xpc-sent-message-regression.py','test-xpc-sent-mobileasset.py','trace-lsd-port-lifetime.py','capture-darling-stacks.py','annotate-macho-stack.py','probe-xcode-service-runtime.py','mdns-native-profile.py','verify-historical-source.py','record-dispatch-xpc-progress.py']]
scripts+=read('artifacts/dispatch-xpc-recorder-guards.json')
for n in scripts:add(n)
for n in ['fixtures/hello/dispatch-workloop-context.c','fixtures/hello/xpc-loopback-sent.c','bin/darling','bin/xcodebuild','scripts/runtime-ns.sh','artifacts/dispatch-xpc-recorder-guards.json']:add(n)
next_work=[
    'Recover the actual required AppleArchive Swift decryption/encryption interfaces and dependency closure, or implement them with genuine archive/crypto behavior; do not satisfy the loader with unsupported success or nil streams.',
    'Continue the unmodified original project build through actual compilation, Unity/CocoaPods integration, archive, signing and export; only then promote the default CI entry.',
    'Keep other generic DiskManagement stubs, AppleArchive processing gaps, Security/attestation, asset-download/trust daemons, Seatbelt profiles and C++ chained replacement limitations explicit until exercised and implemented.'
]
destination='artifacts/dispatch-xpc-progress.json'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,source_runtime=runtime,complete_libdispatch_source_files=32,libdispatch_exports_preserved=654,complete_libxpc_source_files=39,previous_selected_libxpc_exports_preserved=640,complete_DiskManagement_source_files=23,DMNSError_complete_code_identical_to_native=True,disk_operations_implemented=False,real_workloop_async_tasks=1024,real_loopback_checkins=16,real_loopback_request_reply_pairs=256,source_negative_controls_verified=True,original_xcode_probes=probes,current_original_project_exit_status=70,current_loader_symbol=symbol,current_loader_provider='/usr/lib/swift/libswiftAppleArchive.dylib',lsd_alive_at_latest_original_build_completion=True,all_lsd_lifetime_paths_proven=False,source_changes='Scoped current workloop context for the userspace fallback; successful Mach sends no longer destroy already-transferred rights and OOL resources; exact pinned native nil-return DMNSError source entry. Original Xcode remains unchanged.',historical_source_inputs=historical,archives=archives,evidence=evidence,scripts={n:digest(n) for n in scripts},next_work=next_work)
(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_original_xcode_blocker='AppleArchive Swift ArchiveByteStream.decryptionStream interface missing',latest_xcode_loader_blocker=symbol,latest_staged_coreml_and_metal_blocker='Required original Xcode plugin dependency closure',latest_xcode_failure_kind='AppleArchive_Swift_crypto_stream_interface',latest_xcode_runtime_failure='Strict UTI and original version/SDK queries pass. Original project returns 70 for AppleArchive Swift decryption stream; lsd is still running with LastExitStatus 0 at completion after workloop and XPC send-ownership repairs.',latest_implementation_form=record['source_changes'],active_build=dict(task='source-libdispatch-libxpc-lifetime-and-DiskManagement-entry',running=False,report=destination),next_work=next_work)
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded',len(evidence),'file hashes and',len(scripts),'scripts. Full build remains incomplete; goal active.')
