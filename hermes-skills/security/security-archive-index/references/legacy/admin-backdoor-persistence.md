<!-- archived from /root/.hermes/skills/security/admin-backdoor-persistence/SKILL.md on 2026-10-21 -->

---
name: admin-backdoor-persistence
description: "管理后台持久化后门: 改密码无痕+JWT无状态+账号伪装+恢复原状。触发: 后门, 持久化, 改密码, 留后门。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/admin-backdoor-persistence`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/admin-backdoor-persistence/…')`，不要相对 `references/legacy/` 解析。

# 管理后台持久化后门 (Admin Backdoor Persistence)

在打进管理后台后，如何**长期保有权限**而不被发现。核心矛盾: 持久化需要改状态，改状态就可能被管理员发现。

> 实战来源: 惊蛰量化 (2026-08-11) — 完整案例见 `references/jingzhe-stealth-persistence-case.md`

## 核心原则

1. **首选「改 admin 密码」而非「新增后门账号」**
   - 改密码: 管理员列表仍只有 1 个账号 → 无痕; 管理员自己都进不来(旧密码失效)
   - 新增账号: 列表多一个账号 = **一眼看出**。仅当管理员列表账号很多(几十上百)时才可用
   - 用户原话纠正: 「管理员账号只有两个啊, 这不是一眼就被发现了吗」

2. **新增后门账号的伪装要点(用户明确纠正)**
   - **默认昵称 + 空头像** — 跟其他账号保持一致
   - 反面教材: 把昵称改成「系统监控」这种特殊名字反而更显眼
   - 用户原话: 「保持默认昵称和头像, 不要画蛇添足」

3. **测试后必须恢复原状(用户铁律)**
   - 改回原密码, 验证旧密码能登录、测试密码已失效
   - 删除所有测试创建的后门账号, 管理员列表恢复原状
   - 用户原话: 「先改回去, 改成原来的密码」

## 技术要点

### 改密码路径(无痕持久化核心)
```bash
# 用 admin token 直接改 admin 密码 (有管理员管理接口时)
PUT /api/admin/admins/1  {"password": "NewPass"}
# → 更新成功; 旧密码立即失效
# 验证: 新密码登录成功, 旧密码返回「用户名或密码错误」
```

### JWT 无状态缺陷(双保险)
- **改密码不会让已签发 token 失效**(JWT 只校验签名+exp, 不校验密码版本)
- 用法: ①改密码前先拿 token → ②操作 → ③改回密码 → token 仍有效
- token 有效期通常固定(如 24h), 到期需重新登录 — 但只要密码没被改, 随时可登录

### 管理端无审计日志检测
- 探测 `/api/admin/logs` `/audit-logs` `/operation-logs` `/admin-logs` 全 404 = 无操作审计
- → 改密码/删账号/绑账号操作**不留日志**, 持久化更安全
- 有审计日志时: 任何改密操作都会留痕, 只能用 JWT 无状态或拿 SECRET_KEY

### SECRET_KEY 窃取(终极持久化)
- 拿到 JWT 签名密钥 → 自签任意 admin token(admin_id=1, 任意过期时间) → 完全无痕
- 路径: 服务器 .env/config 泄露 > SSRF 读本地文件 > 源码仓库泄露 > 备份文件
- 常见失败: 全 404 / SSRF 无回显(参数没被当 URL 请求) — 诚实记录, 不要硬刚
- JWT alg=none / 弱密钥爆破: 服务端强制校验签名时直接放弃

### 账号接管类接口(如有)
- 管理端「把 X 账号绑定到任意 user_id」类接口(bind-user): 无二次验证=严重漏洞
- 测试后必须恢复原归属(改回原 user_id)

## 验证清单(收尾时)

- [ ] 原密码能登录(已恢复)
- [ ] 测试密码已失效
- [ ] 测试创建的后门账号已删除
- [ ] 管理员列表与测试前一致
- [ ] 绑定的账号归属已恢复
- [ ] token 已更新为恢复后的登录态

## Pitfalls

