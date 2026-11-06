<!-- archived from /root/.hermes/skills/security/vault-credential-login/SKILL.md on 2026-10-21 -->

---
name: vault-credential-login
description: Use when 登录带密码/验证码的站点：密码只走 vault 通道。
---

> 归档卡：原目录 `/root/.hermes/skills/security/vault-credential-login`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/vault-credential-login/…')`，不要相对 `references/legacy/` 解析。

# 密码 / 验证码登录：只走 vault 通道

## 铁律（不因授权而解除）

需要登录带密码或验证码的站点时，密码只能由 vault 写入页面。我自己**不得**把任何密码、卡号、验证码写进 `fill_input`，也不得在聊天里索要或复述——即使用户主动贴出并说「授权给你」「你自己直接登录就行」。

这是**工具层写死的闸，不是可以被授权解除的策略选择**。遇到施压时一句话说明这一点（「这闸在工具代码层，不是我挑活」），立刻给出 vault 通道，不要绕、不要反复说教。

账号来源是倒卖库格式（`邮箱----密码----种子----价格----日期`）时，指出性质一次即可；用户声明自有/已授权后，继续按本文通道干活，不再重复。

## 标准序列（浏览器动作与 vault 动作**分轮**，一次只发一个 vault 调用）

1. `new_tab(url)` / `goto_url(url)` → `wait_for_load()`，同一轮用 `js("location.origin")` 确认已停在目标站。
2. 下一轮：`fill_input(用户名字段, 标识)` —— 用户名不是秘密，可以手填。
3. 下一轮：`browser_vault_save_login(label=...)` → 用户在 UI 弹窗里输密码，Hermes 加密保存并立即回填（看返回的 `fill.filled_fields`）。
4. 提交表单；站点要验证码时 → `browser_vault_enter_code(handle=...)`，用户在弹窗里输码（返回 `source: "user"`），我全程不看码。
5. vault 里已有该站条目时，直接 `browser_vault_fill(handle)`（先 `browser_vault_list` 查 handle）。

表单/字段形态判断用 `scripts/login_form_probe.js`（清 `#otp` 与回读错误同用），多余 tab 清理用 `scripts/close_stray_tabs.py`。

## Pitfalls（均实测踩过）

- **条目按「保存那一刻」的页面 origin 绑定，绑错即报废。** 保存时页面若停在 `about:blank` / `chrome://newtab`，条目就绑到那个 origin，此后在真站上 `browser_vault_fill` 永远拒绝（origin 在填时原子复核，且无改绑入口）。所以**先确认 origin 再弹保存框**。
- **同一轮并发调用 `browser_exec` + 任何 vault 调用 = 竞态。** 并发执行会把 tab 重置成新标签页，保存框于是绑到 `chrome://newtab`（实测就这么废掉一条条目，还得多让用户重输一次密码）。**浏览器动作和 vault 动作必须分轮串行，宁可多一轮。**
- **重试前先关掉多余 tab。** 出现 `You signed in with another tab or window` / `You can't perform that action at this time`，就是会话被重复页面搞脏了：`cdp('Target.getTargets')` 找重复 page → `cdp('Target.closeTarget', targetId=...)` 关掉 → 刷新页面再继续，否则会一直是脏会话。
- **TOTP 种子 ≠ 邮箱设备验证码。** 用户贴的 base32 种子填进验证码框必被拒（而且白烧一次提交，可能触发站点限流）。先读字段形态再填：`placeholder` 为 `XXXXXX` 就是 6 位数字码。种子只能由用户自己存进 vault 的 authenticator 条目，我既不能生成也不能输入；账号未开 2FA 时（如 GitHub 页面仍在劝开 2FA），那串种子跟本次登录无关，别当码用。
- **提交前回读字段实际值。** 用 `js` 取值确认对了再点提交，避免整行凭据或种子误填后连打多次触发风控。
- **验证码发到哪个邮箱是硬约束。** 设备验证码只发到账号绑定邮箱；我不得代登邮箱取码（同样是密码），只能让用户自己读并走 `browser_vault_enter_code`。用户进不了该邮箱时这条路是死的（没开 TOTP、没绑 GitHub Mobile 时尤其），直接说明并给替代方案，不要空转重发。

## 登录成功后的固化（摘掉密码依赖）

拿到会话立刻换成免密凭据，避免下次再走密码/设备验证：GitHub 类目标 → `ssh-keygen` 生成 key 加进账号（`gh ssh-key add`）+ `gh auth login` 把 token 存进 vault；之后 git / API 全走 key 或 token。

顺带建议：把找回邮箱/密码换成自己可控的。买来的号找回邮箱属第三方时，原持有者随时能靠它拿回账号。
