# 授权矩阵扫描 harness(2026-09 实测)

对后台/API 做\"逐路由允许 vs 拒绝\"探测时的方法与坑。同时是 finding 的挖掘工具:
本文件描述的扫描正是发现「业务域模块鉴权最松」这条规律的手段。

## 一、资产组织

- 路由全集:优先取应用自身的 API dump(`/api/*` 列表接口、swagger、前端 chunk 里抽取),
  落成 `{data:{apis:[{method,path,summary}]}}`;比手写字典覆盖率高一个量级(实测 1077 条)
- 按**包含模块**收敛到待测集(如 system/autocode/appadmin/gatewaynode/upload/plugin),
  再叠加**破坏性排除表**

## 二、排除表要用\"精确段匹配\",不要用子串(血泪)

第一版排除表写了子串 `"sign"`,结果把 `/appAdmin/org/signingCerts/*` 和
`/appAdmin/org/installerBuildJobs/*` 一起过滤掉了 —— **扫描结果里静默少了整块候选面**,
事后才发现。规则:
- 排除用动词/精确片段:`delete/remove/reset/logout/import/sync/trigger/batch/replace/apply/rollback`
- **把被排除的条目单独落盘**,扫完人工过一遍,否则你无法知道覆盖率缺口
- 逐条打 `method` 白名单(只发 GET 和自己的空体 POST)

## 三、空体 POST 会真写库(必须提前假设)

\"发空 body 只为了看校验报错\"是错的。实测空体直接提交成功的:
```
POST /appAdmin/org/customerDistribution/policies/save  → code 0,新建记录 ID=2
POST /appAdmin/traffic/share/create                    → code 0,生成 share key
POST /appAdmin/trafficFlows/webDomains/save            → code 0,\"保存成功\"(把配置写成空列表!)
```
纪律:
1. **排除表必须含 `*/save`、`*/create`、`*/update`、`*/webDomains/import` 之类**,\"只是想看报错\"也不行
2. 真要探这些接口,**先读前像**:`GET` 同一资源把当前值存盘(尤其配置类),
   否则事后无法证明\"本来就是空的\"还是\"被我清掉的\"(实测踩过:`webDomains` 事后两站都返回 `[]`,无法自证)
3. 扫完把\"意外写入\"列成账,逐条找对应 delete 恢复,并向用户交代
4. `*/delete`、`*:id` 这类路由**绝不放进自动扫描**,单独手工、单独确认

## 四、harness 工程细节(省几十轮调试)

- **别把结果管道接 `tail -10`**:复用旧 runner 时它写死了输出截断 + 短超时,
  284 条扫描只回 10 行、且看不出是被截断还是被中断。用\"推送-执行-取回\"三段式:
  SFTP 传脚本 → `timeout 800 python3 -u x.py > x.out 2>&1; wc -l x.out` → SFTP 取回 `x.out` 本地分析
- **`python3 -u`(或 print(..., flush=True))**:被 timeout 杀死时缓冲区内容全丢,只剩半截日志
- **单请求超时要压到 6-8s**:个别路由会挂,20s 超时会让整轮扫描被外层掐断(实测 420s 只跑完 1 条)
- 批量只读探测**走本地代理直连通常比经跳板机快几十倍**(跳板机 exec 通道实测单请求 ~200s);
  本地脚本要 `Session.trust_env=False` + 显式 `proxies={...}`,别让系统代理环境变量乱接管
- 工具侧前台调用有硬上限(420s),长扫描**起后台 + 完成通知**,中途 poll 进度

## 五、判读结果

- 三类要分开统计并留原文:`PASS`(权限通)/ `BLOCK`(「权限不足」类)/ `ROUTE404`(模块已下线)
- **`ROUTE404` 不是\"我没有权限\",是\"这段代码不在这台实例上\"**:同一代码库不同 vhost/build
  路由集不同;这里 404 换 vhost 可能就有(反之亦然)
- 报参数错(`XXX 不能为空`)比 `code 0` 更有价值:说明**权限已过,只差参数**,是最干净的写原语
- 敏感返回按价值记:`apiToken`/`secret`/`inviteCode`/`sysUserId`/内部 URL 优先
- **加一句 `无平台管理权限` 的报错是\"处理器内部还有一层更高的角色判定\"**,不是 casbin 拦截 ——
  两者要分开记:后者换角色可解,前者要换账号等级

## 六、触发式验证

扫到写原语后,验证顺序:
1. 空体 → 拿到必填字段报错
2. 从前端 chunk 抠 schema(`x=me({...字段+校验...})` 模式),别猜字段名
3. 用最小合法体真调一次 → 看落库/落盘位置
4. **立即用对应的 delete/还原接口清掉**,并把产物路径记进副作用账
