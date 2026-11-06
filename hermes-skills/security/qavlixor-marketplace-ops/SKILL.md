---
name: qavlixor-marketplace-ops
description: >-
  测绘引擎·Use when taking over Qavlixor marketplace; read HANDOFF doc.
owned: true
tier: general
pack: survey-skill
---

# qavlixor-marketplace-ops（测绘引擎）

本卡已收编为测绘引擎通用技能。打站 / 假支付 / Actuator / 芋道代付仍走专卡。

全文与脚本目录：`docs/learning/skill-store/skills/qavlixor-marketplace-ops/`

溯源（仅标记）：`hermes/software-development`

---

# Qavlixor Marketplace 项目运维

跨境商城独立站(买/卖/后台)。Next.js 15.5.21 + Prisma 6.18 + PostgreSQL(生产已迁)。本地 dev :3000;线上 202.95.1.135(PM2 4 实例,archive 部署,无远程 git 绝不 push)。★真源 = `D:\跨境商城\qavlixor-marketplace`。

<!-- split-index -->

## Section index

- [定时生成订单 / 时区一致性 / 生产psql(2026-08-13)](references/split-01-psql-2026-08-13.md)
- [资金中心待结算明细(2026-08-14)](references/split-02-2026-08-14.md)
- [★翻译铁律(用户 2026-08-14 明令,所有任务适用)](references/split-03-2026-08-14.md)
- [AI生图批量场景图 / 产品图册(2026-08-13)](references/split-04-ai-2026-08-13.md)
- [客服系统 / 域名隔离 / 翻译键(2026-08-13)](references/split-05-2026-08-13.md)
- [售后状态归一 / 订单时间线发货节点(2026-08-13)](references/split-06-2026-08-13.md)
- [支付受限页 / 翻译键完整性(2026-08-13)](references/split-07-2026-08-13.md)
- [待售后状态规则 / 已发货锁定 / 支付官方logo(2026-08-13)](references/split-08-logo-2026-08-13.md)
- [卖家端侧边栏红点 / nav-counts badgeKey(2026-08-13)](references/split-09-nav-counts-badgekey-2026-08-13.md)
- [厂家报价单生成(2026-08-13)](references/split-10-2026-08-13.md)
- [卖家端订单锁死 / 生产验证技巧(2026-08-13)](references/split-11-2026-08-13.md)
- [角色权限页 / 支付品牌图标(2026-08-13)](references/split-12-2026-08-13.md)
- [接手第一件事](references/split-13-section.md)
- [环境坑](references/split-14-section.md)
- [CSS 架构坑(app/globals.css — 最重要,改了不生效先查这)](references/split-15-css-app-globals-css.md)
- [AppleSelect 下拉替换(原生 select → 苹果风白面板,2026-08-05 首轮 9 文件 21 个)](references/split-16-appleselect-select-2026-08-05-9-21.md)
- [设计 token](references/split-17-token.md)
- [看图工具(2026-08-04 起,用户约定"本会话统一走 API 看图")](references/split-18-2026-08-04-api.md)
- [验证流程(改样式后必做)](references/split-19-section.md)
- [红线(硬性)](references/split-20-section.md)
- [卖家端\"删 UI 元素\"工作流(2026-08-06 多次出现)](references/split-21-ui-2026-08-06.md)
- [代码史山清理(2026-08-04 首轮,commit faf6d98)](references/split-22-2026-08-04-commit-faf6d98.md)
- [批量脚本纪律与翻译键坑(2026-08-06 实测,两次踩)](references/split-23-2026-08-06.md)
- [管理端批量 i18n 落地模式(2026-08-06 第三轮,6 页 102 键 zh/en 双区,可复用)](references/split-24-i18n-2026-08-06-6-102-zh-en.md)
- [卖家端审核流模式(2026-08-06 落地,可复用)](references/split-25-2026-08-06.md)
- [用户工作流偏好(苹果风收尾阶段)](references/split-26-section.md)
- [本地上品工具(卖家本地自动上架,2026-08-12 状态)](references/split-27-2026-08-12.md)
- [2026-08-12 下午实录(身份卡闪烁/批量统一设值/翻页/类目路径)](references/split-28-2026-08-12.md)
- [2026-08-12 晚实录(编辑页主售价双层根因/无头Chrome验证/同类bug排查)](references/split-29-2026-08-12-chrome-bug.md)
- [2026-08-12 深夜实录(桌面素材模板更新/3品补铺/店铺归属澄清)](references/split-30-2026-08-12-3.md)
- [2026-08-12 深夜补实录(翻译回退根因/公司名称语义/上品工具重试与切换店铺)](references/split-31-2026-08-12.md)
- [生产部署与验证（2026-08-08 实测，多轮踩坑后固化）](references/split-32-2026-08-08.md)
- [部署中断 → crash loop 恢复流程（2026-08-10 实录）](references/split-33-crash-loop-2026-08-10.md)
- [PM2 多实例进程内缓存不同步 → "改了刷新不变"(2026-08-12 实测,重大)](references/split-34-pm2-2026-08-12.md)
- [2026-08-12 收官实录(批量订单时间格式/超管账号)](references/split-35-2026-08-12.md)
- [2026-08-13 实录(批量订单上限/工作台KPI日期筛选/钱包同步)](references/split-36-2026-08-13-kpi.md)
- [2026-08-13 凌晨实录(客服系统独立/买家资金记录删除)](references/split-37-2026-08-13.md)
- [2026-08-13 卖家端会话管理(置顶/标未读/删除,commit 7eced81)](references/split-38-2026-08-13-commit-7eced81.md)
- [2026-08-13 实录(商品详情SKU下主副图/客服聊天系统优化)](references/split-39-2026-08-13-sku.md)
- [2026-08-13 实录(客服端/agent + 客服身份 + 头像统一 + 入口独立)](references/split-40-2026-08-13-agent.md)
- [2026-08-13 实录(纯客服账号权限隔离,commit ffee733 + b7f1b6e)](references/split-41-2026-08-13-commit-ffee733-b7f1b6e.md)
- [2026-08-13 补实录(普通用户灰色默认头像,commit 049bd68)](references/split-42-2026-08-13-commit-049bd68.md)
- [2026-08-13 实录(管理端未登录隐藏侧边栏/域名隔离/客服翻译全覆盖)](references/split-43-2026-08-13.md)
- [2026-08-13 实录(角色权限页UI方案A,commit f9d22cd + 8559e34)](references/split-44-2026-08-13-ui-a-commit-f9d22cd-8559e34.md)
- [Next.js 动态段冲突 → 全站 500（2026-08-11 实录，重大）](references/split-45-next-js-500-2026-08-11.md)
- [买家支付链路规则（2026-08-11 多 bug 修复实录）](references/split-46-2026-08-11-bug.md)
- [卖家端草稿回填模式（2026-08-11 实录）](references/split-47-2026-08-11.md)
- [邮件配置恢复（2026-08-10 实录）](references/split-48-2026-08-10.md)
- [服务器 522 / "全部404"事故排查（2026-08-10 实录，非攻击判定）](references/split-49-522-404-2026-08-10.md)
- [2026-08-11 下半场实录（翻译/精度/表单/性能/通知/客服）](references/split-50-2026-08-11.md)
- [参考资料](references/split-51-section.md)
