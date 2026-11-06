#!/usr/bin/env python3
"""Compat entry: hall crypto -> local crypto_decode.py."""
import os
import sys
from pathlib import Path

target = Path(__file__).with_name("crypto_decode.py")
os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
