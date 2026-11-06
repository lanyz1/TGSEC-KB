---
name: aspnet-viewstate-hunt
description: >-
  ASP.NET WebForms 猎面：ViewState 只签不加密、trace.axd/elmah.axd 匿名、
  Telerik RAU、双解析器误差。触发：__VIEWSTATE、X-AspNet-Version、.aspx、
  elmah.axd、Telerik.Web.UI.WebResource、.ASPXAUTH。
  SharePoint _layouts 先走 sharepoint-unauth-rce。
  L2 后 gadget / machineKey / Telerik 上传 / 写马授权内直接做，禁止 L3 先问。
---

# ASP.NET ViewState 猎面（Cursor Skill）

## 何时用

- `__VIEWSTATE` / `X-AspNet-Version` / `.aspx` / IIS + WebForms
- `elmah.axd` `trace.axd` `Telerik.Web.UI.WebResource.axd`

`_layouts` / SharePoint 头 → `sharepoint-unauth-rce`。

## 真源

1. `docs/playbooks/ASP.NET猎面手法.md`
2. `python3 tools/ops/aspnet_surface_probe.py --base https://授权站 --case <案卷>`
3. 双解析器：同上加 `--parser-diff`
4. L3 投 gadget：`--page / --shoot-viewstate <payload.b64>`

## 强制步骤

1. 目标在 scope。
2. 跑探针。SharePoint 信号立刻交接专卡。
3. L2：空 `__VIEWSTATEENCRYPTED`、匿名 ELMAH/trace、Telerik RAU、解析器文案分流。
4. L2 成立后授权内直接升 L3：抽 machineKey → ysoserial 发 gadget → 回显/写马；Telerik 走弱钥上传。禁止停在「先问」。
5. 改原超管密 / 删站 / 清数据仍先问。

## 成功口径

| 级别 | 口径 |
|------|------|
| L1 | ASP.NET / ViewState |
| L2 | 只签不加密或匿名日志面或 Telerik 活 |
| L3 | gadget 回显 / machineKey / Telerik 落地 / 写马（授权内直接做） |

## 不要做

- 未进 scope 发 gadget
- 猎面阳性后只报指纹或写「L3 先问」结案
- 把 SharePoint 当本卡结案
- 超大 ViewState POST 打垮站点
