#!/usr/bin/env python3
"""Inspect actual Intel MobileAsset manager/connection Objective-C metadata."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('analyze-logging-stream-native.py')),init_globals={
    'ANALYSIS_PROVIDER':'/System/Library/PrivateFrameworks/MobileAsset.framework/Versions/A/MobileAsset',
    'ANALYSIS_CLASS_NAMES':['MAXpcManager','MAXpcConnection'],
    'ANALYSIS_PREFIX':'mobileasset-xpc',
    'ANALYSIS_NOTE':'Darling MAXpcManager/MAXpcConnection are generic forwarding stubs; the Pallas getter is absent. This is static protocol evidence, not daemon execution proof.'})
