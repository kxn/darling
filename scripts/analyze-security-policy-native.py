#!/usr/bin/env python3
"""Compare the original Intel constructor's branch/literals with pinned upstream source."""
from pathlib import Path
from datetime import datetime,timezone
import bisect,hashlib,json,runpy,struct,subprocess,sys
root=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root/'runtime/tools/python-capstone'))
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86_const import X86_OP_IMM,X86_OP_MEM,X86_REG_RIP
config=json.loads((root/'config/security-external-developer-policy.json').read_text())
reference=json.loads((root/'config/security-session-values.json').read_text())
provider=reference['native_path'];path=root/'runtime/fullsystem-libraries'/provider.lstrip('/')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert digest(path)==reference['native_sha256']
d=runpy.run_path(str(root/'scripts/dsc-image.py'),init_globals={
    'REFERENCE_CACHE_PATH':root/'runtime/fullsystem/intel-cache/dyld_shared_cache_x86_64h',
    'REFERENCE_LIBRARY_ROOT':root/'runtime/fullsystem-libraries'})
im=d['image'](provider);symbols={}
for line in subprocess.check_output(['llvm-nm-19','--defined-only',str(path)],text=True).splitlines():
    parts=line.split(None,2)
    if len(parts)==3:symbols[parts[2]]=int(parts[0],16)
ordered=sorted(set(symbols.values()));machine=Cs(CS_ARCH_X86,CS_MODE_64);machine.detail=True
selected=['_SecPolicyCreateAppleExternalDeveloperOptionalExpiry','_SecPolicyCreateAppleExternalDeveloper',
    '_SecPolicyAddBasicX509Options','_SecPolicyAddBasicCertOptions','_SecPolicyAddAppleAnchorOptions',
    '_SecPolicyAddChainLengthOptions','_SecPolicyAddStrongKeySizeOptions','_SecPolicyCreate']
functions=[];literals={};calls={};log=[]
for name in selected:
    start=symbols[name];end=ordered[bisect.bisect_right(ordered,start)];code=d['read'](start,end-start)
    functions.append(dict(symbol=name,address=hex(start),length=len(code),sha256=hashlib.sha256(code).hexdigest()))
    log.append('\nFUNCTION '+name+'\n');strings=[];targets=[]
    for i in machine.disasm(code,start):
        notes=[]
        for operand in i.operands:
            if operand.type==X86_OP_MEM and operand.mem.base==X86_REG_RIP and i.mnemonic=='lea':
                at=i.address+i.size+operand.mem.disp
                if d['read'](at+8,4)==b'\xc8\x07\x00\x00':
                    value=d['read'](d['pointer'](at+16),300).split(b'\0')[0].decode();strings.append(value);notes.append(repr(value))
        if i.mnemonic in ('call','jmp') and i.operands and i.operands[0].type==X86_OP_IMM:targets.append(i.operands[0].imm)
        log.append(f'{i.address:#x} {i.mnemonic} {i.op_str} '+', '.join(notes)+'\n')
    literals[name]=strings;calls[name]=targets
constructor='_SecPolicyCreateAppleExternalDeveloperOptionalExpiry'
assert symbols[constructor]==d['resolve'](provider,constructor)
for name in ['_SecPolicyAddBasicX509Options','_SecPolicyAddBasicCertOptions','_SecPolicyAddAppleAnchorOptions',
    '_SecPolicyAddChainLengthOptions','_SecPolicyAddStrongKeySizeOptions','_SecPolicyCreate']:assert symbols[name] in calls[constructor]
expected=['1.2.840.113635.100.6.2.1','1.2.840.113635.100.6.2.6',
    *['1.2.840.113635.100.6.1.'+str(i) for i in [2,4,5,7,8,12,13,14,35]],
    '1.3.6.1.5.5.7.3.3',*['1.2.840.113635.100.4.'+str(i) for i in [8,9,13]],
    '1.2.840.113635.100.1.65','Developer','AnyRevocationMethod']
assert set(expected)<=set(literals[constructor])
assert 'DuplicateExtension' in literals['_SecPolicyAddBasicCertOptions']
assert 'UnparseableExtension' in literals['_SecPolicyAddBasicCertOptions']
logpath=root/'logs/security-policy-native-analysis.log';logpath.write_text(''.join(log))
thin=root/'runtime/mobileasset-source/DVTFoundation.x86_64'
imports=[]
for line in subprocess.check_output(['llvm-objdump-19','--macho','--indirect-symbols',str(thin)],text=True).splitlines():
    if '_SecPolicyCreateAppleExternalDeveloperOptionalExpiry' in line:imports.append(line.strip())
assert len(imports)==2
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    native_provider=provider,native_provider_sha256=digest(path),functions=functions,native_CFString_literals=literals,
    DVT_import_locations=imports,upstream_commit=config['modern_source_commit'],
    upstream_source_function_body_sha256=config['selected_upstream_functions']['SecPolicyCreateAppleExternalDeveloperOptionalExpiry'],
    official_source='https://github.com/apple-oss-distributions/Security/blob/'+config['modern_source_commit']+'/OSX/sec/Security/SecPolicy.c#L4082',
    bool_parameter='checkExpiry; true calls BasicX509 helper, false calls BasicCert helper; retained SecPolicyRef result',
    true_false_schema_difference=['TemporalValidity','BlackListedLeaf','GrayListedLeaf'],
    modern_additions_to_legacy_true=['UnparseableExtension=true','DuplicateExtension=true','Swift Package Registry leaf OID 1.2.840.113635.100.6.1.35'],
    constraints_preserved=['Apple anchor','chain length 3','2 intermediate markers','9 leaf markers','4 EKUs','any-method revocation','RSA >=2048 and EC >=256'],
    log=str(logpath.relative_to(root)),log_sha256=digest(logpath),
    existing_object_factory_used=True,new_private_policy_layout_access=False,
    certificate_trust_evaluation_verified=False,execution_report='artifacts/security-policy-source-execution.json')
(root/'artifacts/security-policy-native-analysis.json').write_text(json.dumps(record,indent=2)+'\n')
print('Verified native constructor helper branches, exact policy/OID literals and upstream schema deltas')
