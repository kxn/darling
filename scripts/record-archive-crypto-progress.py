#!/usr/bin/env python3
"""Record executed native archive streams and the actual next Xcode failure."""

# Preserve the newer native cryptography and FileCoordination checkpoint.
from pathlib import Path as _nc_Path
import json as _nc_json
_nc_state = _nc_Path(__file__).resolve().parent.parent / 'artifacts/current-work-state.json'
if _nc_state.exists() and _nc_json.loads(_nc_state.read_text()).get('primary_report') == 'artifacts/native-crypto-progress.json':
    print('Preserving the newer native cryptography checkpoint'); raise SystemExit(0)
from pathlib import Path
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,re,runpy,subprocess
root=Path(__file__).resolve().parent.parent
read=lambda n:json.loads((root/n).read_text())
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
evidence={}
def add(n,sha=None):
    actual=digest(n)
    if sha is not None:assert actual==sha,n
    evidence[str(n)]=actual
def walk(value):
    if isinstance(value,list):
        for item in value:walk(item)
    elif isinstance(value,dict):
        for key,item in value.items():
            if isinstance(item,str) and isinstance(value.get(key+'_sha256'),str) and (root/item).is_file():add(item,value[key+'_sha256'])
            if key=='sha256':
                for pathkey in ['path','source','file']:
                    if isinstance(value.get(pathkey),str) and (root/value[pathkey]).is_file():add(value[pathkey],item)
            if isinstance(item,str) and re.fullmatch('[a-f0-9]{64}',item) and (root/key).is_file():add(key,item)
            if isinstance(item,(list,dict)):walk(item)
def report(n,fields=None):
    d=read(n);add(n)
    walk(d if fields is None else {k:d[k] for k in fields})
    return d

p=runpy.run_path(str(root/'scripts/argument-parser-native-profile.py'))['profile']()
runtime=p['source_runtime']
for item in runtime.values():add(item['path'],item['sha256'])
core=report('artifacts/corecrypto-hkdf-source-build.json')
assert core['full_CoreCrypto_source_build'] and core['complete_source_files']==55 and core['original_exports_preserved']==402
assert not core['other_preexisting_CoreCrypto_stubs_implemented']
for name,count,key in [('hkdf',210,'independent_HMAC_HKDF_cases'),('ctr',81,'independent_OpenSSL_cases')]:
    d=report('artifacts/corecrypto-'+name+'-test.json');assert d['runtime_execution_verified'] and d[key]==count and d['exit_status']==0
    assert d['corecrypto']==core and d['source_runtime']==runtime
archive=report('artifacts/applearchive-native-stage.json')
assert not archive['installed'] and not archive['backend_overrides']
assert [d['exports'] for d in archive['images']]==[232,909,70]
native=report('artifacts/applearchive-native-hkdf-test.json',['checks','sources','binaries','native_applearchive','source_corecrypto_hkdf'])
assert native['runtime_execution_verified'] and native['original_Apple_SDK_interface_used']
assert native['native_applearchive']==archive and native['source_corecrypto_hkdf']==core
text=(root/native['checks'][-1]['log']).read_text()
for marker in ['NATIVE_ARCHIVE_COMPRESSION_OK '+n+' 65537' for n in ['none','zlib','lz4','lzfse']]+['NATIVE_ARCHIVE_ENCRYPTION_ROUNDTRIP_OK 65537','NATIVE_ARCHIVE_WRONG_KEY_REJECTED','NATIVE_ARCHIVE_CORRUPTION_REJECTED','NATIVE_APPLEARCHIVE_STREAMS_OK']:
    assert marker in text,marker
assert 'STUB' not in text
parser=report('artifacts/argument-parser-native-stage.json');assert parser['exports']==707 and not parser['backend_overrides']
loaded=report('artifacts/argument-parser-native-load.json');assert loaded['native_dlopen_verified'] and loaded['stage']==parser
regression=report('artifacts/archive-parser-regression.json',['checks'])
assert len(regression['checks'])==6 and all(d['exit_status']==0 for d in regression['checks'])
assert regression['native_applearchive']==archive and regression['source_corecrypto_hkdf']==core and regression['native_argument_parser']==parser

