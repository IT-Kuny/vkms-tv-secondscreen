#!/usr/bin/env python3
"""tvd — TV virtual display daemon (skeleton, E3)

Unix-socket JSON API + monitorize-vkms lifecycle + Mutter D-Bus layout.
Runs as a systemd USER service (needs the GNOME session bus).

Protocol (one JSON object per line):
  {"cmd":"create"}              -> virtual display + extended layout
  {"cmd":"create","w":2560,"h":1440,"rr":60}
  {"cmd":"remove"}              -> remove display + restore primary-only layout
  {"cmd":"status"}              -> connector + layout state
Replies: {"ok":true,...} / {"ok":false,"error":"..."}
"""
import json, os, socket, subprocess, sys, threading

from layout import Layout

SOCK = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"), "tvd.sock")
DEFAULT_MODE = (1920, 1080, 60)

state = {"display": False, "connector": None}
lock = threading.Lock()


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {p.stderr.strip() or p.stdout.strip()}")
    return p.stdout.strip()


def connector_name() -> str:
    out = run(["monitorize-vkms", "status"])
    for line in out.splitlines():
        if line.strip().startswith("Connector"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError(f"no connector in status output:\n{out}")


def do_create(w: int, h: int, rr: int) -> dict:
    run(["monitorize-vkms", "create", f"{w}x{h}@{rr}"])
    conn = connector_name()
    Layout.extend(conn, w)
    state.update(display=True, connector=conn)
    return {"connector": conn, "mode": f"{w}x{h}@{rr}"}


def do_remove() -> dict:
    conn = state.get("connector")
    Layout.restore()
    if conn:
        run(["monitorize-vkms", "remove"])
    state.update(display=False, connector=None)
    return {"removed": conn}


def handle(req: dict) -> dict:
    cmd = req.get("cmd")
    if cmd == "create":
        w = int(req.get("w", DEFAULT_MODE[0])); h = int(req.get("h", DEFAULT_MODE[1])); rr = int(req.get("rr", DEFAULT_MODE[2]))
        return do_create(w, h, rr)
    if cmd == "remove":
        return do_remove()
    if cmd == "status":
        return {"display": state["display"], "connector": state["connector"]}
    return {"ok": False, "error": f"unknown cmd: {cmd!r}"}


def client(conn: socket.socket):
    with conn:
        try:
            data = conn.makefile("r").readline()
            if not data:
                return
            req = json.loads(data)
            with lock:
                res = handle(req)
                res.setdefault("ok", True)
        except Exception as e:
            res = {"ok": False, "error": str(e)}
        conn.sendall(json.dumps(res).encode() + b"\n")


def main():
    if os.path.exists(SOCK):
        os.unlink(SOCK)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    os.chmod(SOCK, 0o660)
    srv.listen(8)
    print(f"tvd listening on {SOCK}", file=sys.stderr)
    while True:
        client(srv.accept()[0])


if __name__ == "__main__":
    main()
