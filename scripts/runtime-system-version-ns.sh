#!/usr/bin/env bash
set -euo pipefail
project=$1
shift
rootfs="$project/runtime/rootfs"
mount --make-rprivate /
mount --bind "$rootfs" "$rootfs"
# Validate optional account fixtures before entering the Linux rootfs.
account_database_relative=''
if [[ -n ${LINUXCODE_ACCOUNT_DATABASE:-} ]]; then
    account_database=$(realpath -e -- "$LINUXCODE_ACCOUNT_DATABASE")
    case "$account_database" in
        "$project"/runtime/*) ;;
        *) echo "Account database must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    for account_file in passwd master.passwd group; do
        [[ -f "$account_database/$account_file" && -f "$project/runtime/state/prefix/private/etc/$account_file" ]] || exit 2
    done
    account_database_relative=${account_database#"$project"/}
fi
# The selected original Xcode package can also live only in this invocation.
developer_overlay_relative=''
apple_overlay_relative=''
if [[ -n ${LINUXCODE_DEVELOPER_OVERLAY:-} ]]; then
    developer_overlay=$(realpath -e -- "$LINUXCODE_DEVELOPER_OVERLAY")
    case "$developer_overlay" in
        "$project"/runtime/*) ;;
        *) echo "Developer overlay must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -d "$developer_overlay" ]] || exit 2
    developer_overlay_relative=${developer_overlay#"$project"/}
fi
if [[ -n ${LINUXCODE_APPLE_OVERLAY:-} ]]; then
    apple_overlay=$(realpath -e -- "$LINUXCODE_APPLE_OVERLAY")
    case "$apple_overlay" in
        "$project"/runtime/*) ;;
        *) echo "Apple overlay must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -d "$apple_overlay" ]] || exit 2
    apple_overlay_relative=${apple_overlay#"$project"/}
fi
# An experimental metadata binding is visible only in this invocation.
system_version_relative=''
if [[ -n ${LINUXCODE_SYSTEM_VERSION:-} ]]; then
    system_version_path=$(realpath -e -- "$LINUXCODE_SYSTEM_VERSION")
    case "$system_version_path" in
        "$project"/runtime/*/darling-root/System/Library/CoreServices/SystemVersion.plist) ;;
        *) echo "SystemVersion must be in a private runtime variant" >&2; exit 2 ;;
    esac
    system_version_relative=${system_version_path#"$project"/}
fi
# A source-built server can be tested without replacing the package binary.
# This bind mount exists only in this invocation's private mount namespace.
if [[ -n ${LINUXCODE_DARLING_SERVER:-} ]]; then
    source_server=$(realpath -e -- "$LINUXCODE_DARLING_SERVER")
    case "$source_server" in
        "$project"/runtime/*) ;;
        *) echo "Source server must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_server" && -x "$source_server" ]] || exit 2
    mount --bind "$source_server" "$rootfs/usr/bin/darlingserver"
fi
if [[ -n ${LINUXCODE_LIBXPC:-} ]]; then
    source_libxpc=$(realpath -e -- "$LINUXCODE_LIBXPC")
    case "$source_libxpc" in
        "$project"/runtime/*) ;;
        *) echo "Source libxpc must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_libxpc" ]] || exit 2
    source_guest="$(dirname -- "$source_libxpc")/darling-root"
    cmp --silent -- "$source_libxpc" "$source_guest/usr/lib/system/libxpc.dylib" || {
        echo "Source libxpc directory variant is absent or stale; rebuild it first" >&2; exit 2;
    }
    mount --bind "$source_guest" "$rootfs/usr/libexec/darling"
fi
if [[ -n ${LINUXCODE_LAUNCHD:-} ]]; then
    source_launchd=$(realpath -e -- "$LINUXCODE_LAUNCHD")
    case "$source_launchd" in
        "$project"/runtime/*) ;;
        *) echo "Source launchd must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_launchd" && -x "$source_launchd" && -n ${LINUXCODE_LIBXPC:-} ]] || exit 2
    launchd_guest="$(dirname -- "$source_launchd")/darling-root"
    cmp --silent -- "$source_launchd" "$launchd_guest/sbin/launchd"
    cmp --silent -- "$source_libxpc" "$launchd_guest/usr/lib/system/libxpc.dylib"
    mount --bind "$launchd_guest" "$rootfs/usr/libexec/darling"
fi
if [[ -n ${LINUXCODE_LIBSYSTEM_KERNEL:-} ]]; then
    source_kernel=$(realpath -e -- "$LINUXCODE_LIBSYSTEM_KERNEL")
    case "$source_kernel" in
        "$project"/runtime/*) ;;
        *) echo "Source libsystem_kernel must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_kernel" && -n ${LINUXCODE_LIBXPC:-} && -n ${LINUXCODE_LAUNCHD:-} && -n ${LINUXCODE_DARLING_SERVER:-} ]] || exit 2
    kernel_guest="$(dirname -- "$source_kernel")/darling-root"
    cmp --silent -- "$source_kernel" "$kernel_guest/usr/lib/system/libsystem_kernel.dylib"
    cmp --silent -- "$source_libxpc" "$kernel_guest/usr/lib/system/libxpc.dylib"
    cmp --silent -- "$source_launchd" "$kernel_guest/sbin/launchd"
    mount --bind "$kernel_guest" "$rootfs/usr/libexec/darling"
fi
if [[ -n ${LINUXCODE_QUARANTINE:-} ]]; then
    source_quarantine=$(realpath -e -- "$LINUXCODE_QUARANTINE")
    case "$source_quarantine" in
        "$project"/runtime/*) ;;
        *) echo "Source quarantine must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_quarantine" && -n ${LINUXCODE_LIBSYSTEM_KERNEL:-} ]] || exit 2
    quarantine_guest="$(dirname -- "$source_quarantine")/darling-root"
    cmp --silent -- "$source_quarantine" "$quarantine_guest/usr/lib/system/libquarantine.dylib"
    cmp --silent -- "$source_kernel" "$quarantine_guest/usr/lib/system/libsystem_kernel.dylib"
    cmp --silent -- "$source_libxpc" "$quarantine_guest/usr/lib/system/libxpc.dylib"
    cmp --silent -- "$source_launchd" "$quarantine_guest/sbin/launchd"
    mount --bind "$quarantine_guest" "$rootfs/usr/libexec/darling"
fi
if [[ -n ${LINUXCODE_SANDBOX:-} ]]; then
    source_sandbox=$(realpath -e -- "$LINUXCODE_SANDBOX")
    case "$source_sandbox" in
        "$project"/runtime/*) ;;
        *) echo "Source sandbox must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_sandbox" && -n ${LINUXCODE_QUARANTINE:-} ]] || exit 2
    sandbox_guest="$(dirname -- "$source_sandbox")/darling-root"
    cmp --silent -- "$source_sandbox" "$sandbox_guest/usr/lib/system/libsystem_sandbox.dylib"
    cmp --silent -- "$source_quarantine" "$sandbox_guest/usr/lib/system/libquarantine.dylib"
    cmp --silent -- "$source_kernel" "$sandbox_guest/usr/lib/system/libsystem_kernel.dylib"
    cmp --silent -- "$source_libxpc" "$sandbox_guest/usr/lib/system/libxpc.dylib"
    cmp --silent -- "$source_launchd" "$sandbox_guest/sbin/launchd"
    mount --bind "$sandbox_guest" "$rootfs/usr/libexec/darling"
fi
if [[ -n ${LINUXCODE_LIBDYLD:-} ]]; then
    source_dyld=$(realpath -e -- "$LINUXCODE_LIBDYLD")
    case "$source_dyld" in
        "$project"/runtime/*) ;;
        *) echo "Source libdyld must be inside this project's runtime directory" >&2; exit 2 ;;
    esac
    [[ -f "$source_dyld" && -n ${LINUXCODE_SANDBOX:-} ]] || exit 2
    dyld_guest="$(dirname -- "$source_dyld")/darling-root"
    cmp --silent -- "$source_dyld" "$dyld_guest/usr/lib/system/libdyld.dylib"
    cmp --silent -- "$source_sandbox" "$dyld_guest/usr/lib/system/libsystem_sandbox.dylib"
    cmp --silent -- "$source_quarantine" "$dyld_guest/usr/lib/system/libquarantine.dylib"
    cmp --silent -- "$source_kernel" "$dyld_guest/usr/lib/system/libsystem_kernel.dylib"
    cmp --silent -- "$source_libxpc" "$dyld_guest/usr/lib/system/libxpc.dylib"
    cmp --silent -- "$source_launchd" "$dyld_guest/sbin/launchd"
    # The new API uses the matching ImageLoader C++ interface after asking
    # the real dyld2 registry to validate the handle. Select only this pinned
    # loader ABI, and reject prefix overlays that would replace either layer.
    python3 - "$project" "$dyld_guest" <<'PY'
from pathlib import Path
import hashlib,json,sys
r,variant=map(Path,sys.argv[1:]);config=json.loads((r/'config/libdyld-source-build.json').read_text())
for p in [variant/'usr/lib/dyld',r/'runtime/rootfs/usr/libexec/darling/usr/lib/dyld']:
    if hashlib.sha256(p.read_bytes()).hexdigest()!=config['packaged_loader_sha256']:
        raise SystemExit('Source libdyld requires the pinned Darling dyld2 loader ABI')
for relative in ['usr/lib/dyld','usr/lib/system/libdyld.dylib']:
    p=r/'runtime/state/prefix'/relative
    if p.exists() or p.is_symlink():raise SystemExit('Prefix overlay would override the selected source libdyld/loader')
PY
    mount --bind "$dyld_guest" "$rootfs/usr/libexec/darling"
fi
mount -t proc proc "$rootfs/proc"
mount -t tmpfs -o mode=755,nosuid tmpfs "$rootfs/dev"
mkdir -p "$rootfs/dev/pts" "$rootfs/dev/shm"
for device in null zero random urandom tty fuse; do
    if [[ -e /dev/$device ]]; then
        touch "$rootfs/dev/$device"
        mount --bind "/dev/$device" "$rootfs/dev/$device"
    fi
done
mount -t devpts -o newinstance,ptmxmode=0666,mode=620 devpts "$rootfs/dev/pts"
ln -s pts/ptmx "$rootfs/dev/ptmx"
ln -s /proc/self/fd "$rootfs/dev/fd"
ln -s /proc/self/fd/0 "$rootfs/dev/stdin"
ln -s /proc/self/fd/1 "$rootfs/dev/stdout"
ln -s /proc/self/fd/2 "$rootfs/dev/stderr"
mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs "$rootfs/dev/shm"
mount -t tmpfs -o mode=1777,nosuid,nodev tmpfs "$rootfs/tmp"
mount --bind "$project" "$rootfs/workspace"
mount --bind "$project/runtime/state" "$rootfs/state"
mount --bind "$project/runtime/home" "$rootfs/root"
mount -t binfmt_misc binfmt_misc "$rootfs/proc/sys/fs/binfmt_misc"
while IFS= read -r entry; do
    [[ -z $entry || $entry == \#* ]] && continue
    # The release's binfmt file refers to bin/mldr, while the package installs it here.
    entry=${entry//\/usr\/libexec\/darling\/bin\/mldr/\/usr\/libexec\/darling\/usr\/libexec\/darling\/mldr}
    printf '%s\n' "$entry" > "$rootfs/proc/sys/fs/binfmt_misc/register"
done < "$rootfs/usr/lib/binfmt.d/darling.conf"
mkdir -p "$rootfs/.oldroot"
/usr/sbin/pivot_root "$rootfs" "$rootfs/.oldroot"
cd /
umount --lazy /.oldroot
rmdir /.oldroot
cd /workspace
export DPREFIX=/state/prefix
if [[ -n ${account_database_relative:-} || -n ${developer_overlay_relative:-} || -n ${apple_overlay_relative:-} ]]; then
    # Overlayfs does not expose bind mounts placed on its upper-directory
    # backing files. Bootstrap first, then bind onto the live merged view in
    # darlingserver's mount namespace. Neither backing account file changes.
    /usr/bin/env -i HOME=/root USER=root LOGNAME=root \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        LANG=en_US.UTF-8 DPREFIX="$DPREFIX" /usr/bin/darling shell /usr/bin/true
    account_server_pid=$(cat /state/prefix/.init.pid)
    [[ $account_server_pid =~ ^[0-9]+$ && $(cat "/proc/$account_server_pid/comm") == darlingserver ]] || exit 2
    if [[ -n ${account_database_relative:-} ]]; then
        for account_file in passwd master.passwd group; do
            /usr/bin/nsenter --target "$account_server_pid" --mount \
                /usr/bin/mount --bind "/workspace/$account_database_relative/$account_file" "/state/prefix/private/etc/$account_file"
        done
    fi
    if [[ -n ${developer_overlay_relative:-} ]]; then
        /usr/bin/nsenter --target "$account_server_pid" --mount \
            /usr/bin/mount --bind "/workspace/$developer_overlay_relative" "/state/prefix/Library/Developer"
    fi
    if [[ -n ${apple_overlay_relative:-} ]]; then
        /usr/bin/nsenter --target "$account_server_pid" --mount \
            /usr/bin/mkdir -p /state/prefix/Library/Apple
        /usr/bin/nsenter --target "$account_server_pid" --mount \
            /usr/bin/mount --bind "/workspace/$apple_overlay_relative" "/state/prefix/Library/Apple"
    fi
fi
if [[ -n $system_version_relative ]]; then
    # The persistent prefix can shadow lower-directory metadata. Bind onto
    # the live overlay view, preserving both the upper file and default entry.
    /usr/bin/env -i HOME=/root USER=root LOGNAME=root \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        LANG=en_US.UTF-8 DPREFIX="$DPREFIX" /usr/bin/darling shell /usr/bin/true
    metadata_server_pid=$(cat /state/prefix/.init.pid)
    [[ $metadata_server_pid =~ ^[0-9]+$ && $(cat "/proc/$metadata_server_pid/comm") == darlingserver ]] || exit 2
    /usr/bin/nsenter --target "$metadata_server_pid" --mount \
        /usr/bin/mount --bind "/workspace/$system_version_relative" /state/prefix/System/Library/CoreServices/SystemVersion.plist
fi
if [[ ${1:-} == --linux ]]; then
    shift
    exec /usr/bin/env -i HOME=/root USER=root LOGNAME=root \
        PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
        LANG=C.UTF-8 \
        TERM="${TERM:-xterm}" DPREFIX="$DPREFIX" "$@"
fi
set +e
/usr/bin/env -i HOME=/root USER=root LOGNAME=root \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=en_US.UTF-8 \
    COCOAPODS_ALLOW_ROOT=1 COCOAPODS_DISABLE_STATS=true \
    TERM="${TERM:-xterm}" DPREFIX="$DPREFIX" /usr/bin/darling shell "$@"
result=$?
/usr/bin/env DPREFIX="$DPREFIX" /usr/bin/darling shutdown >/dev/null 2>&1
exit "$result"
