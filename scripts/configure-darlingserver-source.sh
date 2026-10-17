#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
python3 scripts/prepare-darlingserver-host-tools.py
python3 - <<'PY'
from pathlib import Path
import json,subprocess
c=json.loads(Path('config/darlingserver-source-build.json').read_text())
if not (Path(c['bootstrap_source'])/'CMakeLists.txt').exists():
    subprocess.run(['git','-C',c['darling_source'],'submodule','update','--init','--depth','1','src/external/bootstrap_cmds'],check=True)
for prefix in ['server','darling','bootstrap']:
    actual=subprocess.check_output(['git','-C',c[prefix+'_source'],'rev-parse','HEAD'],text=True).strip()
    assert actual==c[prefix+'_commit'], 'Changed source revision: '+prefix
PY
export PATH="$project/runtime/host-build-tools/usr/bin:$PATH"
export BISON_PKGDATADIR="$project/runtime/host-build-tools/usr/share/bison"
export M4="$project/runtime/host-build-tools/usr/bin/m4"
cmake -S build-support/darlingserver -B runtime/darlingserver-source-build -G Ninja \
    -DCMAKE_C_COMPILER=clang-19 -DCMAKE_CXX_COMPILER=clang++-19 \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DBISON_EXECUTABLE="$project/runtime/host-build-tools/usr/bin/bison" \
    -DFLEX_EXECUTABLE="$project/runtime/host-build-tools/usr/bin/flex"
cmake --build runtime/darlingserver-source-build --target darlingserver -j 8
