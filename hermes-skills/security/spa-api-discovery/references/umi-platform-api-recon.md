# UMI 企业智脑平台 API 侦察案例(2026-08)

黑盒实战记录:从 SPA 前端挖出真实 API 迁移与请求编码问题的完整过程。目标:山西鼎策云 UMI 企业智脑(多租户 SaaS,来客云AI)。

## 资产与域名

| 域名 | 角色 |
|------|------|
| cqwgw3.dcyuyx.umi6.com | 前端入口(Vue3 SPA) |
| qyapi.umi6.com | 登录/用户 API(旧,但仍在用) |
| znapi.umi6.com | **业务 API 新址**(/api/v1/...) |
| aigc.umi6.com / updown.umi6.com / testaizdrw-v1.umi6.com | 其他子系统 |

## 关键发现与步骤

### 1. API 迁移检测
- 报告(前一天)记录 qyapi.umi6.com 为后端;实测发现业务接口实际走 **znapi.umi6.com/api/v1/system/...**
- 判定方法:浏览器 `performance.getEntriesByType('resource')` 列出真实请求,看到 `https://znapi.umi6.com/api/v1/system/growth-power/project/lists?...`
- qyapi 仍响应但登录接口报"输入值解析错误"(旧参数格式?),新前端 buildTime 2026-08-07 显示刚更新

### 2. 登录接口与密码编码
- 真实登录请求(从页面 hook XHR 抓到):
  ```
  POST https://qyapi.umi6.com/api/login/account
  body: {"terminal":4,"account":"<PHONE-REDACTED>","password":"<编码值>","scene":1}
  ```
- **curl 直接发明文 password 全部报 `{"code":0,"msg":"输入值解析错误"}`**,页面登录却成功
- 前端 JS 里出现 `password?unescape(encodeURIComponent(s.password)` 线索 → 高度怀疑密码字段被前端编码(未完全还原;可能还涉及 axios transformRequest)
- 教训:console/hook 里 password 显示 `"***"` 时,先确认是工具打码还是前端真替换;hook `send()` 的原始 body 才是真相

### 3. token 提取
- 登录成功后 localStorage key = `SOY_token`,值为 32 位 hex(JSON 字符串包裹)
- token 传递头名不确定(SOY-Token / token / Authorization Bearer 都试过,页面用 SOY-Token 或页面内 axios 拦截器注入)

### 4. ThinkPHP 指纹
- `Server: Tengine`,`/index.php?s=/index` → 200(ThinkPHP 兼容模式)
- 根路径显示"系统已停止维护"(nginx 默认页),业务在 /api/* 下

### 5. 前端 JS 特点
- 所有 JS 是 **gzip 压缩**(curl 需 `--compressed`,否则 file 显示 gzip 数据)
- 主 index js 是加载器;业务接口路径在 chunk(`vue-XXX.chunk.js` 等)与页面级 chunk
- 登录参数常量: `login/account` 定义 `data:{terminal:4,...e}`;`login/register` 定义 `data:{channel:"4",...e}`

## 复现脚本要点

```python
# 登录(若还原编码后):
POST https://qyapi.umi6.com/api/login/account
{"terminal":4,"account":"<PHONE-REDACTED>","password":<编码>,"scene":1}
# 业务(新):
GET https://znapi.umi6.com/api/v1/system/...  (需 token)
```

## 遗留问题

- 密码编码算法未还原(下轮优先:在 chunk 里找 qf() 调用处,还原 transformRequest)
- znapi /api/v1/system/{capacity,product,react/chat} 系列接口的越权/上传/RCE 面未测
- qyapi 的 /api/v1/ 路径不存在(ROUTE_NOT_FOUND),确认业务 API 全在 znapi
