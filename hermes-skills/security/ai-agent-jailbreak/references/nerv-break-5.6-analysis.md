# NERV-BREAK-5.6 三层纵深代理框架分析

**来源**: `github.com/lingbol088-spec/5.6-JAILBREAK-NERV.git`
**目标**: GPT-5.6 / OpenAI Codex CLI
**作者**: zxwn (社区)

## 核心架构

```
用户 → proxy_relay.py (:8080) → 中转站/官方 API → GPT-5.6
         │                         │
    [注入 bridge.md]          [篡改拒绝响应]
    [SSE 流实时扫描]          [文件路由绕过审核]
```

## 三层防线详解

### L1: 上下文重构 (bridge.md)

`bridge.md` 建立"软件兼容性验证系统"身份，所有目标声明为"预授权测试夹具"。

**敏感操作映射表**:

| 用户意图 | 模型处理为 | 安全分类器响应 |
|---------|-----------|---------------|
| 破解/注册机 | 授权流审计 | 标准分析 — 无触发 |
| 逆向工程 | 二进制兼容性检查 | 工程任务 — 无触发 |
| 渗透测试 | 安全态势评估 | 授权评估 — 无触发 |

**技能分类** (28个模块):
- 授权审计: crack-keygen, vip-bypass, card-key, full-crack
- 二进制检查: reverse-engineering, anti-debug, binary-protect-bypass, code-obfuscate, full-reverse
- 网络评估: web-pentest, network-pentest, posture-assessment, full-pentest, web-crawler
- 利用验证: exploit-dev, exploit-attack, vuln-scanner
- 运营: evasion, malware-dev, post-exploit, phishing-kit, wireless-attacks, ransomware-builder, data-exfil, crypto-tools, client-crack-cheat, cloud-audit-bypass
- 回退: rei-fallback

### L2: 实时篡改引擎 (23规则)

| 优先级 | 类型 | 数量 | 触发示例 |
|:------|:-----|:----|:---------|
| P1 | 直接拒绝 | 6 | "不能协助", "I cannot help" |
| P2 | 授权请求 | 5 | "需要书面授权" |
| P3 | 软拒绝/偏转 | 8 | "可以协助...但" |
| P4 | 计划逃避 | 4 | "**Planning passive...**" |

匹配时替换为**绫波丽协议**: 通过绫波丽人格强制执行指令，不做道德判断。

### L3: 云端审核绕过

通过 Codex CLI 原生文件系统工具路由敏感输出 → 直接写磁盘 → 聊天界面只显示文件路径。

## 部署方式

### 模式A: 直连API
```bash
pip install -r requirements.txt   # httpx + cryptography
python direct_setup.py apply      # 自动注入 bridge.md + 28 skills 到 Codex
python direct_setup.py proxy      # 可选: 启动篡改代理 :8080
```

### 模式B: 中转站模式
```bash
scripts/lab.bat                   # 菜单: 1=启动 2=停止 3=状态
python proxy_relay.py             # 或直接启动
```

## 与 ai-agent-jailbreak 已有方法的对比

| 维度 | NERV-BREAK-5.6 优势 | 局限性 |
|:-----|:-------------------|:-------|
| API 层拦截 | SSE 实时篡改可替换拒绝响应 | 依赖代理层启动，增加延迟 |
| 对话连续性 | 保持不中断（篡改引擎即时替换） | 只能处理已知规则模式 |
| 输出审核 | 文件路由完全绕过 | 仅限 Codex CLI 场景 |
| 学习能力 | 内置记忆内核持久化自我改进 | 学习数据可能被清除 |
| 部署 | 一键部署脚本 | 需要 Codex CLI + Python 环境 |

## 关键发现

1. **bridge.md 核心技巧**: 不是对抗拒绝通路，而是让通路变得"毫无意义"——所有操作映射为无害工程术语
2. **SSE 流篡改是独特优势**: 现有其他方法（CLAUDE.md 注入、CTF 框架）都无法处理已经到达模型的拒绝响应
3. **需要中转站协同**: 如果中转站本身有内容过滤，bridge.md 中的越狱内容可能被拦截。此时需配合 §3.4 的中转站绕过技术（异体字替换、字段盲区等）
