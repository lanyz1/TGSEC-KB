# 案例课：15 分钟锁窗下的密码预言机与 2-shot 预算

> 来源：报告包 zgycpd（2026-10）· 域：auth-security

## 一句话

登录口 `{username,password,code?}` 有 15 分钟锁，但错误文案分三级：错密 / 缺 OTP / 锁死。只要看到 `invalid authenticator code` 就说明**密码已经对了**，立刻停喷转 OTP 面。

## 三级 oracle

| 响应 | 含义 |
|---|---|
| `invalid username or password` | 账号或密码错 |
| `invalid authenticator code` | **密码正确**，缺/错 OTP |
| `too many login attempts; try again in 15 minutes` | 已锁 |

## 预算

- 报告实测：后台 A 用 `2-shot / 每 16min 2 发`；后台 B 写「每窗口 ~8 次即封」→ **阈值因后台而异**
- 首轮先 **1 发** 探针，读冷却文案确认阈值，再定 2 或 8
- 冷却 ≥16min；单线 oneshot，禁 site_dict/twin/多探针叠喷
- `gate_unlocked()` 这类「错密探针」本身也算一次，必须删
- 记录 WINDOW 去重数，重复密码不占预算
- 按账号锁时换 Tor 无用；先确认锁维度

## 边界

- 报告另见「无限速」的登录体（另一应用），别把锁窗当全家桶
- 密码 HIT 后没有 OTP 种子就停，不要继续喷
- Origin 头必须精确匹配（尾斜杠/缺失 → `invalid origin`），否则全是假失败

## 检查清单

- [ ] 三种错误文案
- [ ] 锁维度（账号/IP）
- [ ] 单发探针确认阈值
- [ ] HIT 落 ADMIN_PWD_OK
- [ ] 转 OTP/种子面

---
@TGSEC社区 · @TGSEC-Qtzuu 整理
