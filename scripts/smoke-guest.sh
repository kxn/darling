#!/bin/bash
set -eu
test "$(uname -s)" = Darwin
test "$(uname -m)" = x86_64
uname -a
sw_vers
printf 'linuxcode-persistent-state\n' > "$HOME/linuxcode-smoke.txt"
/usr/bin/python2.7 -c 'import plistlib; p="/tmp/linuxcode-smoke.plist"; plistlib.writePlist({"platform": "Darwin", "valid": True}, p); assert plistlib.readPlist(p)["valid"]'
/usr/bin/ruby -e 'require "json"; abort unless JSON.parse("{\"valid\":true}")["valid"]; puts RUBY_DESCRIPTION'
test ! -e /Volumes/SystemRoot/home/dl
printf 'GUEST_SMOKE_OK\n'
