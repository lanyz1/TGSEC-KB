#!/usr/bin/env python3
"""Verify Hermes model-alias registration + resolution without needing a TTY.

`hermes model` requires an interactive terminal, so this probe drives the same
resolve_alias() path directly. Run it from the Hermes install dir so the venv
site-packages are importable:

    cd /usr/local/lib/hermes-agent
    python3 scripts/verify_model_alias.py

Prints every registered DIRECT_ALIAS (and confirms base_url + key suffix) plus
resolve_alias() output for each manually-listed alias.
"""
import os
import sys
import logging

# Make hermes_cli importable (install dir + its venv site-packages).
HERMES_DIR = "/usr/local/lib/hermes-agent"
for p in (HERMES_DIR, f"{HERMES_DIR}/venv/lib/python3.11/site-packages"):
    if p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

logging.disable(logging.CRITICAL)

os.environ.setdefault("HERMES_HOME", os.path.expanduser("~/.hermes"))

from hermes_cli.model_switch import (
    resolve_alias,
    _ensure_direct_aliases,
    DIRECT_ALIASES,
)

# The default provider name used when a switch is issued from a session on this
# provider. Change if you want to test resolution from a different anchor.
CURRENT_PROVIDER = "custom:kugua"

ALIASES_TO_CHECK = [
    "glm-5.3",
    "glm-5.3-flash",
    "zuz8-sol",
    "zuz8-gpt5",
    "zuz8-terra",
]


def mask(key: str) -> str:
    if not key:
        return "(none)"
    return f"{key[:6]}...{key[-4:]}"


def main() -> int:
    _ensure_direct_aliases()

    print("=== DIRECT_ALIASES (registered model aliases) ===")
    for name in sorted(DIRECT_ALIASES):
        da = DIRECT_ALIASES[name]
        print(
            f"  {name}: model={da.model} provider={da.provider} "
            f"base={da.base_url} key={mask(da.api_key)}"
        )

    print(f"\n=== resolve_alias (anchor provider: {CURRENT_PROVIDER}) ===")
    ok = True
    for name in ALIASES_TO_CHECK:
        try:
            result = resolve_alias(name, CURRENT_PROVIDER)
        except Exception as exc:  # noqa: BLE001 - report the failure, don't crash
            print(f"  {name} -> ERROR {type(exc).__name__}: {exc}")
            ok = False
            continue
        if result is None:
            print(f"  {name} -> NOT RESOLVED (alias not registered under current provider)")
            ok = False
            continue
        provider, model, key = result
        da = DIRECT_ALIASES.get(name)
        bound = f"base={da.base_url} key={mask(da.api_key)}" if da else "(no direct alias)"
        print(f"  {name} -> provider={provider} model={model} alias={key}  [{bound}]")

    print("\nResult:", "ALL OK" if ok else "CHECK FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
