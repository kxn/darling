#!/usr/bin/env python3
"""Read-only metadata and bounded method inspection of original Intel displays."""
from pathlib import Path
import hashlib,json,runpy,struct
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/ca-render-server.json').read_text())
original=root/'runtime/fullsystem-libraries'/config['provider'].lstrip('/')
assert hashlib.sha256(original.read_bytes()).hexdigest()==config['provider_sha256']
analysis=runpy.run_path(str(root/'scripts/analyze-logging-stream-native.py'),init_globals={
    'ANALYSIS_PROVIDER':config['provider'],
    'ANALYSIS_CLASS_NAMES':['CADisplay','CADisplayMode','CADisplayAttributes'],
    'ANALYSIS_PREFIX':'ca-display',
    'ANALYSIS_NOTE':'Darling QuartzCore has no CADisplay class. Existing CG display enumeration uses AppKit/NSDisplay; headless failure must not be turned into a synthetic display.'})
constants=[]
for name,address,expected in [('factory_rate_multiplier',0x7ff80d41a878,65536.0),
        ('getter_rate_multiplier',0x7ff80d41a868,100.0/65536),('getter_final_multiplier',0x7ff80d41a870,0.01)]:
    payload=analysis['read'](address,8);assert struct.unpack('<d',payload)[0]==expected
    constants.append(dict(name=name,address=hex(address),bytes=payload.hex(),value=expected))
path=root/'artifacts/ca-display-native-analysis.json';report=json.loads(path.read_text())
report['mode_rate_scalar_constants']=constants
report['mode_rate_fixed_point_fractional_bits']=16
report['mode_serialized_copy_length']=16
path.write_text(json.dumps(report,indent=2)+'\n')
