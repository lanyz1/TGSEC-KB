# 95306 竞价系统(business-view)前端逆向 — SM4-ECB + bidding 网关

> 2026-08-30 实测。前端 `https://cg.95306.cn/business-view/`(竞价系统,独立于 bfwz-view)。

## 1. 前端 JS 抓取(chunk 带版本号后缀,非 hash)

```
HTML:  https://cg.95306.cn/business-view/  → 内联 <script> = webpack runtime
chunk: /business-view/js/<chunk-xxx>.<version>.js
       version = 1787574513567(页面里找,如 chunk-libs.1787574513567.js)
```

- runtime 里 chunk map 全量列表(chunk 总数 69)
- **app.js = 业务入口(路由+请求封装模块 b775 + SM4 全局函数)**
- **chunk-65b3177a.js = 2.3MB 全量 API 模块**(127 个接口 url 字段!)
- API 定义模式:`function o(t){return Object(r["a"])({url:"/bidRoom/packTable",method:"get",urlType:"bidding",params:t,encryption:!0})}`

## 2. urlType → baseURL 映射(b775 模块)

| urlType | baseURL |
|---|---|
| `bidding` | `/business-proxy/business-bidding` |
| `oss` | `/business-proxy/business-oss` |
| 默认 | `/business-proxy/business` |

## 3. SM4-ECB 加密协议(完全复刻)

```
变量: p="memberserver", b="$e9s20@2o4u^r2"
v = YYYYMMDD(北京时间,主服 UTC 要 +8)
密钥 y = (v + b)[:16]                → "20260830$e9s20@2"  ← encryption 用(每日变!)
密钥 g = (v + "+" + p)[:16]          → "20260830+members"  ← 写接口 participateInProject 用(8/28 报告验证)
加密: SM4-ECB(PKCS7), 输出 base64
请求: GET ?data=<base64(sm4(JSON params))>  (params 含 r=时间戳+随机)
响应: base64(SM4 密文), 解密得 JSON
```

- 纯 Python SM4 实现(无 gmssl)已写成并过国标测试向量 `681edf34d206965e86b3e94f536e4246`(key=0123456789abcdeffedcba9876543210,pt 同)
- JS 端 sm4encryptEcb 定义在 app.js:`l()`=UTF-8 编码,`d()`=UTF-8 解码,key 必须 16 字节

## 4. bidding 网关接口清单(encryption:true)

```
GET /bidRoom/packTable    竞价包件表(目标:报名期/竞价期全量包件)
GET /bidRoom/packDetail   包件详情
GET /bidRoom/initProjInfo 竞价房间初始化
GET /bidRoom/packInfo     包件信息(轮询)
GET /bidRoom/signIn...    签到
POST /buy/bidRoom/offer   出价(写操作,红线)
```

⚠️ **未攻克点(2026-08-30)**:packTable 请求 HTTP 200,但响应密文用 y/g/日期±1 变体均解不开(112B 密文,8/29y 解出 "{" 首字节但后续乱码;非加密请求也返回加密响应)。疑点:服务器日期/密钥变体、或响应另有包装。**9/1 竞价窗口可继续攻**(打通后 = 竞价中全量包件 + 出价数据)。

## 5. 前端常用情报

- 页面从 `localStorage` 读 projId/packId/packName/bidType(登录后存储)
- 路由 `/auction/packs`=自行项目包件页(saleSupplier1)、`/compete`=竞买、`/auction/jointDis`=联合处置
- 公告/包件清单**纯读通道不依赖 bidding 网关**:见 notice-packlist-bulk.md
