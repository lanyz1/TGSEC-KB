# -*- coding: utf-8 -*-
"""目录整理骨架 —— 复制后按目标目录改 DIR / KEEP / JUNK / GOALS 即可。

用法:
    python organize_dir.py --dry     # 只打印分类预览(给用户确认)
    python organize_dir.py --go      # 真正执行(移动 + 日志 + 索引)

设计要点(别改坏):
  * KEEP 优先于一切:命中即原地不动(快捷方式/运行依赖/启动器组/凭据)
  * 分类按「项目/目标」聚合,不按扩展名散开
  * 每一步写日志,结束后项数对账
  * 目标同名改名 _dup2,绝不覆盖
"""
import os, sys, shutil, datetime, fnmatch

sys.stdout.reconfigure(encoding='utf-8')          # Windows 中文输出必须

DIR = r"C:\Users\<user>\Desktop"                  # ← 要整理的目录
LOG = "_整理日志.txt"
INDEX = "_索引.md"

# ---- 配置区 ----------------------------------------------------------------
KEEP = {
    'desktop.ini',
    # 快捷方式(全部保留): 判断见 classify() 里的 .lnk 规则,不用逐个列
    # 运行依赖 / 启动器组 / 凭据 / 交接文档,例如:
    # '某客户端目录', '启动某工具.bat', '某工具_ui.py', '凭据单_机密.txt', 'soul.md',
}
JUNK = {                                          # → _待清理(不直接删)
    # '空文件.txt', '~$cache1', '__pycache__',
}
GOALS = [                                         # 目标关键词 → 01_<目标>\
    # ('项目A', ['项目A关键词1', '关键词2']),
    # ('项目B', ['B', 'b-']),
]

JUNK_DIR = '_待清理'
DATA_EXT  = {'.csv', '.xlsx', '.xls', '.jsonl', '.json', '.db', '.tar', '.gz'}
TOOL_EXT  = {'.py', '.bat', '.cmd', '.ps1', '.cs'}
PKG_EXT   = {'.zip', '.rar', '.7z', '.exe', '.msi', '.apk'}
MEDIA_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.mp3', '.wav'}
BIG_DIRS  = ()                                    # GB 级数据目录名前缀 → 02_数据导出
# ---------------------------------------------------------------------------


def classify(name, isdir):
    """返回分类子目录名,或 None 表示原地保留。"""
    ext = os.path.splitext(name)[1].lower()
    if name in KEEP or name.lower().endswith('.lnk') or name == 'desktop.ini':
        return None
    if name in JUNK or fnmatch.fnmatch(name, '~$*') or name == '__pycache__':
        return JUNK_DIR
    if isdir and BIG_DIRS and name.startswith(tuple(BIG_DIRS)):
        return '02_数据导出'
    for goal, kws in GOALS:                       # 目标关键词优先于扩展名
        if any(k in name for k in kws):
            return os.path.join('01_报告', goal)
    if ext in TOOL_EXT:
        return '03_工具与脚本'
    if ext in PKG_EXT:
        return '04_交付包'
    if ext in MEDIA_EXT:
        return '05_素材'
    if ext in DATA_EXT:
        return '02_数据导出'
    return None if isdir else '99_未归类'


def size_of(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs)


def tree(d, depth, maxdepth, out):
    if depth > maxdepth:
        return
    for n in sorted(os.listdir(d)):
        p = os.path.join(d, n)
        if os.path.isdir(p):
            cnt = sum(len(f) for _, _, f in os.walk(p))
            out.append('  ' * depth + '- **%s/** (%d 文件)' % (n, cnt))
            tree(p, depth + 1, maxdepth, out)
        else:
            out.append('  ' * depth + '- %s (%d B)' % (n, os.path.getsize(p)))


def main(go):
    items = sorted(os.listdir(DIR))
    plan, keep = {}, []
    for n in items:
        t = classify(n, os.path.isdir(os.path.join(DIR, n)))
        if t is None:
            keep.append(n)
        else:
            plan.setdefault(t, []).append(n)

    print('目录共 %d 项;待归档 %d 项,保留顶层 %d 项\n' % (len(items), sum(len(v) for v in plan.values()), len(keep)))
    for t in sorted(plan):
        print('[%s]  %d 项  %.1f MB' % (t, len(plan[t]),
              sum(size_of(os.path.join(DIR, n)) for n in plan[t]) / 1048576))
        for n in plan[t]:
            print('      ' + n)
    print('\n保留顶层:', keep)
    if not go:
        print('\n(--dry 模式,未做任何改动)')
        return

    log = []
    ok = fail = 0
    for t in sorted(plan):
        dst = os.path.join(DIR, t)
        os.makedirs(dst, exist_ok=True)
        for n in plan[t]:
            s, d = os.path.join(DIR, n), os.path.join(dst, n)
            try:
                if os.path.exists(d):                 # 同名不覆盖
                    base, e = os.path.splitext(n)
                    k = 2
                    while os.path.exists(d):
                        d = os.path.join(dst, '%s_dup%d%s' % (base, k, e)); k += 1
                shutil.move(s, d)
                log.append('OK   %s -> %s' % (n, t)); ok += 1
            except Exception as ex:                  # WinError 5 见 SKILL.md 步骤 5
                log.append('FAIL %s : %s' % (n, ex)); fail += 1

    open(os.path.join(DIR, LOG), 'w', encoding='utf-8').write(
        '===== %s =====\n' % datetime.datetime.now() + '\n'.join(log) + '\n')

    idx = ['# 目录索引', '> 生成: %s ｜ Ctrl+F 搜文件名' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '']
    for d in sorted(os.listdir(DIR)):
        p = os.path.join(DIR, d)
        if os.path.isdir(p) and d not in ('新v2包',):
            idx.append('\n### ' + d + '/')
            o = []; tree(p, 0, 2, o); idx += o[:500]
    open(os.path.join(DIR, INDEX), 'w', encoding='utf-8').write('\n'.join(idx))

    print('=== 完成: 成功 %d / 失败 %d ===' % (ok, fail))
    print('日志: %s   索引: %s' % (LOG, INDEX))
    print('对账: 整理前 %d == 移走 %d + 保留 %d + 新增 2 == %d' % (
        len(items), ok, len(keep), ok + len(keep) + 2))


if __name__ == '__main__':
    main('--go' in sys.argv)
