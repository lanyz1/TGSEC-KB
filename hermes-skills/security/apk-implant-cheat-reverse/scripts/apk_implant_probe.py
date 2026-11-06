#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""APK 内置外挂 / so 替换式植入探针（纯 stdlib，无需 readelf/objdump/NDK）

用法:
  python3 apk_implant_probe.py apk  --path target.apk [--analyze-so]
  python3 apk_implant_probe.py so   --path libztgame.so [--dump-dex outdir]
  python3 apk_implant_probe.py file --path libztgame.so     # 只扫隐藏 dex / 字符串
产物: 时间线（植入判据）/ 导出导入画像 / 真身字符串 / 内嵌 dex 切片
"""
import argparse, os, re, struct, sys, zipfile

DEX_MAGICS = [b"dex\n035\x00", b"dex\n036\x00", b"dex\n037\x00",
              b"dex\n038\x00", b"dex\n039\x00"]
FAKE_SDK_EXPORTS = ("AceProvideJavaVmV1", "AceProvide", "GameGuard",
                    "EasyAntiCheat", "GameGuardian")
HOOK_API = {"dlopen", "dlsym", "dl_iterate_phdr", "android_dlopen_ext",
            "mprotect", "memcpy", "mmap", "mremap", "syscall"}
ANTIDBG_API = {"ptrace", "sigaction", "fork", "waitpid", "getppid",
               "prctl", "raise", "kill"}
JLANG_RE = re.compile(rb"[\x20-\x7e]{1,60}?\.(?:java|kt|cpp|cc|c|h|hpp|cs)\x00")
CFGKEY_RE = re.compile(rb"(POINTER_[A-Z0-9_]{2,20}|aim[A-Za-z]{3,14}|shootTouch[XY]|"
                       rb"action\d{1,2}Touch[XY]|POLL_MS|aimRadius)\x00")
STR_RE = re.compile(rb"[\x20-\x7e]{5,}")


def elf_parse(data):
    """返回 section 列表（含 link/entsize/name）；非 ELF 返回 None"""
    if data[:4] != b"\x7fELF":
        return None
    is64 = data[4] == 2
    en = "<" if data[5] == 1 else ">"
    if is64:
        shoff = struct.unpack_from(en + "Q", data, 0x28)[0]
        shentsize, shnum, shstrndx = struct.unpack_from(en + "HHH", data, 0x3A)
    else:
        shoff = struct.unpack_from(en + "I", data, 0x20)[0]
        shentsize, shnum, shstrndx = struct.unpack_from(en + "HHH", data, 0x2E)
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        if shentsize == 0 or o + shentsize > len(data):
            break
        name, typ = struct.unpack_from(en + "II", data, o)
        if is64:
            _fl, _addr, soff, size = struct.unpack_from(en + "QQQQ", data, o + 8)
            link = struct.unpack_from(en + "I", data, o + 40)[0]
            entsize = struct.unpack_from(en + "Q", data, o + 56)[0]
        else:
            _fl, _addr, soff, size = struct.unpack_from(en + "IIII", data, o + 8)
            link = struct.unpack_from(en + "I", data, o + 24)[0]
            entsize = struct.unpack_from(en + "I", data, o + 36)[0]
        secs.append(dict(idx=i, name_off=name, type=typ, offset=soff,
                         size=size, link=link, entsize=entsize))
    shstr = b""
    if 0 <= shstrndx < len(secs):
        t = secs[shstrndx]
        shstr = data[t["offset"]:t["offset"] + t["size"]]
    for sec in secs:
        n = sec["name_off"]
        end = shstr.find(b"\x00", n) if n < len(shstr) else -1
        sec["name"] = shstr[n:end].decode("latin1") if end > n else ""
    return dict(is64=is64, endian=en, secs=secs)


def elf_symbols(data, info):
    """动态符号表 → exports / imports（import 判据: st_shndx==SHN_UNDEF）"""
    out = {"exports": [], "imports": []}
    if not info:
        return out
    esz = 24 if info["is64"] else 16
    for sec in info["secs"]:
        if sec["type"] not in (2, 11):          # SYMTAB=2 DYNSYM=11
            continue
        strtab = b""
        if 0 <= sec["link"] < len(info["secs"]):
            t = info["secs"][sec["link"]]
            strtab = data[t["offset"]:t["offset"] + t["size"]]
        step = sec["entsize"] or esz
        for o in range(sec["offset"], sec["offset"] + sec["size"], step):
            if o + esz > len(data):
                break
            n = struct.unpack_from("<I", data, o)[0]
            ib = data[o + 4] if info["is64"] else data[o + 12]
            shndx = struct.unpack_from("<H", data, o + (6 if info["is64"] else 14))[0]
            if n == 0 or n >= len(strtab):
                continue
            end = strtab.find(b"\x00", n)
            nm = strtab[n:end if end > n else len(strtab)].decode("latin1")
            bind, styp = ib >> 4, ib & 0xF
            if shndx == 0:
                out["imports"].append(nm)
            elif bind in (1, 2) and styp in (1, 2):
                out["exports"].append(nm)
    for k in out:
        out[k] = sorted(set(out[k]))
    return out


def dex_scan(data, name, dump_dir=None):
    """扫 so 内嵌 dex: magic 定位 + header.file_size 切片（真实提取，不是报个数）"""
    hits = set()
    for magic in DEX_MAGICS:
        pos = 0
        while True:
            pos = data.find(magic, pos)
            if pos < 0:
                break
            hits.add(pos)
            pos += 4
    outs = []
    for pos in sorted(hits):
        rem = len(data) - pos
        size = (struct.unpack_from("<I", data, pos + 0x20)[0]
                if pos + 0x24 <= len(data) else 0)
        note = ""
        ok = 0x70 <= size <= rem
        if not ok and rem >= 0x70:
            # 壳/加密常把 file_size 改掉 → 按剩余字节截断仍然提，标注出来
            note = " 声明size越界→按剩余%d字节截断" % rem
            size, ok = rem, True
        rec = "off=0x%x size=%d %s%s" % (pos, size, "OK" if ok else "不可提报", note)
        if ok and dump_dir:
            os.makedirs(dump_dir, exist_ok=True)
            p = os.path.join(dump_dir, "%s_0x%x.dex" % (
                os.path.basename(name).replace(".so", ""), pos))
            with open(p, "wb") as f:
                f.write(data[pos:pos + size])
            rec += " -> " + p
        outs.append(rec)
    return outs


def java_hints(data):
    srcs = set(m.rstrip(b"\x00").decode("latin1") for m in JLANG_RE.findall(data))
    clss = set(m.decode("latin1") for m in
               re.findall(rb"L(?:com|cn|net|org|io)/[A-Za-z0-9_/$]{3,80};", data))
    keys = set(m.rstrip(b"\x00").decode("latin1") for m in CFGKEY_RE.findall(data))
    return sorted(srcs), sorted(clss)[:200], sorted(keys)


def so_report(data, name, dump_dir=None):
    info = elf_parse(data)
    lines = ["== %s (%d bytes) %s ==" % (name, len(data),
             ("ELF%d" % (64 if info["is64"] else 32)) if info else "非ELF/节区不可解析")]
    if info:
        lines.append("节区: " + ", ".join(s["name"] for s in info["secs"] if s["name"])[:400])
    syms = elf_symbols(data, info)
    exp, imp = syms["exports"], syms["imports"]
    lines.append("导出 %d: %s" % (len(exp), ", ".join(exp[:40]) or "-"))
    lines.append("导入 %d: %s" % (len(imp), ", ".join(imp[:40]) or "-"))
    fake = [e for e in exp if any(k.lower() in e.lower() for k in FAKE_SDK_EXPORTS)]
    if fake:
        lines.append("[!] 伪装导出名候选: %s  → 核对是否替换了原 SDK 同名 so" % ", ".join(fake))
    cap = sorted(i for i in imp if i.lstrip("_") in HOOK_API)
    anti = sorted(i for i in imp if i.lstrip("_") in ANTIDBG_API)
    if cap:
        lines.append("[!] hook/加载能力: %s" % ", ".join(cap))
    if anti:
        lines.append("[!] 反调试面: %s" % ", ".join(anti))
    srcs, clss, keys = java_hints(data)
    if srcs:
        lines.append("[!] 源文件残留(真身线索): %s" % ", ".join(srcs[:20]))
    if clss:
        lines.append("[!] Java 类线索 %d: %s" % (len(clss), ", ".join(clss[:20])))
    if keys:
        lines.append("[!] 配置键 %d: %s" % (len(keys), ", ".join(keys[:30])))
    dz = dex_scan(data, name, dump_dir)
    if dz:
        lines.append("[!] 内嵌 dex: %s" % " | ".join(dz))
    return "\n".join(lines)


def apk_report(path, analyze_so=False, dump_dir=None):
    z = zipfile.ZipFile(path)
    infos = z.infolist()

    def dt(i):
        t = i.date_time
        return "%04d-%02d-%02d %02d:%02d" % (t[0], t[1], t[2], t[3], t[4])

    sos = [i for i in infos if i.filename.endswith(".so")]
    dexs = [i for i in infos if re.match(r"classes\d*\.dex$", i.filename)]
    sigs = [i for i in infos if i.filename.startswith("META-INF/")]
    lines = ["== %s ==" % os.path.basename(path),
             "条目 %d | so %d | dex %d | 签名条目 %d" % (len(infos), len(sos), len(dexs), len(sigs))]
    if dexs:
        lines.append("classes*.dex: " + ", ".join(i.filename for i in dexs))
    lines.append("--- 签名条目时间（重打包时刻）---")
    for i in sigs[:12]:
        lines.append("  %s  %s" % (dt(i), i.filename))
    lines.append("--- lib/*.so 时间线（升序，末尾=最新=植入候选）---")
    for i in sorted(sos, key=lambda x: x.date_time):
        lines.append("  %s  %10d  %s" % (dt(i), i.file_size, i.filename))
    lines.append("--- assets/ 内附属载荷（.so/.dex/.jar/.zip/.dat）---")
    for i in infos:
        if i.filename.startswith("assets/") and re.search(
                r"\.(so|dex|jar|zip|apk|dat)$", i.filename):
            lines.append("  %s  %10d  %s" % (dt(i), i.file_size, i.filename))
    if analyze_so:
        for i in sos:
            lines.append("")
            lines.append(so_report(z.read(i.filename), i.filename, dump_dir))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["apk", "so", "file"])
    ap.add_argument("--path", required=True)
    ap.add_argument("--analyze-so", action="store_true")
    ap.add_argument("--dump-dex", default=None)
    a = ap.parse_args()
    with open(a.path, "rb") as f:
        data = f.read()
    if a.mode == "apk":
        print(apk_report(a.path, a.analyze_so, a.dump_dex))
    else:
        print(so_report(data, os.path.basename(a.path), a.dump_dex))


if __name__ == "__main__":
    main()
