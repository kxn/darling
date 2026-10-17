#!/usr/bin/env python3
"""Reconstruct the pinned CoreEntitlements image using the shared C image tool."""
from pathlib import Path
import subprocess
import sys

script=Path(__file__).with_name('rebuild-c-cache-image.py')
raise SystemExit(subprocess.run([sys.executable,str(script),'--target','coreentitlements',*sys.argv[1:]]).returncode)
