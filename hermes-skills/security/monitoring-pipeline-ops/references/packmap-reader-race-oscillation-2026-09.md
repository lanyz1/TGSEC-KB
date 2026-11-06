# pack_map.json 读者-写者竞态 → 菜单B「审核通过 23→21→23→21」抖动实录(2026-09-03)

## 现象
菜单B监控(每 3 分钟)推送数值横跳:审核通过 23→21、21→23、23→21 反复循环,
另伴随 `[菜单B监控异常] too many values to unpack (expected 2)` 每轮死循环。
用户视角:bot 收到一串互相矛盾的变化推送。

## 根因(两层)

### 1. 非原子写 → 读者整实体归零(抖动主因)
- 写者:**orch8b.py(cron 5/35 分,8 台并行回填)** 与 merger.py,直接
  `json.dump(pmd, open(pmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)`
  → `open("w")` 先截断再逐块写,indent=1 的大文件写入窗口秒级
- 读者:bot `check_status_summary()` json.load 撞上截断 → 异常 → `except: pass`
  → **该项目的 pack_map 整条静默归零**(贡献的 2 个"审核通过"全丢)→ st_pass 23→21
- orch8b 写完 → 恢复 23 → 交替推送 = 抖动
- 关键隐蔽点:json.load 失败的项目**不进 detail 快照** → 与 prev_detail 比无逐项 diff
  → 只推"审核通过 23→21"总量、无项目明细 → 看起来像真实数据变化

### 2. 监控 diff 解包 bug → 真实变化每轮死循环炸
```python
diffs.append((pid, op, (p2, r2)))     # 三元组
for pid, (op0, cu0) in diffs[:4]:     # 二元解包 → ValueError: too many values to unpack
```
- 炸点在 `prev_detail = dict(detail)`(循环尾)之前 → prev_detail 永不更新
  → 每轮都与旧快照比 → 每轮都炸 → 死循环 + 真实审核变化静默丢失
- 纯总量变化轮(实体进出集合,detail 无"双方都在且值变"项目)不炸、照常推送 → 迷惑性强
- 日志只打 `str(e)[:60]` 无行号 → 静态审代码+文件 mtime 对账都定位不到 → 上 traceback 才见分晓

## 修复
1. **全部写点原子化**(orch8b 1 处 + merger 2 处):
   ```python
   _tmp = pmp + ".tmp"
   with open(_tmp, "w", encoding="utf-8") as _f:
       json.dump(pmd, _f, ensure_ascii=False, indent=1)
   os.replace(_tmp, pmp)   # 原子替换
   ```
   读者端不用改。找全写点:`grep -n 'json.dump(.*open(.*"w"'` 各文件。
2. **unpack 修复**:`for pid, op0, cu0 in diffs[:4]:`(三元解三元)。
3. **异常打印带行号**(排查期):`traceback.format_exc().splitlines()[-2]`。

## 补丁灾难(本次实录,教训价值高)
把单行 json.dump 替换成多行原子写,**字符串缩进全乱**:
- `s.replace(old, new)` 保留被匹配行的行首缩进;new 首行 0 空格 → 替换后首行仍带锚点缩进,
  new 内部各行按字面缩进 → 内部行错位(16 vs 8 空格)→ `IndentationError: unexpected indent`
- 按记忆中的坏段重打补丁 → 叠出双 try/双 except(第一处补丁已坏,第二次基于坏文件再补)
- 修复纪律:① 每次远程补丁后立即 `python3 -m py_compile`(stderr 要读,不能只读 stdout);
  ② 报错后用 `cat -A` 或带行号输出看**实际内容**;③ 一次用整段特征正则重写坏区,不再小步猜

## 验证
- 原子写修复后**等下一轮 orch8b cron(5/35 分)自然用新代码**,看 bot 监控 3-4 轮(3min/轮)
  日志:不再出现抖动推送 + 不再每轮异常
- 修后若出现单次大跳(如 21→26)= 真实数据变化(原子写后写者不再产生半文件),非抖动

## 关联
- 同源案例:index.json 非原子写 → bot 假告警 49→0→49(`index-json-atomic-write.md`,2026-09-02)
- 通用规则:所有被多进程读写的落盘 JSON 一律 tmp+os.replace;监控/汇总的推送计数抖动,
  先查"谁在非原子写读者读的文件",别查数据源
