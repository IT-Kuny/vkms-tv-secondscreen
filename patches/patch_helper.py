#!/usr/bin/env python3
"""Patch monitorize helper to use renamed configfs dir (coexistence with stock vkms)."""
p = "/usr/lib/monitorize-vkms/monitorize_vkms/helper.py"
s = open(p).read()
a1 = '(mount / "vkms").is_dir()'
a2 = 'instance = root / "vkms" / INSTANCE_NAMES["primary"]'
assert a1 in s, "anchor1 missing"
assert a2 in s, "anchor2 missing"
s = s.replace(a1, '(mount / "monitorize_vkms").is_dir()', 1)
s = s.replace(a2, 'instance = root / "monitorize_vkms" / INSTANCE_NAMES["primary"]', 1)
open(p, "w").write(s)
print("helper patched")
