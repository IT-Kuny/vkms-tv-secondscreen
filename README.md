# vkms-tv-secondscreen

A real **extended desktop on any TV** — a virtual second monitor on GNOME Wayland,
streamed to an Android TV via RustDesk. No cables, no reboot, no dummy plug.

Built and battle-tested on **Fedora 43 / GNOME 49 / kernel 7.1.10** (AMD iGPU),
client: Sony BRAVIA (Android TV 11) running RustDesk (flutter_hbb) 1.4.9.

## Why this exists

- GNOME/mutter refuses virtual monitors without an EDID — and mainline vkms has
  **no EDID support**. So a "virtual second screen" on Wayland is normally
  impossible without a hardware dummy plug.
- [monitorize-vkms](https://github.com/vinnavannewton/monitorize-vkms) ships an
  out-of-tree vkms **with dynamic EDID generation** — but it collides with the
  stock `vkms` module if that one is (or ever was) loaded.

This repo contains the coexistence patches + the complete deploy chain.

## The three patches (why)

1. **`strip-exports.sh`** — removes all `EXPORT_SYMBOL*` from the module source.
   The stock `vkms` module owns symbols like `apply_3x4_matrix`; loading a second
   module exporting the same names is refused by the kernel
   (`Exec format error` → dmesg: "exports duplicate symbol"). A standalone driver
   doesn't need its exports — stripping them lets both modules coexist.
2. **configfs rename** — the module registers the configfs directory `vkms/`,
   which clashes with the stock module's directory (`Device or resource busy`).
   Rename `.ci_name` in `vkms_configfs.c` to `monitorize_vkms` and adjust all
   paths in the Python CLI / polkit helper (see `patch_helper*.py`).
3. **Helper paths** — two helpers carry the configfs path:
   `/usr/lib/monitorize-vkms/monitorize_vkms/helper.py` AND
   `/usr/libexec/monitorize-vkms/monitorize-vkms-helper`. Both must be patched —
   and re-patched after every rerun of `install.sh`.

## Deploy chain

```sh
# 1. Prereqs (Fedora)
sudo dnf install -y dkms git gcc make
test -f "/lib/modules/$(uname -r)/build/Makefile"   # kernel headers

# 2. Clone + patch + install
git clone https://github.com/vinnavannewton/monitorize-vkms.git
cd monitorize-vkms
bash patches/strip-exports.sh   # from THIS repo, run against the clone's src/vkms/
# sed the configfs rename + cli.py/bootstrap paths (see patches/)
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
sudo systemctl edit rustdesk   # → see deploy/rustdesk-wayland.conf
sudo systemctl restart rustdesk

# 7. If the portal restores an old monitor selection:
sed -i '/wayland-restore-token/d' ~/.config/rustdesk/RustDesk_local.toml
sudo systemctl restart rustdesk
# → next connection pops the GNOME screen-share dialog: select BOTH monitors
```

Then on the RustDesk client (TV): session toolbar → TV/monitor icon → switch to
display **2**. Enjoy.

## Gotchas discovered the hard way

- **GNOME 49 `ApplyMonitorsConfig` monitor spec is `(connector, mode-id, props)`**
  — two strings, the second being the mode ID (`"1920x1080@59.963"`) from
  `GetCurrentState`. Send a serial and mutter answers `Invalid mode specified`.
  See `scripts/arrange_monitors.py` (GLib Variant constructors — the GVariant
  text parser cannot express empty `a{sv}` values inside literals).
- **RustDesk without the wayland override captures via Xwayland** — one combined
  X screen, no per-monitor selection on the client. With
  `RUSTDESK_FORCED_DISPLAY_SERVER=wayland` it uses the portal/PipeWire path.
- **The portal restore token** (`~/.config/rustdesk/RustDesk_local.toml`)
  restores whatever monitor selection was granted when it was created. Delete it
  whenever your monitor topology changes.
- Stock `vkms` can't be unloaded live once fbcon grabbed its framebuffer — hence
  the coexistence patches instead of "just rmmod".

## Credits

- [monitorize-vkms](https://github.com/vinnavannewton/monitorize-vkms) by
  vinnavannewton (GPL-2.0) — the EDID-enabled vkms that makes all of this work.
- Upstream vkms kernel developers; the pending vkms EDID patchset authors.

## License

GPL-2.0 (kernel-module derivative). Patches and scripts in this repo may be
reused under the same terms.
