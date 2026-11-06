#!/usr/bin/env python3
"""Linux Privilege Escalation Assistant"""
import subprocess, os, sys, pwd

CHECKS = {
    "sudo": "sudo -l 2>/dev/null",
    "suid": "find / -perm -4000 -type f 2>/dev/null",
    "writable_etc": "find /etc -writable -type f 2>/dev/null",
    "cron_jobs": "cat /etc/crontab 2>/dev/null;ls -la /etc/cron.* 2>/dev/null",
    "capabilities": "getcap -r / 2>/dev/null",
    "docker_group": "groups | grep docker",
    "unmounted": "cat /etc/fstab 2>/dev/null;mount",
    "kernel": "uname -a;cat /proc/version",
    "services": "systemctl list-units --type=service --state=running 2>/dev/null",
    "network": "ss -tlnp 2>/dev/null;netstat -tlnp 2>/dev/null",
    "env_vars": "env | grep -i pass;env | grep -i token;env | grep -i key",
    "history": "cat ~/.bash_history 2>/dev/null;history 2>/dev/null",
    "ssh_keys": "find / -name id_rsa -o -name id_ed25519 2>/dev/null",
    "passwd": "cat /etc/passwd;cat /etc/shadow 2>/dev/null",
}

EXPLOITS = {
    "dirty_cow": "CVE-2016-5195 — gcc -pthread dirty.c -o dirty -lcrypt",
    "overlayfs": "CVE-2015-1328 — Ubuntu 12.04-15.04",
    "pkexec": "CVE-2021-4034 — PwnKit: pkexec privilege escalation",
    "sudo_baron": "CVE-2021-3156 — Sudo Baron Samedit",
    "polkit": "CVE-2021-3560 — Polkit authentication bypass",
    "dirty_pipe": "CVE-2022-0847 — Linux kernel 5.8+",
}

def run_check(name: str, cmd: str):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
    if r.stdout.strip():
        print(f"\n[+] {name}:")
        print(r.stdout[:500])
    if r.stderr.strip():
        print(f"[-] {name}: {r.stderr[:100]}")

def suggest_exploit():
    kernel = subprocess.run("uname -r", shell=True, capture_output=True, text=True).stdout.strip()
    print(f"\n[*] Kernel: {kernel}")
    for name, desc in EXPLOITS.items():
        print(f"    {name}: {desc}")

if __name__ == "__main__":
    print("[*] Linux Privilege Escalation Scanner")
    for name, cmd in CHECKS.items():
        run_check(name, cmd)
    suggest_exploit()
