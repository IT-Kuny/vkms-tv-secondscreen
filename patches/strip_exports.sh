#!/bin/bash
# Strip all EXPORT_SYMBOL from monitorize-vkms source so it can coexist with stock vkms
set -e
cd /home/hx/Github/monitorize-vkms/src/vkms
for f in *.c; do
  grep -n "EXPORT_SYMBOL" "$f" | head -3 || true
done
# backup once
if [ ! -f /home/hx/Github/monitorize-vkms/.exports_stripped ]; then
  git -C /home/hx/Github/monitorize-vkms stash list | grep -q exportstrip || \
    git -C /home/hx/Github/monitorize-vkms stash push -m "exportstrip-backup" src/ || true
  touch /home/hx/Github/monitorize-vkms/.exports_stripped
fi
sed -i -E '/^[[:space:]]*EXPORT_SYMBOL(_GPL|_IF_KUNIT)?\(/d' *.c
echo "--- after ---"
grep -c "EXPORT_SYMBOL" *.c | grep -v ":0" || echo "all exports stripped"
