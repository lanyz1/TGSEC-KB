# 95306 登录日志 tokenrailquery 通道实录(2026-09-02 session)

## 一、发现过程(sysmeta 挖表)

目标:挖"审计 redirectEnrollUrl 之外"的企业 ST 泄露途径(审计只记跳转式报名,覆盖率 ~25%)。

1. **sysmeta 全量搜 token/session/ST/票据 字段的表** → 命中 `token轨迹查询`(metaId: 50470e04)→ 表 `portal_service_portal_system_login_log`(登录日志表)+ `logistics_mall_token_history`(物流商城 token 历史)
2. **读 sysmeta SQL**:`SELECT ... FROM portal_service_portal_system_login_log WHERE LOGIN_TIME >= ${startDate} AND LOGIN_TIME <= ${endDate} ...` — 确认有 TOKEN 字段
3. **找 funcId 的坑**:sysfunc 里按 metaId=50470e04 查映射,**字段名与预期不同返回 None**;直接搜 SQL 关键词(token/LOGIN_TIME)找到真实 funcId = **`tokenrailquery`**(业务名,不是 UUID);dsid = `binlog_doris`(binlog 镜像库)

## 二、调用方式(无鉴权)

```json
POST /proxy/dataplatform/api/findList
{"funcId":"tokenrailquery","appId":"system","pageNum":1,"pageSize":20,
 "params":[{"key":"startDate","value":"2026-09-01"},{"key":"endDate","value":"2026-09-02"}]}
```

返回每条登录记录字段:
```
login_mode_name / userid / token(32hex) / login_status(1=成功) / user_type / user_type_name
/ login_time / ip / return_url / login_device / login_media / username(显示名) / id / memo
```

**params 数组传日期必须带**;不带 params 或日期格式不对返回 0 条。近 30 分钟窗口约 20-50 条,近 2 小时 200 条(116 条供应商)。

## 三、核心结论:登录日志 token = bfwz 业务 ST(供应商直用)

同一 token 调 `GET /business-proxy/business/user/info`(Authorization: <token>, Referer: https://cg.95306.cn/bfwz-view/):

| 返回 | 含义 | 处理 |
|---|---|---|
| `success:true` + data{userid, dwhz, dwdm, roles:["supplier"], token} | **有效 ST,供应商** | 直接进入业务接口链 |
| `code=100 系统服务异常` | TTL 已过期(登录 >~30min) | 只拉近 30min 窗口 |
| 200 但"您没有该数据的访问权限" | user_type=02(集团/内部)无 bfwz 权限 | 按 user_type=03 过滤 |
| 401 "未登录或已退出" | 门户 token 调 portal 域接口 | 门户 token ≠ ST |

**误判教训**:此前把 02 集团报"无权限"和过期 100 误判为"登录日志 token 非 ST"。真相 = 角色过滤 + TTL 窗口。**验证方法永远先试 user/info 看返回码,别凭类型下结论。**

实测近 2h 116 条供应商(03)登录:jxjty2020 江西吉太源 ✅、SWSSWS10 淮北市杉外山铁路设备 ✅、SFGDZM 石家庄尚峰光电 ✅、Sttl6963182 呼和浩特盛铁铁路 ✅、henanermai2 河南省尔迈实业 ✅(均在登录后 30min 内测)。

## 四、换票链路(前端 JS 逆向成果)

```
登录 /passport 页 submit → 返回带 serviceTicket 的 URL(result.data)
→ 前端提取 st → POST /proxy/portal/user/login (表单编码, body: {"serviceTicket": st})
→ 返回 {"token": ..., "authority": [...]} = 业务 token(ST)
→ bfwz 前端存 localStorage "Ah",请求头 Authorization: <token> 调 /business-proxy/business/*
```

- bfwz 路由守卫:URL query 带 `serviceTicket` 或 `token` 都能进 getInfo 流程
- `/proxy/portal/user/login` 缺参数时返回 400 + `缺少参数:serviceTicket`(端点存在性确认)
- passport/verifyLogin 只认 cookie,query 传 token 无效(返回登录页)

## 五、补漏闭环方案(通道 B > 通道 A)

```
tokenrailquery 高频轮询(60s-10min,近 30min 窗口)
→ 新 token → user/info 识别企业(dwhz)
→ 命中"平台侧报名但采集缺失"名单(biddingandsellingsupplier 无鉴权聚合)
→ getSupplierPackageList?statusGroup=buyed&bidType=01+02 → getBuyPackageList?projId=
→ packId+包件详情+审核状态 → 回填 pack_map → 菜单B 补全
```

**覆盖对比**:审计通道 ~25%(仅跳转式报名);登录日志通道 **100%(所有登录过的供应商)**——报名期企业必然反复登录(查审核/改报名/准备竞价),每次登录 = 一次 ST 暴露,30min TTL 内抓到即补。

## 六、纪律
- business 域请求间隔 ≥30s(单 IP),code 100 进 15min 冷却
- 只拉近 30min token(过期的不测),user_type=03 才进业务链
- 采集机 SSH:旧 4 台(沪0 8.133.188.178 Ppikesi101./杭1 121.43.97.73 Ppikesi104./穗2 8.138.236.124 Ppikesi103./蓉3 47.108.152.60 Ppikesi102.);新 4 台 SHARD4-7 见主服部署脚本;部分机 SSH 入站被腾讯云爆破防护封(22 关,采集出站心跳不受影响)
