#!/usr/bin/env python3
"""Mutter DisplayConfig layout — generalized from arrange6.py (2026-09-26 PoC).

GNOME 49 spec: Logical-Monitor-Spec = a(iiduba(ssa{sv}))
Monitor = (connector, MODE-ID-STRING, props) — mode ID like "1920x1080@59.963"
from GetCurrentState, NOT vendor/serial.
"""
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

V = GLib.Variant


class Layout:
    def __init__(self):
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.proxy = Gio.DBusProxy.new_sync(bus, Gio.DBusProxyFlags.NONE, None,
            "org.gnome.Mutter.DisplayConfig", "/org/gnome/Mutter/DisplayConfig",
            "org.gnome.Mutter.DisplayConfig", None)

    def _state(self):
        res = self.proxy.call_sync("GetCurrentState", None, Gio.DBusCallFlags.NONE, -1, None)
        serial, monitors = res[0], res[1]
        primary, modes = None, {}
        for mon in monitors:
            conn = mon[0][0]
            for mode in mon[1]:
                props = mode[6]
                try:
                    is_cur = bool(props.get("is-current")) if hasattr(props, "get") else False
                except Exception:
                    is_cur = False
                if is_cur and conn not in modes:
                    modes[conn] = mode[0]
            if conn not in modes and mon[1]:
                modes[conn] = mon[1][0][0]
            if conn.startswith(("eDP", "LVDS")):
                primary = conn
        return serial, primary, modes

    def _logical(self, x, y, primary, conn, mode, scale=1.0):
        m = V.new_tuple(V.new_string(conn), V.new_string(mode), V.new_array(VariantType_empty, []))
        arr = V.new_array(GLib.VariantType("(ssa{sv})"), [m])
        return V.new_tuple(V.new_int32(x), V.new_int32(y), V.new_double(scale),
                           V.new_uint32(0), V.new_boolean(primary), arr)

    def _apply(self, serial, logicals):
        props = V.new_array(GLib.VariantType("{sv}"), [])
        params = V.new_tuple(V.new_uint32(serial), V.new_uint32(1), logicals, props)
        self.proxy.call_sync("ApplyMonitorsConfig", params, Gio.DBusCallFlags.NONE, -1, None)

    def extend(self, virt_conn: str, virt_w: int):
        """Primary on (0,0), virtual monitor right of it."""
        serial, primary, modes = self._state()
        if not primary:
            primary = sorted(modes)[0]
        logicals = V.new_array(GLib.VariantType("(iiduba(ssa{sv}))"), [
            self._logical(0, 0, True, primary, modes[primary]),
            self._logical(virt_w, 0, False, virt_conn, modes[virt_conn]),
        ])
        self._apply(serial, logicals)

    def restore(self):
        """Primary only."""
        serial, primary, modes = self._state()
        if not primary:
            primary = sorted(modes)[0]
        logicals = V.new_array(GLib.VariantType("(iiduba(ssa{sv}))"), [
            self._logical(0, 0, True, primary, modes[primary]),
        ])
        self._apply(serial, logicals)


VariantType_empty = GLib.VariantType("{sv}")
