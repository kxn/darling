#!/usr/bin/env python3
"""Check the conservative proof and rerun existing semantics/safety inputs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,struct,subprocess
root=Path(__file__).resolve().parent.parent
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
build=root/'runtime/unrestricted-sandbox-tests';build.mkdir(exist_ok=True)
corpus=json.loads((root/'artifacts/native-sandbox-policy-corpus.json').read_text())
cases=[]
for name,item in corpus['policies'].items():
    assert digest(item['binary'])==item['sha256']
    # Even native (allow default) retains four implicit deny entries.
    cases.append((name,(root/item['binary']).read_bytes(),'restricted'))
original=(root/corpus['policies']['allow-all']['binary']).read_bytes();count=struct.unpack_from('<H',original,2)[0]
deny=next(i for i in range(count) if original[416+i*8]==1 and original[417+i*8]&1)
allow=next(i for i in range(count) if original[416+i*8]==1 and not original[417+i*8]&1)
unrestricted=bytearray(original)
for operation in range(198):struct.pack_into('<H',unrestricted,16+operation*2,allow)
cases.append(('all-operation-roots-allow',bytes(unrestricted),'unrestricted'))
for operation in range(198):
    b=bytearray(unrestricted);struct.pack_into('<H',b,16+operation*2,deny);cases.append(('deny-operation-'+str(operation),bytes(b),'restricted'))
explicit=build/'explicit-profile.bin'
if explicit.exists():cases.append(('native-explicit-allow-all',explicit.read_bytes(),'unrestricted'))
for reject in [False,True]:
    b=bytearray(440);struct.pack_into('<HHB',b,0,0,3,198)
    for i in range(198):struct.pack_into('<H',b,16+i*2,2)
    struct.pack_into('<BBHHH',b,416,1,0,0,0,0);struct.pack_into('<BBHHH',b,424,1,1,0,0,0)
    struct.pack_into('<BBHHH',b,432,0,43,4,0,1 if reject else 0)
    cases.append(('conditional-'+str(reject),bytes(b),'restricted' if reject else 'unrestricted'))
base=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'vendor/darlingserver/internal-include'),str(root/'vendor/darlingserver/src/sandbox-policy.cpp')]
rows=[]
for name,fixture in [('proof','sandbox-unrestricted-proof.cpp'),('semantic','sandbox-policy-vm.cpp'),('parser','sandbox-policy-parse.cpp')]:
    binary=build/name;command=[*base,str(root/'fixtures/hello'/fixture),'-o',str(binary)];subprocess.run(command,check=True)
    if name=='proof':
        data='\n'.join(b.hex() for _,b,_ in cases)+'\n';expect=[expected for _,_,expected in cases];args=[]
    elif name=='semantic':
        data=(root/'runtime/sandbox-policy-vm/queries.tsv').read_text();expect=[item['expected'] for item in json.loads((root/'runtime/sandbox-policy-vm/expectations.json').read_text())];args=[str(root/'runtime/sandbox-policy-corpus')]
    else:
        data=(root/'runtime/sandbox-policy-vm/parser-input.hex').read_text();expect=[line.split('\t',1)[0] for line in (root/'logs/native-sandbox-policy-parser.log').read_text().splitlines()];args=[]
    r=subprocess.run([str(binary),*args],input=data,text=True,capture_output=True);actual=r.stdout.splitlines()
    if name=='parser':actual=[line.split('\t',1)[0] for line in actual]
    log='logs/unrestricted-sandbox-'+name+'-test.log';(root/log).write_text(r.stdout+r.stderr)
    failures=[dict(index=i,expected=e,actual=a) for i,(e,a) in enumerate(zip(expect,actual)) if e!=a]
    ok=r.returncode==0 and len(actual)==len(expect) and not failures
    rows.append(dict(name=name,command=command,exit_status=r.returncode,cases=len(expect),passed=ok,failures=failures[:10],log=log,log_sha256=digest(log),binary=str(binary.relative_to(root)),binary_sha256=digest(binary)))
    print(name,'cases',len(expect),'passed',ok,failures[:3],flush=True)
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),checks=rows,ASan_UBSan=True,
            source_files={n:digest(n) for n in ['vendor/darlingserver/src/sandbox-policy.cpp','vendor/darlingserver/internal-include/darlingserver/sandbox-policy.hpp','fixtures/hello/sandbox-unrestricted-proof.cpp']},
            runtime_application_tested=False,all_passed=all(row['passed'] for row in rows))
(root/'artifacts/unrestricted-sandbox-proof-test.json').write_text(json.dumps(report,indent=2)+'\n');assert report['all_passed']
