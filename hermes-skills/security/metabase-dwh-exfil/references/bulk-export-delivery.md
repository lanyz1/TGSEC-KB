# 大文件交付（Telegram 50MB 限 + GoFile 直链）2026-10 实证

## 通道选择

| 规模 | 通道 | 要点 |
|---|---|---|
| ≤48MB | Telegram 直发（MEDIA:path） | 实测 48MB 过（50MB×1024×1024=52,428,800B 为 Bot API 上限）；63MB 被拒（Request Entity Too Large） |
| 大文件 | GoFile 网盘直链 | 匿名可用、快（~14MB/s）、返回服务器侧 MD5 |
| 批量分片 | `hermes send` 脚本循环 | CLI 直接推，可后台跑，收尾发清单 |

## GoFile 上传（两行 curl）

```bash
SRV=$(curl -sk https://api.gofile.io/servers | python3 -c "import json,sys;print(json.load(sys.stdin)['data']['servers'][0]['name'])")
curl -sk -F "file=@<path>" "https://$SRV.gofile.io/contents/uploadfile" -o resp.json
# resp.json -> data.downloadPage (https://gofile.io/d/XXXX) + data.md5 + data.size
```
- **服务器返回 md5 与本地 md5sum 对账**——交付消息里写「MD5 已核对一致」
- 页面上点 Download；免费档文件长期不取会被清，提醒用户尽快转存
- 小文件验证流程：先传一个 1-2MB 文件跑通再传大包

## Telegram 分片推送脚本（hermes send）

```python
r = sh(f'hermes send --to telegram:<chat_id> --json "MEDIA:{part}"')
if '"success": true' in r.stdout: ok
else: retry ×3 (sleep 15); 全部失败标记 GAVE UP 并继续
sleep 4  # 片间间隔，防 flood
```
- `hermes send`：`--to telegram:<chat_id> "MEDIA:/abs/path"`；`--json` 给机器可读结果；成功返回 message_id
- **片大小用 48MB**（`split -b 48M -d --additional-suffix=.part src out-`）；末片会偏小很正常
- 收尾自动发合并清单消息（`cat out-*.part > full.zst` + 解压命令 + 整包 MD5 + 内容清单），用户不用问
- 用户对「下载链接」类交付明显偏好：**能直链就别让他装工具**（先问怎么打开 → 要下载链接）

## 聊天内大文件的使用说明（写给用户）

- `.tar.zst`：7-Zip 解两次（先出 .tar 再解）；Mac/Linux `zstd -d` + `tar -xf`
- 内含 `.csv.zst` 分片时：逐个 zstd 解出 CSV
- 大 CSV（百万行）别用 Excel（卡死/104 万行上限）：推荐 DuckDB（单文件免安装）或先导 SQLite；小表 Excel 导入时编码选 UTF-8
- SQLite 库（.db）：DB Browser for SQLite（免费 GUI）

## 交付消息模板要素

文件清单+行数 → 解压/合并命令 → MD5 → 过期提醒 → 「缺什么说要哪份单独出」
