#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split an archive into <=48MB parts and push them via `hermes send`.
Telegram bot API hard-caps ~50MB/file; 48MiB parts validated in the field.

Usage:  python send_parts_via_hermes_send.py <archive> <chat-target> [part-size-MB]
        chat-target like 'telegram:8263338802'
Runs long -> launch via terminal(background=true, notify=true).
Sends a final manifest message (concat cmds + md5 + part count).
"""
import os, sys, subprocess, time, hashlib, glob


def log(msg, path):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(path, "a") as f:
        f.write(line + "\n")


def main():
    arch = os.path.abspath(sys.argv[1])
    chat = sys.argv[2]
    mb = sys.argv[3] if len(sys.argv) > 3 else "48"
    parts_dir = os.path.join(os.path.dirname(arch), "send_parts")
    logf = arch + ".send.log"
    os.makedirs(parts_dir, exist_ok=True)
    for f in glob.glob(f"{parts_dir}/*"):
        os.remove(f)

    md5 = hashlib.md5(open(arch, "rb").read()).hexdigest()
    subprocess.run(
        f"split -b {mb}M -d --additional-suffix=.part {arch} {parts_dir}/dump_part-",
        shell=True, check=True)
    parts = sorted(glob.glob(f"{parts_dir}/dump_part-*"))
    base = os.path.basename(arch)
    log(f"{base}: {os.path.getsize(arch)}b -> {len(parts)} parts, md5={md5}", logf)

    ok = 0
    for i, p in enumerate(parts, 1):
        sent = False
        for att in range(3):
            r = subprocess.run(f'hermes send --to {chat} --json "MEDIA:{p}"',
                               shell=True, capture_output=True, text=True, timeout=900)
            if '"success": true' in r.stdout:
                sent = True
                break
            log(f"part {i}/{len(parts)} att{att+1} fail: {r.stdout[:120]}", logf)
            time.sleep(15)
        ok += int(sent)
        log(f"part {i}/{len(parts)} {'sent' if sent else 'GAVE UP'} ({os.path.getsize(p)}b)", logf)
        time.sleep(4)

    manifest = (f"{base} 发送完成 {ok}/{len(parts)} 片 | "
                f"合并(Windows): copy /b dump_part-*.part full.tar.zst | "
                f"(Mac/Linux): cat dump_part-*.part > full.tar.zst | "
                f"解压: 7-Zip 解两次 or tar --zstd -xf full.tar.zst | MD5: {md5}")
    subprocess.run(f'hermes send --to {chat} "{manifest}"', shell=True,
                   capture_output=True, text=True, timeout=120)
    log("manifest sent. DONE", logf)


if __name__ == "__main__":
    main()