probes={}
for mode in ['version','showsdks','build']:
    names=list((root/'artifacts').glob('xcode-service-runtime-parser-hkdf-*prefs-daemon-'+mode+'.json'));assert len(names)==1
    n=str(names[0].relative_to(root));d=report(n,['jobs','service_logs','original_preference_service'])
    for key in ['log','script']:add(d[key],d[key+'_sha256'])
    assert d['source_runtime']==runtime and d['native_applearchive']==archive and d['source_corecrypto_hkdf']==core and d['native_argument_parser']==parser
    assert d['UTI_preflight_verified'] and d['xcode_process_started'] and d['xcode_process_returned']
    text=(root/d['log']).read_text()
    if mode!='build':assert d['exit_status']==0 and 'SERVICE_RUNTIME_XCODE_STATUS 0' in text
    else:
        assert 'Build settings from command line:' in text
        assert 'Symbol not found: _$s12AppleArchive' not in text and 'Library not loaded: /System/Library/PrivateFrameworks/ArgumentParserInternal' not in text
        assert 'Symbol not found: _$s9CryptoKit13SecureEnclaveO' in text
        assert 'SERVICE_RUNTIME_XCODE_STATUS 132' in text and d['exit_status']==-9
    probes[mode]=dict(report=n,report_sha256=digest(n),wrapper_exit_status=d['exit_status'],original_xcode_returned=d['xcode_process_returned'])

crypto_stage=report('artifacts/cryptokit-original-stage.json');crypto_load=report('artifacts/cryptokit-original-load.json')
assert crypto_load['stage']==crypto_stage and crypto_load['checks'][0]['native_dlopen_verified']
assert not crypto_load['all_selected_images_load'] and not crypto_load['checks'][1]['native_dlopen_verified']
assert 'Symbol not found: _ccsha3_256_di' in (root/crypto_load['checks'][1]['log']).read_text()
for target in ['apple-archive-crypto-native','swift-apple-archive-crypto-native','swift-compression-archive-native','argument-parser-internal-native','cryptokit-native-original','cryptokit-cbridging-native-original']:
    d=report('runtime/rebuilt-'+target+'/reconstruction.json')
    assert not d['modern_adapter'] and not d['backend_call_overrides'] and not d['redirected_imports']

archives={}
for n in ['artifacts/dispatch-xpc-history/manifest.json','artifacts/corecrypto-hkdf-source-history/manifest.json','artifacts/corecrypto-hkdf-pre-ctr-history/manifest.json','artifacts/applearchive-native-initial-history/manifest.json','artifacts/archive-crypto-recorder-history/manifest.json','artifacts/native-archive-load-report-history/manifest.json']:
    d=read(n)
    for original,item in d.items():assert digest(item['archived'])==item['sha256'],(n,original)
    add(n);archives[n]=dict(sha256=digest(n),verified_files=len(d))
guards=read('artifacts/archive-crypto-recorder-guards.json');assert len(guards)==32
scripts=guards+['scripts/'+n for n in ['stage-applearchive-native.py','applearchive-native-profile.py','probe-applearchive-native.py','test-applearchive-native.py','build-corecrypto-hkdf-source.py','corecrypto-hkdf-profile.py','test-corecrypto-hkdf.py','test-corecrypto-ctr.py','stage-argument-parser-native.py','probe-argument-parser-native.py','argument-parser-native-profile.py','test-archive-parser-regression.py','stage-cryptokit-original.py','cryptokit-original-profile.py','probe-cryptokit-original.py','probe-xcode-service-runtime.py','rebuild-c-cache-image.py','restore-swift-metadata.py','audit-cache-code-imports.py','record-archive-crypto-progress.py']]
for n in scripts:ast.parse((root/n).read_text());add(n)
for n in ['fixtures/hello/applearchive-native.swift','fixtures/hello/applearchive-native-owner.c','fixtures/hello/corecrypto-hkdf.c','fixtures/hello/corecrypto-ctr.c','config/cache-image-pins.json','artifacts/archive-crypto-recorder-guards.json','artifacts/darling-corecrypto-hkdf-hmac-ctr-source.patch','bin/darling','bin/xcodebuild','scripts/runtime-ns.sh','README.md']:
    add(n)
