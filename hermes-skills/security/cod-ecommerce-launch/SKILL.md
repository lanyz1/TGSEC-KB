---
name: cod-ecommerce-launch
description: "COD电商站部署上线: CentOS+PHP+SQLite/HTTPS/斗篷/像素。触发: 部署、上线、绑域名、斗篷。"
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

> 完整原文（含完整 CVE 表 / 变体矩阵 / 命令全集）：`skill_view(name='cod-ecommerce-launch', file_path='references/full.md')`

# COD 电商站生产部署与上线

覆盖: 长安COD/迅睿CMS系重建版(PHP+SQLite)从本地到生产服务器的完整上线: 环境安装、代码同步、域名+HTTPS、数据迁移、营销配套(斗篷/像素回传)、上线收尾清单。

<!-- split-index -->

## Section index

- [When to Use](references/split-01-when-to-use.md)
- [1. 服务器侦察(先做)](references/split-02-1.md)
- [2. 环境安装(CentOS7 + PHP 8.2)](references/split-03-2-centos7-php-8-2.md)
- [3. 代码上传(本地/服务器配置分离!)](references/split-04-3.md)
- [4. 域名 + HTTPS(Let's Encrypt)](references/split-05-4-https-let-s-encrypt.md)
- [5. 数据迁移(地区库/大表)](references/split-06-5.md)
- [6. 营销配套](references/split-07-6.md)
- [7. 上线收尾清单](references/split-08-7.md)
- [8. 测试/验证坑(curl / shell)](references/split-09-8-curl-shell.md)
- [9. 后台模块扩展(占位菜单 → 真功能)](references/split-10-9.md)
- [10. 后台自助域名绑定(一键切换, sudoers 白名单模式)](references/split-11-10-sudoers.md)
- [11. 配置类接口的 POST 覆盖坑](references/split-12-11-post.md)
- [11b. 后台图片本地上传模式(商品管理/任意表单)](references/split-13-11b.md)
- [Verification](references/split-14-verification.md)
- [12. 组件化落地页编辑器(投手自助建页, 零前端依赖)](references/split-15-12.md)
- [12b. 商品=落地页融合 + 多平台像素(用户纠正)](references/split-16-12b.md)
- [12c. 商品页交互失效根因(Swiper 中断 ready 回调)⭐](references/split-17-12c-swiper-ready.md)
- [12d. 下单提交不跳转/500 完整排查链(三层 bug 叠加)⭐](references/split-18-12d-500-bug.md)
- [12e. CDP 无头调试要点(页面交互问题必用)⭐](references/split-19-12e-cdp.md)
- [12f. 商品详情长图文组件化(用户纠正: 不要 HTML 文本域, 必须组件编辑器)⭐](references/split-20-12f-html.md)
- [12g. 新建落地页 = 添加商品(单页 COD 产品模式)⭐](references/split-21-12g-cod.md)
- [12h. 后台简体 / 前端繁体(用户 UI 偏好)⭐](references/split-22-12h-ui.md)
- [12i. 新建落地页 slug 自动生成(投手零门槛)⭐](references/split-23-12i-slug.md)
- [12j. 后台列表 UI 迭代坑(操作列/弹层/手机预览)⭐](references/split-24-12j-ui.md)
- [References](references/split-25-references.md)
