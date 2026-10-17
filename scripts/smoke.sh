#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
cd "$project"
snapshot() {
    ls /proc/sys/fs/binfmt_misc
    cat /proc/self/mountinfo
    cat /proc/modules
    dpkg-query -W
}
snapshot > logs/host-smoke-before.txt
timeout 60 bin/darling shell /bin/bash /Volumes/SystemRoot/workspace/scripts/smoke-guest.sh \
    > logs/smoke-guest.log 2>&1
timeout 30 bin/darling shell /bin/bash -c 'test "$(cat "$HOME/linuxcode-smoke.txt")" = linuxcode-persistent-state; printf "PERSISTENCE_OK\n"' \
    > logs/smoke-persistence.log 2>&1
timeout 30 bin/darling --linux /bin/bash -c \
    'test ! -e /home/dl; test -e /workspace/bin/darling; test "$(id -u)" = 0; cat /proc/self/uid_map; cat /proc/sys/fs/binfmt_misc/Mach-O-64-bit' \
    > logs/smoke-isolation.log 2>&1
set +e
timeout 30 bin/darling shell /bin/bash -c 'exit 7' > logs/smoke-exit-code.log 2>&1
status=$?
set -e
test "$status" -eq 7
snapshot > logs/host-smoke-after.txt
diff -u logs/host-smoke-before.txt logs/host-smoke-after.txt > logs/host-smoke.diff
printf 'Darwin runtime, script runtimes, persistence and host isolation passed.\n'