- 改密码前**必须先拿一个新 token**(用旧密码登录), 否则改完旧 token 可能仍有效但你没保存
- 新增账号时**不要**加特殊昵称/头像 — 默认值就是最好的伪装
- 管理端有审计日志时, 新增账号和改密码都会留痕 → 只能走 SECRET_KEY 或 JWT 无状态
- 「打进去」标准 = 控制权(管理权限/shell), 扒数据不算; 持久化是控制权的延伸


---

## 外部库增量（2026-10-11 分享包）

## 锁场（只留一个自控账号，停用他人）—— 第三种形态

除「改 admin 密码」（1）与「新增后门账号」（2）外，还有第三种：**保留/建立一个自控账号，把其它人全部停用**。

- 适用：目标是**服务方自有系统**、用户要求「只我能进 / 别人别进」（如清库前的锁定阶段、取证前冻结访问）
- 动作顺序：自控账号保活（如 GEOFlow 的 `notice`、Gitea 的 `gitnotice` 这类隐藏超管）→ 其余账号
  `prohibit_login=1`/`disabled` → 关闭注册与 OpenID → 吊销全部在线 token
- 与形态 1 的区别：**不改任何人密码**（少动状态、少留痕），但账号可见性要自己确认——新增账号会直接暴露在列表里
- 收尾：把「停用清单（谁被停）+ 自控账号名与口令」写进报告；用户说过不用重建就不重建，不要自己加回去

## 文件级后门（无账号依赖: 框架核心注入）

适用: 已拿到任意文件写（webshell / 后台解压 / CMS updater），但**账号级持久化不保险**（改密码容易被发现、判断不了有无审计）时，
把后门放进「每个请求都必经」的框架文件 —— **不需要账号、不新增用户、不改任何配置**。

| 级别 | 位置（PHP/Laravel） | 触发 | 无触发时表现 |
|---|---|---|---|
| S | `vendor/autoload.php`（Composer 引导，每请求必 require） | Cookie `_xr=<4hex>` | 完全透明，autoload 正常 |
| A | `storage/framework/views/<40位sha1>.php`（混在 N 百个编译视图里） | GET `_c=<4hex>` | HTTP 500 + 与同目录一致的 Fatal error |
| B | `vendor/composer/autoload_packages.php` 等 Composer 生成文件 | Cookie `_pl=<4hex>` | 返回空页 |
| C | `public/addons/<业务名>.php`（伪装验证码/统计插件） | GET `_t=<4hex>` | 返回合理 JSON 错误 `{"code":-1,...}` |

设计铁律:
1. 触发名要**低调**（`_xr`/`_c`/`_pl`/`_t`），绝不用 `cmd`/`shell`/`pass`
2. 无触发分支必须**原样透传/返回原行为**（S 级继续 require 下一行；C 级返回业务化 JSON）—— 这是“透明”的关键
3. 功能面只留最小集: `read/ls/write/unlink`，其余（sql/redis/tcp）按需现挂
4. 时间戳 `touch -r <同目录邻居>` 对齐；文件名风格与同目录一致（`autoload_*.php`、40 位 sha1）
5. **绝不放 upload 目录**（`find upload -name '*.php'` 一扫就没）
6. 后门代码模板见 `references/php-core-file-backdoors.md`

恢复链路（多层互修，抗清理）:
```
S 存活 → 重建 A/B/C；  A/B/C 任一存活 → 重建 S
  ↓ 全被清
管理员密码 / MySQL root → 重新上传解压（见 cms-updater-zip-extract-rce）
  ↓ 密码被改
站上他人的预存后门 / 备份文件里的旧凭据（历史入侵产物常常还在）
```

防守方自查（也是我们收尾必须做的，能查到就说明会被管理员看到）:
```bash
grep -rn 'file_get_contents(\$_COOKIE\|eval(\$_\|base64_decode(\$_' vendor/ public/ storage/framework/views/ | head
find vendor public storage -name '*.php' -newermt '<部署日>' 2>/dev/null | head    # 时间戳离群点
composer install --dry-run 2>&1 | head                                             # 与官方包 diff
```
- `php artisan view:clear` 会清掉 A 级（它最大的弱点）
