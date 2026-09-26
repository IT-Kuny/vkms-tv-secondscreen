#!/usr/bin/env python3
"""Patch the libexec monitorize helper (renamed configfs dir)."""
import sys
p = "/usr/libexec/monitorize-vkms/monitorize-vkms-helper"
s = open(p).read()
a1 = '(mount / "vkms").is_dir()'
a2 = 'instance = root / "vkms" / INSTANCE_NAMES["primary"]'
assert a1 in s, "anchor1 missing"
assert a2 in s, "anchor2 missing"
s = s.replace(a1, '(mount / "monitorize_vkms").is_dir()', 1)
s = s.replace(a2, 'instance = root / "monitorize_vkms" / INSTANCE_NAMES["primary"]', 1)
open(p, "w").write(s)
print("libexec helper patched")
