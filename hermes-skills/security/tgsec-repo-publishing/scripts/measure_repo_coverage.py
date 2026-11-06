#!/usr/bin/env python3
"""量「本机安装库 vs 仓库」的蒸馏覆盖率：同名交集 / 仅本地 / 名字在仓正文出现过 / legacy 覆盖。

用法: python3 measure_repo_coverage.py <repo_dir> [skills_dir]
输出: JSON（stdout），四个核心数：same_name / installed_only / only_mentioned / legacy_mentioned

口径：卡名取 frontmatter 的 name:，无则用目录名。`mentioned` 只代表名字在仓正文出现过
（常是 eval_core.json / docs/updates 的路径引用），不代表内容被蒸馏——报数时别混。
"""
import os, re, sys, glob, json, subprocess, tempfile

repo = sys.argv[1]
sk = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/.hermes/skills')


def name_of(p):
    try:
        head = open(p, encoding='utf-8', errors='replace').read(1500)
    except OSError:
        return None
    m = re.search(r"^name:\s*['\"]?([\w.\-]+)", head, re.M)
    return m.group(1) if m else os.path.basename(os.path.dirname(p))


def collect(root, pattern):
    d = {}
    for p in glob.iglob(os.path.join(root, pattern), recursive=True):
        if os.path.isfile(p):
            n = name_of(p)
            if n:
                d.setdefault(n, p)
    return d


inst = collect(sk, '**/SKILL.md')
dom = collect(repo, 'domains/**/SKILL.md')
umb = collect(repo, '.claude/skills/**/SKILL.md')
repo_names = set(dom) | set(umb)
only = sorted(set(inst) - repo_names)
legacy = [p for p in glob.iglob(os.path.join(sk, '**/references/legacy/*.md'), recursive=True) if os.path.isfile(p)]
legacy_names = sorted({name_of(p) or os.path.basename(p)[:-3] for p in legacy})


def mentioned(names):
    if not names:
        return 0
    fd, path = tempfile.mkstemp(suffix='.txt')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write('\n'.join(names) + '\n')
        r = subprocess.run(['grep', '-rhoF', '-f', path, '--include=*.md', '--include=*.json',
                            '--include=*.yaml', '.'], cwd=repo, capture_output=True, text=True, errors='replace')
        return len({x.strip() for x in r.stdout.splitlines() if x.strip()})
    finally:
        os.unlink(path)


n_inst, n_repo = len(inst), len(repo_names)
print(json.dumps({
    'installed': n_inst,
    'repo_domains': len(dom),
    'repo_umbrella': len(umb),
    'repo_names_total': n_repo,
    'same_name': len(set(inst) & repo_names),
    'same_name_pct': round(100.0 * len(set(inst) & repo_names) / n_inst, 2) if n_inst else 0,
    'installed_only': len(only),
    'installed_only_pct': round(100.0 * len(only) / n_inst, 2) if n_inst else 0,
    'installed_only_mentioned': mentioned(only),
    'legacy_files': len(legacy),
    'legacy_mentioned': mentioned(legacy_names),
}, ensure_ascii=False, indent=1))
