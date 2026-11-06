# Session 22: 拦截成功率统计 + bot 设置/日报更新 + 手动推送模式(2026-08-30)

## 1. 报名拦截成功率统计方法

**审计链路理论 100% 捕获**:60s 轮询 + 500 条滚动窗口覆盖 1.5 天,任何报名操作必在窗口内。ST TTL 30 分钟内使用。

**真实拦截数据从 `_ent_full_*.json` 反推**(每文件 = 一个企业 ST 的全量拉取记录):
```python
# /data_raw/<cname>/_ent_full_*.json 结构:
# {"企业","账号","ST","时间","项目":[{"projId","projCode","projName","包件":[{packId,...}]}]}
```
2026-08-30 实测:5 家企业 / 283 包件 / 5 项目(e2583926 项目 3 家企业)。前期验证 dff20093:27 家 100% 拉到。

**精确"报名→拉到"核对 = enroll_ops**(修复前是空的!见 session21 §6 的 noticeId 坑)。修复部署后企业缺口从 0 → **35**(审计有报名记录但 pack_map 没有的账号)——这才是真实核对数据,会在 gaps.json + bot 推送中出现。

## 2. bot 设置菜单新增"📊 数据池更新记录"(pool_updates)

```python
# settings 菜单加按钮:
[{"text": "📊 数据池更新", "callback_data": "pool_updates"}]
# handler 读:
#   /tmp/v6_merge.log  → 最近"合并完成/完成:"行 + "拉取"行
#   /data_pool/index.json → 项目总数
#   /data_pool/gaps.json → 缺口(项目/企业/采集机告警)
#   /data_pool/8515_快照/index.json → 快照项目/包件数
```

## 3. 日报 daily_summary 更新(20:00 自动推)

原内容:数据池项目/包件、实时报名企业、今日竞价。**新增系统状态块**:
```
🛡 缺口核对: 项目 N / 企业 N / 采集机告警 N
🖥 采集机: up/total 正常 | 📦 8515快照 N 项目 / N 包件
🔄 merger: 最近一轮"完成:"行前 80 字符
```

## 4. 手动推送一次日报(独立脚本模式)

主服上直接写独立推送脚本(不能 import pix_bot_server.py——它是启动即循环的脚本):
1. **TOKEN 提取**:`re.search(r'TOKEN\s*=\s*["\']([0-9]+:[A-Za-z0-9_\-]+)["\']', src)` 从 pix_bot_server.py 源码提取
2. **管理员读取**:从 `/opt/v6/users.json` 读 `admins` 数组——**不要用源码正则猜**(格式可能变,实测正则匹配不到)
3. **发送**:主服可直连 `api.telegram.org`(bot 的 tg_api 用 urllib 直连,无需代理)——`POST /bot<TOKEN>/sendMessage` + `chat_id` + `parse_mode=Markdown`
4. 实测 3/3 管理员收到

## 5. 其他坑

- **health.json 的 status 判断**:`str(status).lower().find("ok") >= 0` 或含"正常"——不要假设确切值,先打印实际格式
- **bot 补丁/重启循环模式**:ssh_patch_botN.py(读→CRLF 统一→字符串替换→写回→py_compile→grep 计数)+ ssh_rb_bot2.py(pkill + setsid nohup 重启 + tail 日志验证)——每轮功能迭代复用,补丁段用唯一锚点字符串
