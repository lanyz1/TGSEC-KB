#!/usr/bin/env python3
"""Extract NiceGUI initial UI structure from a saved page HTML.

NiceGUI (2.x) renders the initial UI inside the page as:
    parseElements(String.raw`{...json...}`)

The JSON is a dict of element nodes keyed by numeric string IDs. Children are
ID references (numeric strings), NOT nested objects — walk by ID lookup.

Usage:
    python3 extract_nicegui_ui.py <saved_page.html>

Output: one line per text node / labeled input / button, indented by depth.
"""
import json
import re
import sys


def main(path: str) -> int:
    html = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"parseElements\(String\.raw\`(\{.*?\})\`\)", html, re.DOTALL)
    if not m:
        print("NO parseElements FOUND (page may be a rejection page or not NiceGUI)")
        return 1
    data = json.loads(m.group(1))
    out: list[str] = []

    def walk(nid, depth: int = 0) -> None:
        node = data.get(str(nid))
        if not node:
            return
        text = node.get("text", "")
        if text and str(text).strip():
            out.append("  " * depth + "TEXT: " + str(text))
        props = node.get("props", {})
        extras = []
        for key in ("placeholder", "label", "hint", "name", "icon", "type"):
            if props.get(key):
                extras.append(f"{key}={props[key]}")
        if extras:
            out.append("  " * depth + f'<{node.get("tag", "")}> ' + " ".join(extras))
        for child in node.get("children", []):
            if isinstance(child, (int, str)):
                walk(child, depth + 1)

    walk("0")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
