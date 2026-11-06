# 比特浏览器（BitBrowser）扩展采集路线（2026-08-29 PoC）

设备农场/多账号采集的新形态：把采集逻辑做成 **MV3 Chrome 扩展内置进比特浏览器窗口**。
窗口内嵌扩展 → hook 页面网络层拿 item_list → 登录态天然（窗口里就是登录态）→ 直传平台 sync API。
对比 iOS 设备农场：零 App 开发、指纹/IP 由窗口自带、无跨机器 CDP 问题（扩展跟着窗口走）。

## 比特浏览器 Local API（控制窗口的入口）
- 软件设置 → Local API（本地接口）→ 开启（localhost 服务，记 url+token）
- 关键接口（全部 POST，body 传参，success:true 为成功）：
  - `POST /health` 健康检查
  - `POST /browser/update` 创建/修改窗口：指纹对象必传（空 {} = 随机）；代理字段 `proxyMethod/proxyType(支持 'noproxy','http','https','socks5','911s5')/host/port/proxyUserName/proxyPassword`
  - **`POST /browser/open {id}` → 返回 `data.http: '127.0.0.1:50106'` = CDP 调试地址 + `data.ws` = devtools ws** —— 不需要手动配 debug port！API open 即返回
  - `POST /browser/close {id}`
- 文档：https://doc.bitbrowser.cn/api-jie-kou-wen-dang/liu-lan-qi-jie-kou（含无头模式指南）

## MV3 扩展架构（TikFlow 采集助手 v0.1，实测语法/打包通过）
```
main.js      (MAIN world) hook window.fetch + XMLHttpRequest → 匹配 /api/post/item_list/（排除 prefetch）
             → JSON.parse itemList → window.postMessage({source:'tf-hook', ...})
content.js   (ISOLATED) 收 postMessage 去重收集(Map by id) → 滚动 scrollBy(0,1400)/1.1s
             判停：item_list 响应数连续 5 轮无增长(最多 40 轮) → 收集完 mapVideos() → sendResponse
background.js 收 popup collect → chrome.scripting.executeScript({files:['main.js'], world:'MAIN', injectImmediately:true})
             → chrome.tabs.sendMessage(content 'start') → 收结果 → fetch 上传 sync API（background 无 CORS）
popup.html/js 显示当前 tab handle(URL /@xxx) + 同步码输入(chrome.storage 记住) + 开始按钮 + 进度
manifest      permissions: storage/scripting/tabs; host_permissions: https://*.tiktok.com/* + https://tiktide.com/*
```
关键实现决策：
- **executeScript world:'MAIN' 放 background**（background 有 tabId；content 里拿不到干净的 tabId）——不要在 content 里调
- **上传放 background**（content 的 fetch 受页面 CORS 限制；background fetch 无 CORS）
- 作品字段映射与 tk_ck_gui 一致：`video.cover` 字符串 URL(或 originCover) → coverUrl；videoUrl 构造 `https://www.tiktok.com/@handle/video/<id>`；stats playCount/diggCount/commentCount/collectCount
- 真实作品数：读 SSR `__UNIVERSAL_DATA_FOR_REHYDRATION__` 的 user-detail stats.videoCount
- 安装：比特窗口 chrome://extensions → 开发者模式 → 加载已解压；扩展产物目录 `C:\Users\Administrator\Desktop\ttck\extension-tikflow\`（zip: TikFlow采集助手_v0.1.0.zip）

## 待验证点（PoC 未闭环）
- 登录态主页 item_list 是否触发（游客模式实测触发；登录态此前在服务器端测试"不触发"——扩展里 hook+滚动实测待做）
- hook 不到时的兜底：DOM 提取作品卡片（拿 id/封面，stats 缺失）

## 与 iOS 设备农场的取舍
- iOS：无越狱 + WiFi 代理 127.0.0.1 被忽略 + 单 VPN 限制 → 手机端手动抓包死路（见 ios-ck-capture skill）；正解=企业签名 App 隧道
- 比特窗口：Windows 真实环境 + 每窗口独立指纹/独立代理（可 socks5）——轻量、可批量、可下发客户
- 采集触发形态：用户在窗口登录账号 → 打开自己主页 → 点扩展图标 → 填同步码 → 采集上传
