# vkms-tv-secondscreen

A real **extended desktop on any TV** — a virtual second monitor on GNOME Wayland,
streamed to an Android TV via RustDesk. No cables, no reboot, no dummy plug.

Built and battle-tested on **Fedora 43 / GNOME 49 / kernel 7.1.10** (AMD Ryzen AI
9 HX 370 / Radeon 890M), client: Sony BRAVIA TL (Android TV 11) running RustDesk
(flutter_hbb) 1.4.9.

## How this project came to be

It started with a simple question on a Saturday morning:

> *"Can I cast my desktop from my laptop to the TV?"*

**Act 1 — everything that refuses to work.**
The Sony TV (a 2022 model, never updated — the Play Store is blocked at the
router) turned out to have a broken Cast receiver: its `mediashell` 1.56 (from
2022, frozen) accepts only "insecure" connections, resets every TLS handshake on
port 8009 and rejects plaintext CastV2 frames as "invalid messages". mDNS
multicast turned out to be completely dead on the WLAN (Broadcom wl on the AP —
60 seconds of sniffing at the radio: zero mDNS frames). Chromecast: dead end.

**Act 2 — the rescue.**
RustDesk over a direct LAN connection (flutter_hbb on the TV as client,
direct-IP to the laptop) worked beautifully — including controlling the laptop
with the TV remote, no accessibility service needed. But that only mirrored the
primary screen. The actual goal was a **second desktop**.

**Act 3 — "impossible", then GitHub.**
Stock `vkms` (the kernel's virtual display driver) creates a connector, but
GNOME/mutter refuses any monitor without an EDID — and mainline vkms has no EDID
support at all. Verdict: impossible on GNOME Wayland without a hardware dummy
plug.

Wrong. A GitHub search later:
[monitorize-vkms](https://github.com/vinnavannewton/monitorize-vkms) — an
out-of-tree vkms **with dynamic EDID generation** (carrying the pending upstream
EDID patchset). But it collides with the stock vkms module (duplicate exported
symbols, clashing configfs directory). So it got patched live, no reboot:

- ✂️ stripped all `EXPORT_SYMBOL`s → both modules coexist
- 🔧 renamed the configfs directory → no EBUSY
- 🐍 patched the Python CLI + both polkit helper paths

The virtual monitor appeared — and then GNOME 49's `ApplyMonitorsConfig` D-Bus
API had to be reverse-engineered (spoiler: the monitor spec is
`(connector, mode-id)` — two strings, the second is the mode ID), RustDesk had
to be forced onto the Wayland/portal capture path (`RUSTDESK_FORCED_DISPLAY_SERVER=wayland`)
so the client gets a real per-monitor switch, and a stale portal restore token
had to be deleted so the screen-share dialog would grant **both** monitors.

**Result:** a 1920x1080 virtual monitor, extended desktop, monitoring dashboard
glowing on 55", laptop screen untouched — zero reboots, zero cables, in one
morning.

Moral of the story: before declaring something impossible with high confidence
— search GitHub harder.

## What's in this repo

| Path | Purpose |
|---|---|
| `patches/strip-exports.sh` | Removes all `EXPORT_SYMBOL*` so the module coexists with stock `vkms` |
| `patches/patch_helper.py` | Retargets `/usr/lib/monitorize-vkms/.../helper.py` to the renamed configfs dir |
| `patches/patch_helper2.py` | Same for `/usr/libexec/monitorize-vkms/monitorize-vkms-helper` |
| `scripts/arrange_monitors.py` | Arranges eDP + virtual display as extended desktop (GNOME 49 DisplayConfig D-Bus) |
| `deploy/rustdesk-wayland.conf` | systemd drop-in forcing RustDesk onto Wayland/portal capture |

## Deploy chain

```sh
# 1. Prereqs (Fedora)
sudo dnf install -y dkms git gcc make
test -f "/lib/modules/$(uname -r)/build/Makefile"   # kernel headers

# 2. Clone + patch + install
git clone https://github.com/vinnavannewton/monitorize-vkms.git
cd monitorize-vkms
bash <this-repo>/patches/strip-exports.sh          # against src/vkms/*.c
# rename configfs dir: vkms_configfs.c '.ci_name = "vkms"' -> "monitorize_vkms"
# retarget paths in cli.py + scripts/monitorize-vkms-bootstrap.sh (see patches/)
sudo ./install.sh

# 3. Force a rebuild after patching (install.sh skips if version unchanged)
sudo dkms remove monitorize-vkms/<ver> --all
sudo dkms install monitorize-vkms/<ver>

# 4. Load + create the virtual display
sudo systemctl start monitorize-vkms-bootstrap.service
sudo monitorize-vkms create 1920x1080@60

# 5. Arrange as extended desktop (GNOME 49 DisplayConfig D-Bus)
python3 scripts/arrange_monitors.py   # eDP at (0,0), virtual at (1920,0)

# 6. RustDesk: force Wayland/portal capture (per-monitor switch!)
sudo cp deploy/rustdesk-wayland.conf /etc/systemd/system/rustdesk.service.d/wayland.conf
sudo systemctl daemon-reload && sudo systemctl restart rustdesk

# 7. If the portal restores an old monitor selection:
sed -i '/wayland-restore-token/d' ~/.config/rustdesk/RustDesk_local.toml
sudo systemctl restart rustdesk
# -> next connection pops the GNOME screen-share dialog: select BOTH monitors
```

Then on the RustDesk client (TV): session toolbar → TV/monitor icon → switch to
display **2**. Enjoy.

## Gotchas discovered the hard way

- **GNOME 49 `ApplyMonitorsConfig` monitor spec is `(connector, mode-id, props)`**
  — two strings, the second being the mode ID (`"1920x1080@59.963"`) from
  `GetCurrentState`. Send a serial instead and mutter answers
  `Invalid mode specified`. See `scripts/arrange_monitors.py` (GLib Variant
  constructors — the GVariant text parser cannot express empty `a{sv}` values
  inside literals).
- **RustDesk without the wayland override captures via Xwayland** — one combined
  X screen, no per-monitor selection on the client. With the portal path each
  monitor becomes a switchable display.
- **The portal restore token** (`~/.config/rustdesk/RustDesk_local.toml`)
  restores whatever monitor selection was granted when it was created. Delete it
  whenever your monitor topology changes.
- **Helper patches must be re-applied after every `install.sh` rerun** — the
  installer restages the Python helpers from the repo.
- Stock `vkms` cannot be unloaded live once fbcon grabbed its framebuffer —
  hence the coexistence patches instead of "just rmmod".
- **flutter_hbb on Android TV:** `adb shell input text` garbles in Flutter
  dialogs (OSD keyboard interference) — type passwords as
  `input keyevent KEYCODE_T ...` sequences, or use the
  `rustdesk://connection/new/<ip>` deep link to skip typing entirely.

## Credits

- [monitorize-vkms](https://github.com/vinnavannewton/monitorize-vkms) by
  vinnavannewton (GPL-2.0) — the EDID-enabled vkms that makes all of this work.
- Upstream vkms kernel developers and the pending vkms EDID patchset authors.

## License

GPL-2.0 (kernel-module derivative). Patches and scripts in this repo may be
reused under the same terms.
