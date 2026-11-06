# 远程批量跑的"完成"判定 + 生成器脚本的 4 个必炸点

**触发**: 用跳板机/多机分片跑批量任务(扫站/收割/补跑), 需要判断"这一片到底跑没跑完"。

## 1. 核心教训: 输出文件 0 字节 ≠ 没跑完

**2026-09 实测代价**: 一趟 6 机分片扫描(58 目标), 跑到中途 `ls` 看到 `shaoxing.out` **0 字节**,
判定该片"托死", 于是**重跑了一遍切片**, 并在**已交付的报告里写"该片未出结果, 靠补跑救回"**。
跑完回头一看: `shaoxing.out` 最终 **3,266 字节 / 9 目标有效 JSON** —— **它一直是正常的**。
0 字节只是流式回传工具(`rex2.py` 之类)**运行中途不落盘**造成的假象。

**双重代价**: ① 白跑一轮(浪费配额, 还可能触发目标 WAF 限流);
② **交付物里出现错误声明, 被迫发勘误**——用户对"报告说错"的容忍度远低于"没打到"。

## 2. 正确的完成判定(三条同时看, 不看文件尺寸)

```
① 父进程/子进程退出码   (timeout 的 124 = 真超时, 这个可信)
② 每片的最终产物标记     (如 @@JSON@@ 且能 json.loads 出非空列表)
③ 覆盖断言: 合并全部片 -> 去重 -> 与目标清单逐条比对
```

覆盖断言脚本模式(必写, 不要"目测齐了"):

```python
targets = {l.split("\t")[0].strip() for l in open(TARGETS_FILE, encoding="utf-8") if l.strip()}
got = set()
for f in sorted(glob.glob(WORKERS + "/*.out")):
    raw = open(f, encoding="utf-8", errors="replace").read()
    if "@@JSON@@" not in raw:
        print("[无JSON] %s (%d bytes)" % (os.path.basename(f), len(raw))); continue
    for line in raw.split("@@JSON@@", 1)[1].splitlines():
        line = line.strip()
        if line.startswith("["):
            try:
                got |= {r["domain"] for r in json.loads(line)}; break
            except Exception:
                continue
print("targets=%d covered=%d 未覆盖=%s" % (len(targets), len(got & targets), sorted(targets - got)))
```

**逐片计数也要打出来**(`文件名 / 字节 / N 目标`)—— 一眼看出哪片少给了目标, 比总数字节数有用得多。

## 3. 生成器脚本(把目标清单内联进远端单文件)的 4 个必炸点

远端单文件上传工具只能传一个文件, 所以常用"生成器 + 内联列表"模式。这类脚本的坑每次都一样:

| # | 坑 | 症状 | 防法 |
|---|---|---|---|
| 1 | **`import sys` 漏了** | 本地 `ast.parse` **通过**, 远端一跑就 `NameError: name 'sys' is not defined`(只在用 `sys.argv` 的行炸) | 生成后**在本地真的执行一次** `python gen.py --dry` 或跑通一个 1 目标的切片; 光语法检查不够 |
| 2 | **模板里 `%` 格式化打架** | 脚本模板本身含 `%`(URL 拼接 `%s://%s/`), 用 `%` 注入列表 → `not enough arguments for format string` | **用占位符替换** `TPL.replace("__TARGETS__", json.dumps(...))`, 模板内所有 `%` 保持原样(不要再手工转义成 `%%`) |
| 3 | **输入文件是富记录不是纯列表** | 目标清单是 `域名\t分类\t标题\tIP` 的 TSV, 直接当域名用 → 全部"不可达" | 一律 `l.split("\t")[0].strip()` 取第一列, 并加 `"." in d` 兜底过滤 |
| 4 | **写脚本被静默截断** | 工具回报 `bytes_written` 远小于预期(如 262), 脚本尾部丢失 → `SyntaxError: unterminated string literal` | 写完立刻 `ast.parse` + `wc -c` 复核; 长脚本**分片写或追加**; 内容过长就拆成两个文件 |

## 4. 分片补跑的正确做法

- 某片真失败时, **换一台机补同一 slice**(不要重跑全部)——同 IP 出口不等于同结果
- 补跑**双机冗余**(两台跑同一 slice)比单机重试更稳: 结果按 domain 去重即可, 重复无害
- 补跑**仍要进覆盖断言**, 否则"补了但没算进总数"这种错误无法发现

## 5. 与报告纪律的衔接

- 报告里写"X 站全部完成"是**硬声明**, 必须由覆盖断言支撑, 不能由"我发了 N 个分片"推断
- 发现自己先前说法不准时: **改报告 + 保留原文划掉 + 加勘误段**, 不要静默改数字
  (实测: 两处都被用户侧通知"抓"到, 主动发勘误比被点出来代价小得多)
