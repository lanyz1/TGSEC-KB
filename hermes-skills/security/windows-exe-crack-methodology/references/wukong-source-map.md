# 悟空聊天(wukong-chat v3.1.7)源码深挖施工图(2026-08-09)

完整文档: `D:\渗透\wukong_src\源码深挖文档.md`(429行)+ `源码深挖补充.md`(375行)+ `map_extract.py`(映射提取脚本)

## 架构 4 层(复刻施工图)
```
前端 Vue3(63页)→ IPC(localRequest/localRequest2/localRequest3/accountList/startConnect/runTask/ws-send)
→ CommonInterceptor(82 URL 分发)→ Service/Logic → 本地 SQLite(46 表)+ 远端服务器 + TikTok 官方
```

## 源码深挖方法论(可复用于任何 Electron 采集工具)
1. `find src/views -name "*.vue"` 列页面 → 正则提取每个页面 import 的 `src/api/*request.ts`
2. `src/api/*.ts` 全是 `window.ipcRenderer.invoke("localRequest"/"localRequest2", 模块, 方法, options)`
3. 主进程 `main.ts`: localRequest → `CommonInterceptor.process(url, options)`(巨型 if-else 82 分支)
   localRequest2 → `process2(url, oper, options)`(模块化: agent/agentReply/letterTask/messageTemplate/monitorMessageReplyTask/msgReplyRecord/speechcraft/speechcraftGroup)
   localRequest3 → worker 线程(异步任务)
4. `electron/interceptor/CommonInterceptor.ts` = 页面操作→service 的完整映射表
5. `electron/database/MultiDBManager.ts` = 46 张建表语句(正则 `CREATE TABLE (\w+)` 提取)
6. WS cmd 从 `electron/wss/wssLetterUtilWeb.ts` 提取(每方法内的 `cmd=` 或 `Headers.create({key:"cmd",value:"N"})`)

## 数据库 46 表(复刻建库直接用)
账号: pm_account_manager/account_resource/account_status(status='违反约束')/account_play_exce/account_play_violation
好友: pm_fans/fans_req/fans_letterflag/fans_conversation/friend_note
会话消息: pm_conversation_info/member/url、pm_letter_history、pm_message_task/reply、pm_msg_reply、pm_pin_mark
群组: pm_creategroup_record/group_history/group_member_fail/group_task_account/members
营销: pm_message_template/monitor_message_reply_task/speechcraft/speechcraft_group/quick_speech/tags/my_tags/giphy_resources
代理: pm_proxy_info(proxy_type/proxy_ip/proxy_port/region/username)
AI: pm_agent/agent_reply/agent_status/character_profile
其他: pm_link_manager/play_info/resource/user_info/func_setting/delete_recycle/cluster_task/chat_tag_user_uploaded/followback_record

## 任务类型枚举(群发核心)
```
taskType=0 普通群发(BulkSend.vue)  9=强制私信(AccountForceSend.vue, letterNum 30/天)
10=群组发送(GroupSend.vue)  群组子类: 拉人 0新好友/1未回复/2所有/9导入好友; 退群 3选择好友
执行链: insertLocal → beginTaskAPI(tuid) → IPC(runTask) → taskthreadPool → AccountChatWorker → TikTok API
pm_message_task 表关键字段: min_interval/max_interval(发送间隔 1-5s 风控)/region(选代理)/run_status(0初始/1运行中/2完成)/repeat_friend
```

## WS 协议 cmd 完整映射(实测)
```
100=发送消息(sendMessage)  603=删除会话(deleteConversationYes)
609=创建会话(createConversation)  610=会话列表/详情(getConversation)
701=删除单条(deleteOne)  702=删除全部(deleteAll)
群组操作(dissolve/leave/addParticipants/createConversationG)同 cmd 不同参数
```

## 风控规避架构(作者方案,复刻照抄)
```
ProxyService: 导入代理 ip:port:user:pass#地区 → pm_proxy_info
IPService: uniqueIdIPMap(账号绑定代理组)/regionIPMap(地区轮换)
SingBoxService: 客户端内置 sing-box TUN 系统级分流(和 v2rayN 同款!)
AccountStatusService: pm_account_status status='违反约束'(违规跟踪)
AccountPlayViolationService: 违规记录(tuid/status/status_msg)
tiktokAPI.unlimit(): 解除聊天限制接口
authAPI.uploadauthkey: cookie 失效检测(「uploadauthkey:失效」)
```

## 管理后台突破(43.130.37.129)
- 域名线索: 客户端源码注释 `backaddress="http://tk_wu.sswhgame.com/api"` → DNS → 43.130.37.129
- 80 端口 = 「智能聊天」Vue 后台(LayUI 风格 SPA)
- API 同源: `http://tk_wu.sswhgame.com/api`(nginx 反代后端)
- 登录: POST /api/user/slogin {account, password, vercode, captchaKey}
- 验证码: GET /api/user/captcha → {img(base64), key} → **ddddocr 自动识别**(4位数字)
- **admin/admin 弱口令直接进后台**(全权限)
- 后台 366 个 API 从 bundle 提取: 账户/任务/GPT智能体/员工/设备全管理
- 上传点 5+: /api/account/uploadFile(需 file[] 参数)/avatar/playData/playAweme/static-ip
  - JSP 单扩展名 400 黑名单; **双扩展名 .txt.jsp 过校验(500 处理错误但未落盘)**
  - /api/upload/ 前缀被 Spring 接管(200 空)— 存储路径存在但文件未写入(后端 bug)

## 关键页面实现速查
- Login.vue(442行): chatlogin(子账号)/stafflogin(员工),登录响应 AES-128-ECB 解密,remember 存 setStore+localStorage
- ChatMain.vue(2560行): 发送= `ipcRenderer.send('ws-send','send',fanJson,lxmsgData)` → worker → TikTok WS
- BulkSend.vue(947行): insertLocal 存任务 → beginTaskAPI → worker 群发
- account.vue(1013行): selectAccountLocal/exportAccount/checkAccountBanned/repairAccount 全走 localRequest
- settings/proxy.vue(569行): importProxyLocal(ip:port:user:pass#地区)/importSubscriptionLocal/checkProxyNetworkLocal
