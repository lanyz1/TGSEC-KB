# TRX Hash Racing 监控面板：未授权读写（2026-09-20）

指纹：标题「TRX Hash Racing」；Python `BaseHTTP`；内联 HTML+JS 调 `/api/*`。

## 合约
| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| GET | `/api/state` | 无 | status/latest/history/opening/pending/alert + 证据文件名 |
| GET | `/api/settings` | 无 | `configured,site_hint,account_hint,proxy_configured`（密码不明文） |
| POST | `/api/settings` | 无 | body: `game_url,account,password,proxy` |
| POST | `/api/pending/remove` | 无 | 需 `period` |
| POST | `/api/draw-alert/dismiss` | 无 | 需 `period` |
| GET | `/evidence/{name}` | 无 | `*.opening.json` / `*.pre.json` / `*.result.json` |

## settings 字段与校验
- 前端：`#gameUrl #gameUser #gamePassword #gameProxy` → POST JSON 上述四键。
- 缺键 → `请填写有效网址、账号和密码`。
- `game_url` 必须**包含子串 `_nc`**，否则 `游戏平台网址必须包含 _nc 参数`。
- **不要用探测账号覆盖生产配置**；用缺字段/非法 URL 证形状即可。若必须证写入，先备份 `GET /api/settings` 快照并征得用户同意。

## evidence 批量
1. 从 `/api/state` walk 所有 `*.json` 文件名。
2. `GET /evidence/{quote(name)}` 全量下；`result.json` 可 1MB+（含整块 TRON block/tx）。
3. 通常**无 session cookie**；`balance` 等来自链上/平台 JSON，不是面板登录态。
4. settings 的 `site_hint`（如 `mem3.….com`）= 下一跳博彩/开奖平台。

## 报告要点
写清：未授权读 state/settings、未授权写 settings 形状、evidence 数量与目录；账号只给 hint 脱敏。
