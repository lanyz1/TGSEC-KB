# 极融/ARES(cftcredit) 自研 token 变换（已定案）

## 服务端流水线（勿重测）
1. `D = base64decode(seg1)`；token 是 3 段 `seg1.seg2.seg3`，**服务端只处理第 1 段**，seg2/seg3 完全无关（三段矩阵实测）。
2. `out = D 的半字节流左移 1`：丢首 nibble、整体左移、末尾补 nibble 0；逐字节即 `out[i] = (D[i]&0x0F)<<4 | (D[i+1]>>4)`，末字节 `= (D[-1]&0x0F)<<4`。
3. **在 out 前面拼 4 字节服务端常量头**：实测首字节 `05`、第 3 字节 `7A`，第 2/4 字节为非 UTF-8 字节（回显成 U+FFFD ⇒ 服务端自身做过一次 UTF-8 解码）。
4. 把 `常量头 + out` 当 JSON 解析；失败即 `500 {"message":"The string '...' doesn't have a valid JSON format"}`。
5. 技术栈：Nimbus JOSE JWT（3 段）+ Fastjson 1.x。

## 长度律（严格）
`len(out) = n`（`len(D)%3==1`），否则 `n-1`；等价判据 = seg1 是否以 `==` 结尾。

## 逆变换（自查用）
`S = (int.from_bytes(P,'big') << 4) | 2` ⇒ 服务端 out = `P + 0x20`（尾空格，JSON 合法，避开 Fastjson 拒尾随 NUL）。

## 判定：seg1 伪造路线已死
常量头不可控，且已逐项证伪来自 seg2/seg3、请求 body、Authorization scheme、请求路径、环境差异 ⇒ parse 目标永远带垃圾前缀，**任何 seg1 都无法让 parse 成功**。
- **禁止重复 nibble-swap / CTR / RC4 / 压缩编码 / 长度律复测这一系**（曾连烧十几轮，全无产出）。
- 要拿真实构造算法只能从前端 JS/APK 侧取。

## 免鉴权面（已确证）
- `/mobile/crm/online/*` —— **整个命名空间 8 个端点全部免鉴权**：
  - `GET /mobile/crm/online/get_key/{key}`：**键值读取原语**（真实 KV；未命中返 `data:null`，null 是查询结果不是"接口无效"）
  - `GET /mobile/crm/online/question-info/{qid}`、`POST /mobile/crm/online/question/{...}`、`POST .../self-service/{mid}/{service-code}`、`POST .../split-service-url/{mid}`
- `/api/h5/credit/item/enum`、`/api/h5/certificate/item/enum`：免鉴权返业务枚举（含企业实名类数据）。
- 写原语面：`/api/h5/credit/save`、`/api/h5/certificate/save` 的 `upPath` + `name` 是 **query 参数**；`/api/h5/credit/upload` 是 multipart（`mid`/`type` 必填 + 文件字段）。
- 接口清单：Swagger 实测 369 path / 339 POST。

## 主机面
- 生产/预发：`al-h5.geerong.com`、`al-h5.cftcredit.com`（H5 API 主面）、`api.geerong.com`、`preprod.geerong.com`、`loans.cftcredit.com`、`jiakah5.cftcredit.com`、`af.geerong.com`、`fingate.geerong.com`、`cdnzd.geerong.com`、`apk.geerong.com`
- 测试：`loans-test1.cftcredit.com`、`loans-test2.cftcredit.com`、`la.cftcredit.com`
- ★ 测试环境 KV 为空（`get_key` 扫 70 键全 null）⇒ 原语判定必须换生产面重放。
- 其他上下文：平台代号 ARES、框架 LYRA、厂商 `com.fincloud.privilege`/cftcredit、App 包名 `com.niwodai.finance.apppack`。

## 红线（该目标长期约定）
零爆破口令、零破坏性写（上传类只验功能）、不批量下载个人数据、不做短信触达（`sendSmsCode`/`getVerifySms`/发券/发合同类端点一律不碰）、凭据与会话 ID 不回显。
