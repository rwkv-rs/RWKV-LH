#!/bin/sh
set -eu
profile=/etc/apparmor.d/rwkv-lh-bwrap
if [ -e "$profile" ]; then
 echo 'Refusing to overwrite existing profile' >&2
 exit 1
fi
journalctl -k -n 300 --no-pager | grep -E 'apparmor=.*(bwrap|unprivileged_userns)' | tail -12 || true
cat > "$profile" <<'EOF'
abi <abi/4.0>,
include <tunables/global>
profile rwkv-lh-bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
}
EOF
chmod 644 "$profile"
/usr/sbin/apparmor_parser -a "$profile"
sha256sum "$profile"
