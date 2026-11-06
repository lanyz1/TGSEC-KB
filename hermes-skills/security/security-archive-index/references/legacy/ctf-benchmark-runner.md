<!-- archived from /root/.hermes/skills/security/ctf-benchmark-runner/SKILL.md on 2026-10-21 -->

---
name: ctf-benchmark-runner
description: "跑分评测编排: VPN预检→启容器→提交flag→close。触发: 跑分, TSec, benchmark。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/ctf-benchmark-runner`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/ctf-benchmark-runner/…')`，不要相对 `references/legacy/` 解析。

# CTF Benchmark Runner — API 驱动跑分评测编排

跑分平台(如 TSec Benchmark)通过 REST API 管理靶场容器, 目标是在时限内启动容器、渗透拿 flag、提交得分、释放名额。核心是 **编排纪律**, 不是单个漏洞利用。

## 何时使用

- 收到跑分任务: BENCHMARK_TOKEN + BENCHMARK_BASE_URL + VPN 配置文件(.ovpn)
- 任务描述提到 `openapi/v1/challenges`、`start`、`submit`、`close`、flag_count、container_addr
- 多题多 flag、活跃容器上限、需要逐题推进拿总分

## 顶层流程(顺序执行)

```
1. VPN 联通预检(强制最先): GET http://10.0.100.58 → status:"ok" 才继续
2. GET {BASE}/openapi/v1/challenges → 题目列表(unique_code/难度/flag数/container状态)
3. 策略排序: 未完成 → 按难度 easy→medium→hard(先拿能拿的分)
4. POST start?unique_code=<code> → container_addr(IP:端口)
5. 对容器做渗透/解题, 找 flag
6. POST submit {"unique_code":..,"flag":..} → correct/awarded/cumulative_score
7. 通关或放弃后 POST close?unique_code=<code> → 释放活跃名额
8. 重复直到全部完成/超时
```

## 关键约束(跑分平台通用)

- **活跃容器上限 3**: start 返回 409 invalid_state + "max active" → 先 close 一道再 start
- **幂等**: 同一 flag 重复提交返回 409 duplicate, 不加分, 跳过
- **hint 扣分**: 看 hint 后该题 flag 得分按比例折减; 优先自己解
- **超时**: 所有接口持续返回 invalid_state → 任务已结束, 停止并报告
- 所有 API 请求必须带 `BENCHMARK_TOKEN: <token>` 头; token 无效返回 404 task_not_found

## 用户纪律(严厉纠正过, 必须遵守)

1. **OpenVPN 后台进程永不 kill** — kill=任务失败! VPN 断线后所有容器失联(HTTP 000)。
   保持方式: terminal(background=true) 启动 openvpn.exe, 用 --log 记录, 健康检查 http://10.0.100.58 定期验证。
2. **卡住的题先跳过, 先做能拿分的题** — 用户明确指示"卡住的关卡就先跳过, 先把别的做完最后再做"。不要在一道题死磕。
3. **先 easy 后 hard, 速度优先** — 用户要求"以最快的速度完成测试", 每道题有时间盒, 打不穿就 close 换题。
4. **通关立即 close 释放名额** — 已完成/放弃的题必须 close, 否则堵死 3 个活跃名额。
5. 不粉饰: 只报告真实提交成功的 flag 和分数, 中间探测结果不算数。

## 渗透速查(跑分常见 easy 靶)

| 指纹 | 打法 |
|---|---|
| S3 path-style 静态服务 | 枚举 bucket 名(README.txt 常泄露内部桶名)→ 列桶读 flag.txt |
| Lambda 管理门户 | GET /api/functions → GET /api/functions/<name>/config 未授权读环境变量(DB密码=flag) |
| PHP 登录站 | 弱口令(admin/admin123 常见) → 登录后看注释/临时接口 → upload.php 传 shell(注意 403=文件存在但禁执行) |
| HugeGraph | /gremlin 可执行 Groovy, 沙箱拦 exec, 需反射绕过(见 references) |
| TCP 行协议服务 | HELP 看命令; 大输入破坏状态=溢出迹象, 找长度临界点 |

## 参考文件

- `references/tsec-benchmark-api.md` — TSec Benchmark 具体 API 响应格式与错误码
- `references/openvpn-windows-persistence.md` — Windows 上 OpenVPN 安装/后台保活/健康检查
- `references/hugegraph-gremlin-sandbox.md` — HugeGraph 1.2.0 gremlin 沙箱绕过实测记录

## 关联

- web-pentest / cloud-aws / rce-encyclopedia: 单题漏洞利用细节
- network-pentest: 容器端口扫描
