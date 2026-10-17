#!/usr/bin/env bash
set -euo pipefail
rootfs=$1
debs=$2
owner_uid=${3:?host owner UID required}
owner_gid=${4:?host owner GID required}
mount --make-rprivate /
mount -t proc proc "$rootfs/proc"
mount --rbind /dev "$rootfs/dev"
mount --make-rslave "$rootfs/dev"
mount --bind "$debs" "$rootfs/packages"
cp /etc/resolv.conf "$rootfs/etc/resolv.conf"
chmod 1777 "$rootfs/tmp" "$rootfs/var/tmp"
cat > "$rootfs/usr/sbin/policy-rc.d" <<'EOF'
#!/bin/sh
exit 101
EOF
chmod 755 "$rootfs/usr/sbin/policy-rc.d"
chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/bash -s <<'EOF'
set -euo pipefail
apt-get update
apt-get install -y --no-install-recommends ca-certificates procps util-linux \
  /packages/darling-core_*.deb \
  /packages/darling-system_*.deb \
  /packages/darling-cli_*.deb \
  /packages/darling-cli-gui-common_*.deb \
  /packages/darling-cli-python2-common_*.deb \
  /packages/darling-cli-devenv-gui-common_*.deb \
  /packages/darling-cli-devenv-gui-stubs-common_*.deb \
  /packages/darling-ffi_*.deb \
  /packages/darling-python2_*.deb \
  /packages/darling-ruby_*.deb \
  /packages/darling-perl_*.deb \
  /packages/darling-iosurface_*.deb
apt-get install -y --no-install-recommends \
  /packages/darling-gui_*.deb /packages/darling-gui-stubs_*.deb /packages/darling-iokitd_*.deb
apt-get clean
EOF
# The launcher runs as namespace root; host setuid/setgid binaries are unnecessary.
find "$rootfs" -xdev -type f -perm /6000 -exec chmod a-s {} +
find "$rootfs" -xdev -exec chown -h "$owner_uid:$owner_gid" {} +
