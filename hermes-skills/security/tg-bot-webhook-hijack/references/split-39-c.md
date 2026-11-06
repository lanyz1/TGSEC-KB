## C 面: 云控面板认族(四族,禁止混打)
| 指纹 | 走 | 不要做 |
|---|---|---|
| `gAAAAA` / `:8000/:8020` / Fernet | Fernet session 解密(本族) | 当 JWT 弱钥结案 |
| 「系统选择」`/tgcloud_pc` `/customer` / OSS STS | tg-cloud-control 扩展(双应用) | 打 Fernet/proxy |
| JWT HS256 `your_secret_key` / `/proxy/list` / `/admin/users` / Session ZIP | **伪造 admin → GET /proxy/list /admin/users → Session ZIP 收明文 2FA** | 打 Fernet/OSS |
| `/main.wasm` + `window.goEncrypt` + 掩码票 | 有头浏览器 oracle + jwt probe | 先逆向 WASM |

- **JWT 第三族顺序**: 手工试 `your_secret_key` → 伪造 admin → `/proxy/list` `/admin/users` 未授权读 → Session ZIP 明文 2FA → 撤权后枚举 `ver/version/v/jti`(五次内复活才报)
- **成功口径 = 可登录 session**,不是手机号/代理条数

