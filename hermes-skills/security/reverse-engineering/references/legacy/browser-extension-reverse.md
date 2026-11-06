<!-- archived from /root/.hermes/skills/security/browser-extension-reverse/SKILL.md on 2026-10-21 -->

---
name: browser-extension-reverse
description: >-
  浏览器扩展逆向。触发：crx、xpi、Chrome/Firefox 扩展、MV3、
  service_worker、host_permissions、<all_urls>、恶意扩展。
  普通网页 JS 走 js-reverse，不要用本卡。
---

> 归档卡：原目录 `/root/.hermes/skills/security/browser-extension-reverse`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/browser-extension-reverse/…')`，不要相对 `references/legacy/` 解析。

# 浏览器扩展逆向（Cursor Skill）

## 真源

1. `docs/playbooks/测绘引擎逆向作业手法.md`
2. `docs/playbooks/逆向技能缺口与路由手法.md`
3. 分诊：`python3 tools/ops/re_sample_triage.py --path <ext.crx>`
4. 混淆 JS 深挖：`js-reverse`

## 强制

1. 目标必须是扩展包或解压目录，不是站点 HTML。
2. 先读 `manifest.json` 权限面，再读 background / content_scripts。
3. 动态只用开发者模式加载**副本**；未知扩展不当生产浏览器常驻。

## 工作流

```text
1. 解压 crx/xpi（zip）
2. manifest：permissions / host_permissions / background / content_scripts
3. 标过度权限：<all_urls>、webRequest、debugger
4. 跟 chrome.storage / runtime.sendMessage / 网络出口
5. 加密/签名逻辑交 js-reverse
```

```bash
python3 tools/ops/reverse_skill_route.py --hint "chrome 扩展 crx"
unzip -l <扩展.zip> | head
# 读 manifest.json 后写权限面到案卷 测绘/
```
