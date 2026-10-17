#!/usr/bin/env python3
"""Compare the Linux decision interpreter with independent SBPL/regex test expectations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,random,re,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
corpus=json.loads((root/'artifacts/native-sandbox-policy-corpus.json').read_text())
for item in corpus['policies'].values():assert digest(item['binary'])==item['sha256']
build=root/'runtime/sandbox-policy-vm';build.mkdir(exist_ok=True);binary=build/'evaluate'
command=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'vendor/darlingserver/internal-include'),str(root/'vendor/darlingserver/src/sandbox-policy.cpp'),str(root/'fixtures/hello/sandbox-policy-vm.cpp'),'-o',str(binary)]
subprocess.run(command,check=True)
rng=random.Random(8675309);cases=[]
STRING_FILTERS={'path':1,'posix':5,'global':6,'local':7,'control':10,'iokitClass':17,'iokitProperty':18,'preference':28,'sysctl':38,'xpc':50}
ALL_ABSENT=sum(1<<i for i in STRING_FILTERS.values())
def add(policy,op,expect,**context):
    absent=ALL_ABSENT
    for name in context:
        if name in STRING_FILTERS:absent&=~(1<<STRING_FILTERS[name])
    context['absent']=absent
    cases.append(dict(policy=policy,operation=op,context=context,expected=('allow' if expect else 'deny') if isinstance(expect,bool) else expect))
def under(path,parent):return path==parent or path.startswith(parent+'/')
paths=['/','/tmp','/tmp/darling-sandbox-policy','/tmp/darling-sandbox-policy/','/tmp/darling-sandbox-policy/a','/tmp/darling-sandbox-policy-other/a','/tmp/darling-sandbox-policy/file','/tmp/darling-sandbox-policy/file/a','/tmp/darling-policy/','/tmp/darling-policy/any','/tmp/alpha','/tmp/alphabet','/tmp/alphabet/','/tmp/beta','/tmp/item-a0','/tmp/item-b12345','/tmp/item-c9','/tmp/item-d1','/tmp/item-a','/tmp/item-a12x','/tmp/abc','/tmp/abd33','/tmp/z','/tmp/z1','/tmp/abcx','/tmp/ab','/tmp/darling-1','/tmp/darling-x-darling-123','/tmp/darling-123x','/tmp/allowed','/tmp/allowed/a','/tmp/allowed-other','/tmp/'+('abcdefghij'*29)]
paths+=['/tmp/group/'+str(i)+'-'+('x'*36) for i in range(22)]
for i in range(320):
    segment=''.join(rng.choice('abcxyz0123456789-_') for _ in range(rng.randrange(0,24)))
    paths.append(rng.choice(['/tmp/','/tmp/darling-sandbox-policy/','/tmp/darling-sandbox-policy-','/tmp/darling-policy/','/tmp/item-','/tmp/allowed/'])+segment)
for path in paths:
    # The VM receives canonical guest paths; these vectors contain no dot
    # components or duplicate separators. Case folding is ASCII for this pin.
    lower=path.lower()
    for name,op,expected in [
        ('allow-all','file-read-data',True),('deny-all','file-read-data',False),
        ('subpath-read','file-read-data',under(lower.rstrip('/'),'/tmp/darling-sandbox-policy')),
        ('literal-read','file-read-data',lower=='/tmp/darling-sandbox-policy/file'),
        ('regex-read','file-read-data',bool(re.fullmatch(r'/tmp/darling-policy/.*',lower,re.S))),
        ('write-temp','file-write-data',under(lower.rstrip('/'),'/tmp/darling-sandbox-policy')),
        ('negated-path','file-write-data',under(lower.rstrip('/'),'/tmp/allowed')),
        ('disjunction','file-read-data',lower in ['/tmp/alpha','/tmp/alphabet','/tmp/beta']),
        ('ranges','file-read-data',bool(re.fullmatch(r'/tmp/item-[a-c][0-9]+',lower))),
        ('alternation','file-read-data',bool(re.fullmatch(r'/tmp/(abc|abd|z)[0-9]*',lower))),
        ('seek','file-read-data',bool(re.search(r'darling-[0-9]+$',lower))),
        ('long-literal','file-read-data',lower=='/tmp/'+('abcdefghij'*29)),
        ('long-alternation','file-read-data',lower in ['/tmp/group/'+str(i)+'-'+('x'*36) for i in range(20)]),
    ]:add(name,op,expected,path=path)
for name in ['com.apple.DiskArbitration.diskarbitrationd','com.apple.diskarbitration.diskarbitrationd','com.apple.DiskArbitration.diskarbitrationd.more','org.example.debug','org.example.platform','org.example.installer','org.example.initproc','org.example.unknown']:
    add('mach-service','mach-lookup',name=='com.apple.DiskArbitration.diskarbitrationd',**{'global':name})
    for mask in range(32):
        for policy,service,bit in [('platform-only','org.example.platform',4),('installer-only','org.example.installer',1),('initproc-only','org.example.initproc',3)]:
            add(policy,'mach-lookup',name==service and bool(mask&(1<<bit)),**{'global':name,'attributes':mask})
        add('global-and-debug','mach-lookup',name=='org.example.debug' and bool(mask&2),**{'global':name,'systemAttributes':mask})
for self in [0,1]:
    add('self-only','mach-task-name',bool(self),self=self)
    # Native compiler emits a self-allow prologue before allow-others rules
    # for both Mach task names and signals. These are explicit compiler
    # conformance cases; the remaining predicate cases use source expectations.
    add('other-only','mach-task-name',True,self=self)
    add('signal-other-only','signal',True,self=self)
for path in ['/tmp/files','/tmp/files/a','/tmp/files-other/a','/tmp/other']:
    for vnode in range(1,8):add('regular-file-only','file-write-create',under(path,'/tmp/files') and vnode==1,path=path,vnode=vnode)
for value in ['/tmp/com.apple.csseed.123','/tmp/comXappleYcsseedZ42','/tmp/com.apple.csseed.','/tmp/com.apple.csseed.123x','/tmp/com.apple.csseed.1/','/tmp/com.apple.csseed.000001']:
    add('posix-name','ipc-posix-shm-write-create',bool(re.fullmatch(r'/tmp/com.apple.csseed.[0-9]+',value)),posix=value)
for value in ['Protocol Characteristics','CaseSensitive','caseSensitive','Protocol CharacteristicsExtra','Unknown']:
    add('io-property','iokit-get-properties',value in ['Protocol Characteristics','CaseSensitive'],iokitProperty=value)
for value in ['org.example.preferences','org.example.preferences.more','org.example.Preferences']:
    add('preference','user-preference-read',value=='org.example.preferences',preference=value)
# Expectations below follow the original named source and system.sb imports,
# not a decompiler's reconstructed text or the VM's output.
for path in ['/tmp/com.apple.coreservicesd','/tmp/com.apple.coreservicesd/a','/tmp/com.apple.coreservicesd-other/a','/root/.cache/com.apple.coreservicesd/a','/tmp/other','/dev/null','/dev/zero','/dev/fd/9','/dev/fd-other/9','/System/Library/Caches/com.apple.Components2.SystemCache.Components','/System/Library/Caches/com.apple.Components2.SystemCache.ComponentsExtra']:
    allow=under(path,'/tmp/com.apple.coreservicesd') or under(path,'/root/.cache/com.apple.coreservicesd') or under(path,'/dev/fd') or path in ['/dev/null','/dev/zero','/dev/dtracehelper'] or path.lower() in ['/system/library/caches/com.apple.components2.systemcache.'+n for n in ['components','audiocomponents','quicktimecomponents']]
    add('coreservicesd','file-write-data',allow,path=path);add('coreservicesd','file-read-data',True,path=path)
for mask in [0,1,2,3]:
    for path in ['/usr/lib','/usr/lib/libSystem.B.dylib','/usr/library/file','/System/Library/Frameworks/Foo','/AppleInternal/usr/lib/Foo','/tmp/Foo']:
        expected=under(path.lower(),'/usr/lib') or under(path.lower(),'/system/library/frameworks') or (bool(mask&1) and under(path.lower(),'/appleinternal/usr/lib'))
        add('coreservicesd','file-map-executable',expected,path=path,systemAttributes=mask)
for service in ['com.apple.DiskArbitration.diskarbitrationd','com.apple.logd','com.apple.cfprefsd.daemon','com.apple.cfprefsd.daemon.system','com.apple.cfprefsd.daemon.system.more','com.apple.bsd.dirhelper','org.example.unknown']:
    add('coreservicesd','mach-lookup',service in ['com.apple.DiskArbitration.diskarbitrationd','com.apple.logd','com.apple.cfprefsd.daemon','com.apple.cfprefsd.daemon.system','com.apple.bsd.dirhelper'],**{'global':service,'systemAttributes':0,'attributes':0})
for key in ['Removable','Ejectable','CaseSensitive','Encrypted','NotAProperty']:
    add('coreservicesd','iokit-get-properties',key!='NotAProperty',iokitProperty=key)
for key in ['kern.grade_cputype','kern.wq_limit_cooperative_threads','vm.task_no_footprint_for_debug','kern.other']:
    for mask in [0,1,2]:add('coreservicesd','sysctl-write',key in ['kern.grade_cputype','kern.wq_limit_cooperative_threads'] or (key=='vm.task_no_footprint_for_debug' and bool(mask&1)),sysctl=key,systemAttributes=mask)
# Missing context is distinct from a context known to be absent, and malformed
# path spellings must not be treated as resolved filesystem identities.
for policy,op,context in [('subpath-read','file-read-data',{}),('global-and-debug','mach-lookup',{'global':'org.example.debug'}),('platform-only','mach-lookup',{'global':'org.example.platform'}),('self-only','mach-task-name',{})]:
    cases.append(dict(policy=policy,operation=op,context=context,expected='unsupported'))
for path in ['relative','/tmp/darling-sandbox-policy/../outside','/tmp//darling-sandbox-policy/a','/tmp/./darling-sandbox-policy']:
    add('subpath-read','file-read-data','unsupported',path=path)
add('allow-all','not-a-real-operation','unsupported')
queries='\n'.join('\t'.join([c['policy'],c['operation'],*[k+'='+str(v) for k,v in c['context'].items()]]) for c in cases)+'\n'
(build/'queries.tsv').write_text(queries);(build/'expectations.json').write_text(json.dumps(cases,indent=2)+'\n')
r=subprocess.run([str(binary),str(root/'runtime/sandbox-policy-corpus')],input=queries,text=True,capture_output=True);(root/'logs/native-sandbox-policy-vm.log').write_text(r.stdout+r.stderr)
actual=r.stdout.splitlines();failures=[]
if r.returncode or len(actual)!=len(cases):failures.append(dict(exit_status=r.returncode,actual_rows=len(actual),expected_rows=len(cases),stderr=r.stderr))
for i,(case,value) in enumerate(zip(cases,actual)):
    if case['expected']!=value:failures.append(dict(index=i,case=case,actual=value))
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),exit_status=r.returncode,semantic_cases=len(cases),policies=len(corpus['policies']),failures=failures,source_policies='artifacts/native-sandbox-policy-corpus.json',source_policies_sha256=digest('artifacts/native-sandbox-policy-corpus.json'),queries='runtime/sandbox-policy-vm/queries.tsv',queries_sha256=digest('runtime/sandbox-policy-vm/queries.tsv'),expectations='runtime/sandbox-policy-vm/expectations.json',expectations_sha256=digest('runtime/sandbox-policy-vm/expectations.json'),log='logs/native-sandbox-policy-vm.log',log_sha256=digest('logs/native-sandbox-policy-vm.log'),binary=str(binary.relative_to(root)),binary_sha256=digest(binary),build_command=command,ASan_UBSan=True,policy_application_implemented=False)
(root/'artifacts/native-sandbox-policy-vm-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Semantic cases',len(cases),'failures',len(failures));print(json.dumps(failures[:15],indent=2));assert not failures
