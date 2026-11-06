# index.json 非原子写 → bot 假告警(49→0→49)排查实录(2026-09-02)

## 现象
bot 日志出现:可拦截项目 49 → 0(🔵0/🟢0);审核通过 1 → 0,3 分钟后自动恢复 0 → 49。
用户视角 = 收到一条假告警推送。数据本身没丢。

## 根因
merger.py 直接 `json.dump(idx, open(INDEX,"w"), ...)` 写 7MB index.json。
`open(...,"w")` 先截断文件 → 写入瞬间(毫秒~几十 ms)文件为空/半写,
此时 bot 的菜单B监控(每 3 分钟 `all_projects()` 读 index.json)读到 0 项目 → total=0 → 推送"49→0"。

## 修复(3 处写入点全部原子化)
```python
# 原来:json.dump(idx, open(INDEX, "w"), ensure_ascii=False, indent=1)
_tmp = INDEX + ".tmp"
json.dump(idx, open(_tmp, "w"), ensure_ascii=False, indent=1)
os.replace(_tmp, INDEX)   # POSIX rename 原子替换
```
- build_index 内 2 处(INDEX 变量)+ 主合并流程 1 处(os.path.join(POOL,"index.json"))。
- 读取方永远看到完整的旧文件或完整的新文件,不再出现空/半文件窗口。

## 补丁陷阱(实际踩过)
字符串替换把单行 `json.dump(...)` 换成 3 行时,**try 块内缩进丢失** →
`json.dump` 行顶格 → `SyntaxError: expected 'except' or 'finally' block`。
修复:替换出的后续行必须补回 try 块缩进(4 空格),逐处核对:
```
    try:
        _tmp = INDEX + ".tmp"
        json.dump(...)      # ← 这行必须有 8 空格(函数内 4 + try 内 4)
        os.replace(...)
    except Exception:
```
主服 3 处全部替换后 `python3 -m py_compile` 验证 → SYNTAX_OK → 等下一轮 cron(每 3 分钟)自然加载,无需重启。

## 关联
与 09-01 心跳告警"并发写半文件 → merger JSON 解析失败"同源:
非原子写两种表现 = ①读者读到空/半文件(误报 0)②读者 JSON 解析失败(告警)。
**所有被多进程读写的落盘 JSON(health.json/index.json/gaps.json)统一 tmp+os.replace 原子写。**
验证原子写生效:ls 检查无 .tmp 残留 + 下一次 cron 运行日志正常。
