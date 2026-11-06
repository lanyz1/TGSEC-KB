# UMI/webpack 路由 chunk 全量拉取 + H5/APP 包二次挖面

> 2026-09 实战(灰豚 dy.huitun.com/app 的 UMI 包 2.3MB → 1,340 接口;
> 再加 H5 包 251KB → 另 174 个 PC 包里没有的接口,并**新发现 3 个未授权端点**)。
> 单点结论:PC 端接口清单 ≠ 全量;**页面级 chunk 才有参数**;**移动端包必须单独挖**。

## 1. chunk URL 规则(webpack runtime 的 `.u` 函数)

压缩产物里会出现一张 id→hash 映射 + `.async.js` 后缀:

```js
t + "." + {0:"a40763c4", 1:"95709147", …, 162:"9532311c"}[e] + ".async.js"
```
⇒ 实际 URL:`https://<站点>/app/<id>.<hash>.async.js`

**⚠️ 最大坑:文件里通常有 2 张同形状映射表(一张给 JS、一张给 CSS)。**
用错表拿到的 URL 会返回 **约 478 字节的 COS/S3 `NoSuchKey` 错误页**(不是 404 状态,是 200 里裹着 XML)。
判读与规避:

```python
# 逐个映射块挑选"含已知可用 id 的那张表"
maps = [dict((int(k),v) for k,v in re.findall(r'([0-9]{1,3}):"([0-9a-f]{8})"', m.group(0)))
        for m in re.finditer(r'\{(?:[0-9]{1,3}:"[0-9a-f]{8}",){5,}[0-9]{1,3}:"[0-9a-f]{8}"\}', T)]
hm = next((d for d in maps if d.get(36) == "b1af90f8"), None)   # 用已在浏览器里验证过的 id 锚定
```
另:先 `curl -sI` 校验一个 chunk 的字节数(正常 chunk 常 100KB~1.5MB),**别用"HTTP 200"当成功**。

## 2. 从路由表反推"该拉哪些 chunk"

UMI 路由表就在主包里,形如:

```js
{name:"达人详情", path:"/anchor/anchor_list/anchor_detail",
 component:Object(E.b)({component:function(){return Promise.all([n.e(0),n.e(8),n.e(15),…,n.e(36)]).then(n.bind(null,"r27/"))}})}
```
- `n.e(<id>)` 列表 = 该页面加载的 chunk 集合;**比父路由多的那些 id 才是这个页面自己的业务 chunk**(本例达人详情页 = 36)。
- 页面 chunk 里是**参数与字段名**(`payload`、`{uid,pageNum,contactWay}` 之类);
  **接口路径字面量多在主包(共享 api 模块)**里 —— 两者结合才是完整契约。

## 3. H5/APP 包单独挖(高产出,常被忽略)

```
https://dy.huitun.com/phone/            # H5/APP webview 入口(通常是 CRA: /phone/static/js/main.<hash>.chunk.js)
https://dy.huitun.com/app/              # PC 端(UMI)
```
同一份代码在移动端常用**不同路径名**(本例 PC `/anchor/...` vs APP `/user/detailInfo`、`/aweme/detail2`),
且**白名单更松**:本次仅通过 APP 包才发现的未授权端点包括 `/common/dyCid`(1.16MB 类目树)、
`/common/mobile`(APP 配置)、`/common/festivalList`。

做法:把 APP 包的全部接口串出来,做**有/无会话双扫**(每接口 2 发),按响应体是否含真实数据分类
(登录过滤文案、404、空占位一律丢)。这一步是本目标里性价比最高的一轮。

## 4. 其他拿到包名/入口的旁路

- **前端错误页会漏 chunk 名**:`Unable to preload CSS for /css/home-XXX.css` 报错栈里直接带 JS 名 ⇒ 顺手当入口。
- SPA 全站兜底(Spring Cloud Gateway / nginx)会把任意路径渲成首页 HTML ⇒
  **别把"200 + 首页 HTML"当路径存在**(本例 `robots.txt` 的 `Disallow:` 路径全部是假阳性)。
- buildId 差异可发现**多构建/多部署**(旧 build 常留旧接口),RSC/`_buildManifest.js` 可看路由总数。

## 5. 交付物模式

把"包 → 接口清单 → 有/无会话双扫 → 分类结果"做成**可重跑脚本**并落盘 TSV
(`path \t status|size \t class \t 证据摘要`),后续每轮只增量补扫;报告里给
"接口总数 / 未授权命中数 / 有真实数据数"三个数,比罗列路径有说服力。
