#!/usr/bin/env python3
"""Check original native programs, malformed uploads and deterministic mutation safety."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,random,struct,subprocess
root=Path(__file__).resolve().parent.parent;digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
corpus=json.loads((root/'artifacts/native-sandbox-policy-corpus.json').read_text());build=root/'runtime/sandbox-policy-vm';build.mkdir(exist_ok=True);binary=build/'parse'
command=['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(root/'vendor/darlingserver/internal-include'),str(root/'vendor/darlingserver/src/sandbox-policy.cpp'),str(root/'fixtures/hello/sandbox-policy-parse.cpp'),'-o',str(binary)];subprocess.run(command,check=True)
originals={n:(root/item['binary']).read_bytes() for n,item in corpus['policies'].items()};cases=[]
for name,b in originals.items():assert hashlib.sha256(b).hexdigest()==corpus['policies'][name]['sha256'];cases.append((name,b,True))
core=originals['coreservicesd'];node_count=struct.unpack_from('<H',core,2)[0];assert node_count==37
for end in range(len(core)):cases.append(('truncated-'+str(end),core[:end],False))
def mutation(label,at,data):
    b=bytearray(core);b[at:at+len(data)]=data;cases.append((label,bytes(b),False))
mutation('wrong-profile-kind',0,b'\x01\0');mutation('zero-nodes',2,b'\0\0');mutation('truncated-node-count',2,b'\xff\xff');mutation('wrong-op-table',4,b'\xc5')
for at in range(5,16):mutation('unsupported-header-'+str(at),at,b'\x01')
for i in range(198):mutation('entry-out-of-bounds-'+str(i),16+i*2,b'\xff\xff')
for i in range(node_count):
    at=416+i*8;mutation('unknown-node-type-'+str(i),at,b'\xff')
    if core[at]==0:
        for edge in [4,6]:mutation('edge-out-of-bounds-'+str(i)+'-'+str(edge),at+edge,b'\xff\xff');mutation('cycle-'+str(i)+'-'+str(edge),at+edge,struct.pack('<H',i))
        if core[at+1] in [1,5,6,7,10,17,18,28,38,50]:mutation('pattern-reference-out-of-bounds-'+str(i),at+2,b'\xff\xff')
    else:mutation('unsupported-action-'+str(i),at+1,b'\xff')
cases.append(('oversized-upload',b'\0'*(1024*1024+1),False))
rng=random.Random(440044);base=list(originals.values())
for i in range(3000):
    b=bytearray(rng.choice(base))
    for _ in range(rng.randrange(1,12)):b[rng.randrange(len(b))]=rng.randrange(256)
    cases.append(('mutation-'+str(i),bytes(b),None))
stream='\n'.join(b.hex() for _,b,_ in cases)+'\n';(build/'parser-input.hex').write_text(stream)
r=subprocess.run([str(binary)],input=stream,text=True,capture_output=True);log='logs/native-sandbox-policy-parser.log';(root/log).write_text(r.stdout+r.stderr)
actual=r.stdout.splitlines();failures=[]
if r.returncode or len(actual)!=len(cases):failures.append(dict(exit_status=r.returncode,actual_rows=len(actual),expected_rows=len(cases),stderr=r.stderr))
for (name,b,expected),out in zip(cases,actual):
    if expected is not None and out.startswith('accept\t')!=expected:failures.append(dict(name=name,expected_accept=expected,actual=out))
record=dict(checked_at=datetime.now(timezone.utc).isoformat(),exit_status=r.returncode,cases=len(cases),valid_original_programs=len(originals),malformed_rejection_cases=sum(v is False for _,_,v in cases),mutation_safety_cases=3000,mutated_programs_accepted=sum(out.startswith('accept') for out in actual[-3000:]),ASan_UBSan=True,failures=failures,binary=str(binary.relative_to(root)),binary_sha256=digest(binary),build_command=command,input='runtime/sandbox-policy-vm/parser-input.hex',input_sha256=digest('runtime/sandbox-policy-vm/parser-input.hex'),log=log,log_sha256=digest(log),policy_application_implemented=False)
(root/'artifacts/native-sandbox-policy-parser-test.json').write_text(json.dumps(record,indent=2)+'\n');print('Parser cases',len(cases),'failures',len(failures));print(json.dumps(failures[:10],indent=2));assert not failures
