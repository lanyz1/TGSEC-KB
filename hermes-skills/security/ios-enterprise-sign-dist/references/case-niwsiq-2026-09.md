# 案例:niwsiq 企业签分发 →「原创福利」木马 → 数据后台(2026-09-14 → 09-16续)

## 入口与分发层
- 入口:`https://ztkwm2m0nz.niwsiq.com/1MLILbKZ537D91uKZ?8b34e5bc3=<32hex>`
- 分发域:niwsiq.com(Gname 注册,泛解析;备用子域 odhjotqyzj.niwsiq.com);回源 146.103.66.117;前有 gccdn.net CDN
- 页面伪装:`<title>Google</title>`,SPA catch-all,robots.txt=Disallow /
- 下载 CDN:`wswc99.hgg2023.com`(网宿 wsSecret/wsTime 签名)

## 木马样本
- 名称「原创福利」;内部 appid=2hsbp6;bid=`com.dataapp.dataCollector`;Flutter + 可疑 `doge.dylib`(AdSupport/CoreTelephony/CFNetwork/SQLite)
- 权限插件:flutter_contacts/photo_manager/location/device_info_plus —— 通讯录/相册/定位采集
- Android 侧:isAndroidOn=true 但 apkUrl 为空(未投放)

## 证书链
- 跳板 `jump.mobileprovision`:VINWASH COMPANY LIMITED(越南空壳),TeamID `ZN438TT4S3`,2025-12~2026-12
- IPA `embedded.mobileprovision`:**Chowbus, Inc.(美国外卖平台,证书被滥用)**,TeamID `22788Y94CY`,2026-03~2029-03,AppIDName "POS Ent"

## 数据后台 172.252.224.195(+ sibling 163.223.146.148)
- 端口:80(Vue3 SPA + /manage API)、888(nginx 403)、3622(SSH OpenSSH 9.6p1)、8081-8091(Go)、**22398=BT soft 安全入口**(非 Ajenti)
- soft md5:`41475addd2fb7b605373355b8f4e3c47` — 裸8位 a-z / a-z0-9 均耗尽未中;续打 `/`+8 a-z0-9
- /manage API:auth/login|logout|password;admin/create|list;config/app-frontend|download-links|upload-image;device/list|show|stats|deleteUser|cloneUser|clear|remark;ip-blacklist/add|list;relatives/{id}
- JwtAuth:`env('JWT.SECRET','default_secret')`;DOCUMENT_ROOT=`public/dist`;HOME=`/home/www`
- 设备 JWT:邀请码松(含 `admin`/`10001`)可铸;claims 仅 `user_id`;mass-assign `admin_id` Ignored
- **同 secret 判定**:设备 JWT → `/manage/*` 验签成功后炸 `Undefined admin_id`(跨 148/8088/8090)
- **写 IDOR 坐实**(device JWT → 任意 deviceId):contacts/sms/calls/loc/photos;混淆路径 `/s/ac0yci…`;跨 8083/86/88/90
- 读回需 admin JWT 未闭环;photos JSON 统一「文件读取失败」(假 SSRF)
- 上传:`/uploads/photos/...` UUID 名;195 可读 PHP 尾不执行;150=403 → 假 RCE
- CFG 多端口无鉴权可读;写/SSRF/poison 消费链不成立(8083 phpfilter→.env 仅存储)
- Auth/Login catch 包死;TP `s=`/经典 LFI 被 SPA 吞或 404

## 限速实测数据
- 第 1-4 发:还可尝试 4→3→2→1;第 5 发:直接"登录失败次数过多，请15分钟后再试"(不校验密码)
- XFF/X-Real-IP 伪造:无效;换源 IP / Tor NEWNYM:配额重置 ✓(每出口 4 次有效)
- 喷洒挂背景;主刀非爆破(IDOR/源码/soft/旁路)

## OSINT 关联
- urlscan.io 同款网络(2025-08~09):mnvqia.com / rui4u.com / pengdajiang.com / 54e71s.com / puerct.com / zhny1.com
- 产品谱系:游侠云(uxym.net / codes.uxw.net,"加密版 1500U");站长 YUANLEI / QQ 709466365;演示口令 `SG@UXWNET` 对本站无效

## 产出
- 报告:`/root/niwsiq/REPORT_niwsiq_trojan_2026-09-14.md`
- 战利品:`/root/niwsiq/loot_device/`(JwtAuth dump、IDOR_WRITE_HIT、STATUS_NOW、soft/ssh 进度)
- 脚本族:wave173–wave268(Tor 铸 token / IDOR / Auth dump / soft watch)
