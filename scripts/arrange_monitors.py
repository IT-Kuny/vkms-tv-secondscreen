#!/usr/bin/env python3
"""Arrange eDP-1 + Virtual-4 as extended desktop — GNOME 49 (connector, mode) spec."""
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
V = GLib.Variant

bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
    "org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig",
    "org.gnome.Mutter.DisplayConfig", None)
res = proxy.call_sync("GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None)
serial = res[0]

current_mode = {}
for mon in res[1]:
    conn = mon[0][0]
    for mode in mon[1]:
        props = mode[6]
        if props.get("is-current") or any(True for _ in [1] for k, v in props.items() if k == "is-current" and v.get_boolean()):
            current_mode[conn] = mode[0]
    if conn not in current_mode and mon[1]:
        current_mode[conn] = mon[1][0][0]  # fallback: first/preferred mode
print("modes:", {k: v for k, v in current_mode.items() if k in ("eDP-1", "Virtual-4")})
assert "eDP-1" in current_mode and "Virtual-4" in current_mode

empty_dict = V.new_array(GLib.VariantType("{sv}"), [])

def logical(x, y, primary, conn):
    m = V.new_tuple(V.new_string(conn), V.new_string(current_mode[conn]), empty_dict)
    arr = V.new_array(GLib.VariantType("(ssa{sv})"), [m])
    return V.new_tuple(V.new_int32(x), V.new_int32(y), V.new_double(1.0),
                       V.new_uint32(0), V.new_boolean(primary), arr)

logicals = V.new_array(GLib.VariantType("(iiduba(ssa{sv}))"),
    [logical(0, 0, True, "eDP-1"), logical(1920, 0, False, "Virtual-4")])
props = V.new_array(GLib.VariantType("{sv}"), [])
params = V.new_tuple(V.new_uint32(serial), V.new_uint32(1), logicals, props)
proxy.call_sync("ApplyMonitorsConfig", params, Gio.DBusCallFlags.NONE, -1, None)
print("APPLIED OK")