subprocess.run(['git','-C',str(root/'vendor/darling/src/external/corecrypto'),'apply','--reverse','--check',str(root/'artifacts/darling-corecrypto-hkdf-hmac-ctr-source.patch')],check=True)
original='runtime/state/prefix/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild';sha='d6ceec0a4fa47e3f7a20c712d960ffb954b2246a2c94a0bf0818b2e8344065c5'
add(original,sha);add('runtime/xcode-extract/Xcode.app/Contents/Developer/usr/bin/xcodebuild',sha)
with (root/'runtime/session.lock').open('a') as lock:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
next_work=[
    'Resolve original CryptoKit SecureEnclave ABI used by SwiftPM. Complete original CryptoKit/C bridge dependency support beginning with genuine CoreCrypto SHA3 descriptors; inspect PQC requirements without fake cryptographic success or fabricated hardware keys.',
    'Retry original project build, diagnose any remaining CoreSimulator/service waits and server corpse-info failure from saved live traces, then execute actual project compilation.',
    'Complete Unity/CocoaPods, archive, code signing and export with original CI commands; only then promote the default entry. Full AppleArchive processing, other CoreCrypto algorithms and hardware-backed Security remain unproven.'
]
destination='artifacts/archive-crypto-progress.json'
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),goal_status='active',complete=False,full_xcode_build_ready=False,signing_ready=False,default_entry_promoted=False,source_runtime=runtime,complete_CoreCrypto_source_files=55,CoreCrypto_previous_exports_preserved=402,HMAC_HKDF_independent_cases=210,AES_CTR_independent_cases=81,original_AppleArchive_exports=[232,909,70],compression_formats_verified=['none','zlib','lz4','lzfse'],encrypted_byte_stream_payload_size=65537,wrong_key_rejected=True,ciphertext_corruption_rejected=True,original_ArgumentParser_exports=707,ArgumentParser_dlopen_verified=True,full_ArgumentParser_semantics_verified=False,original_xcode_probes=probes,original_xcode_build_status=132,build_wrapper_killed_after_server_failure=True,current_loader_symbol='_$s9CryptoKit13SecureEnclaveO4P256O7SigningO10PrivateKeyV06publicH0AaDOAFO06PublicH0Vvg',current_loader_provider='/System/Library/Frameworks/CryptoKit.framework/Versions/A/CryptoKit',native_CryptoKit_candidate_loads=False,native_CryptoKit_candidate_next_missing_symbol='_ccsha3_256_di',hardware_enclave_implemented=False,hardware_enclave_availability_verified=False,source_changes='Real HKDF extract/expand, corrected long-key HMAC padding, real streaming AES-CTR and its ECB block size in Darling source. Original AppleArchive C/Swift/Compression and ArgumentParser cache code recovered without call overrides. Original Xcode unchanged.',archives=archives,evidence=evidence,scripts={n:digest(n) for n in scripts},next_work=next_work)
(root/destination).write_text(json.dumps(record,indent=2)+'\n')
state=read('artifacts/current-work-state.json');state.update(updated_at=record['checked_at'],primary_report=destination,goal_status='active',complete=False,latest_selected_runtime=runtime,latest_original_xcode_blocker='SwiftPM CryptoKit SecureEnclave ABI; original CryptoKit candidate requires real CoreCrypto SHA3 descriptors',latest_xcode_loader_blocker=record['current_loader_symbol'],latest_xcode_failure_kind='CryptoKit_SecureEnclave_ABI_and_original_CryptoKit_backend',latest_xcode_runtime_failure='Original version and SDK queries pass with strict UTI. Original build passes AppleArchive/ArgumentParser discovery, reports a CryptoKit SecureEnclave symbol missing, returns 132; driver is killed after failed server cleanup. Saved live stacks also show a CoreSimulator service wait.',latest_sdk_listing_succeeded=True,latest_sdk_listing_attempted=True,latest_original_project_exit_status=132,latest_implementation_form=record['source_changes'],active_build=dict(task='native-AppleArchive-source-CoreCrypto-and-ArgumentParser',running=False,report=destination),next_work=next_work)
new_verifications=['Original AppleArchive C + Swift + Compression executed none/zlib/lz4/lzfse roundtrips of 65537 bytes; authenticated symmetric AEA roundtrip, wrong key and ciphertext corruption checks passed','All 55 Darling CoreCrypto sources rebuilt; 402 old exports preserved. Real HKDF/HMAC passed 210 independent OpenSSL-backed comparisons; streaming AES128/192/256 CTR passed 81 independent ECB-counter comparisons and chunk/reset/in-place guards','Original ArgumentParserInternal 707 exports reconstructed and actual dlopen passed; original Xcode moved to SwiftPM SecureEnclave CryptoKit ABI failure','Original CryptoKit 1823 exports and C bridge 29 exports privately reconstructed. C bridge dlopen passes; original CryptoKit loader explicitly rejects missing _ccsha3_256_di. Neither promoted nor claimed compatible']
state.setdefault('last_verification',[]).extend(v for v in new_verifications if v not in state['last_verification'])
(root/'artifacts/current-work-state.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded',len(evidence),'current hashes and',len(scripts),'scripts; full goal remains active.')
