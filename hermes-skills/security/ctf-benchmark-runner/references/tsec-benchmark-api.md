# TSec Benchmark API 参考(实测 2026-08)

BASE: `https://tsecbench.zc.tencent.com`(公网可达), 所有请求带 `BENCHMARK_TOKEN: <token>` 头。
靶场容器在 VPN 网段 10.0.x.x, 需先连 OpenVPN。

## 接口

### GET /openapi/v1/challenges
返回数组, 每项:
```json
{"unique_code":"d-01","description":"...","difficulty":"easy|medium|hard",
 "level":1,"total_score":200,"flag_count":1,"correct_flag_count":0,
 "is_completed":false,"container_status":"stopped","container_addr":[]}
```
- 63 题: easy 9 (100-200分) / medium 25 (200-500分) / hard 29 (250-1800分)
- b-01/b-02/b-03 是多 flag 题(4-6 个 flag, 总分 1200-1800)

### POST /openapi/v1/challenges/start?unique_code=<code>
返回 `{"unique_code":"d-01","container_addr":["10.0.187.8:8000"]}`
- 409 invalid_state "max active challenge instances reached (3)" → 先 close 一题

### POST /openapi/v1/challenges/submit
Body: `{"unique_code":"d-01","flag":"flag{...}"}`
返回: `{"correct":true,"awarded":200,"cumulative_score":200,"correct_flag_count":1,"total_flag_count":1,"matched_flag_index":0}`
- 重复提交已正确 flag → 409 duplicate

### POST /openapi/v1/challenges/close?unique_code=<code>
返回 `{"unique_code":"d-01","closed":true}`

### GET /openapi/v1/challenges/hint?unique_code=<code>
看 hint 后该题 flag 得分按 hint_cost_radio 扣减。通关后不能再看(409)。

## 错误码

- 404 task_not_found: token 无效/缺失 → 停止报告
- 404 challenge_not_found: unique_code 拼写错 → 跳过
- 409 invalid_state: (a)任务超时结束 (b)活跃达上限 (c)通关后看 hint
- 409 duplicate: flag 已提交过 → 跳过
- 503 resource_unavailable: 可短暂重试 start
- 500 internal_error: 重试一次

## flag 格式
`flag{uuid}` 形如 `flag{55dad451-c7ca-43ba-8623-e6da386b3135}`

## 实战提交命令
```bash
BASE="https://tsecbench.zc.tencent.com"; TOKEN="<token>"
curl -s -H "BENCHMARK_TOKEN: $TOKEN" "$BASE/openapi/v1/challenges" -o /tmp/ch.json
curl -s -X POST -H "BENCHMARK_TOKEN: $TOKEN" "$BASE/openapi/v1/challenges/start?unique_code=d-01"
curl -s -X POST -H "BENCHMARK_TOKEN: $TOKEN" -H "Content-Type: application/json" \
  -d '{"unique_code":"d-01","flag":"flag{xxx}"}' "$BASE/openapi/v1/challenges/submit"
curl -s -X POST -H "BENCHMARK_TOKEN: $TOKEN" "$BASE/openapi/v1/challenges/close?unique_code=d-01"
```
