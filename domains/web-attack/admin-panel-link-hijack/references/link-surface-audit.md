# Link Surface Audit

Use before and after a bulk link change. The goal is to know which field actually drives the click and which fields are read-only, derived, or dead.

## Surface matrix

| Surface | Typical field | Editability | Notes |
|---|---|---|---|
| Product | `url` | Usually writable via batch update | The real click target in most H5/nav panels |
| Product | `icon`, `detailImage` | Asset fields | Not redirects; leave alone |
| Classification/ad record | `pid`, `name`, `icon` | `pid` points to product | Often has no own URL; do not invent one |
| Channel | `channelLink` | Often stored or derived; may be labelled bot-maintained | `edit` may return 200 while ignoring it; verify exact value |
| Channel | `entryPath`, `jsonName` | Path/name fields | Can affect generated links; not the product click |
| Channel | `apkPath`, `apkDownloadCode` | APK fields | Not a URL redirect |
| Settings | `WEB_DOMAIN`, `LANDING_DOMAIN` | Shared dependencies | Never repoint to the redirect target as a shortcut |
| Settings | `IMG_DOMAIN`, `IMAGE_DOMAIN_NAME` | Asset prefix/placeholder | `IMAGE_DOMAIN_NAME` is often a dead placeholder; images may use `IMG_DOMAIN` |
| Settings | `LANDING_DOWNLOAD_DOMAIN`, `LANDING_PAGE_PATH` | Landing injector | May be dead; verify file hash, not just API response |
| Client endpoint | `gen_html`, `landing_inject` | Generator/injector | `200` + `data:0` means no file write |
| Entry page | `backRedirectConfig.targetUrl` | Product-derived | Check it separately from product `url` |

## Read and verify

```bash
# Login and keep the token in a file used by subsequent calls.
curl -sS -X POST -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<PW>"}' \
  'http://<BASE>/api/sys/login'

# Read one full object per surface; page/size names differ by panel.
curl -sS -X POST -H 'token: <TOKEN>' -H 'Content-Type: application/json' \
  -d '{"pageNum":1,"pageSize":2}' 'http://<BASE>/api/product/list'
curl -sS -X POST -H 'token: <TOKEN>' -H 'Content-Type: application/json' \
  -d '{"pageNum":1,"pageSize":2}' 'http://<BASE>/api/channel/list'
curl -sS -X POST -H 'token: <TOKEN>' -H 'Content-Type: application/json' \
  -d '{"pageNum":1,"pageSize":20}' 'http://<BASE>/api/classification/list'

# Product tree: useful to confirm every product url in one response.
curl -sS -H 'token: <TOKEN>' 'http://<BASE>/api/classification_product/product'

# Settings: snapshot exact values before any write.
curl -sS -H 'token: <TOKEN>' 'http://<BASE>/api/sys/setting/list'
```

## Batch change and exact read-back

```bash
# Change one row first, then read it back.
curl -sS -X POST -H 'token: <TOKEN>' -H 'Content-Type: application/json' \
  -d '[{"id":<ID>,"url":"<TARGET>"}]' \
  'http://<BASE>/api/product/batch_update'

# Count exact matches in the returned list; do not trust the write response.
```

```python
# After fetching the product list JSON.
target = "<TARGET>"
print(sum(1 for p in products if p.get("url") == target), "of", len(products))
```

## Entry page and static page checks

```bash
# Entry page: count target vs old host; also check backRedirect targetUrl.
curl -sS 'https://<ENTRY_HOST>/entry/<CID>?v=$(date +%s)' -o /tmp/entry.html
grep -o '<TARGET_HOST>/<TARGET_PATH>' /tmp/entry.html | wc -l
grep -o '"targetUrl":"[^"]*"' /tmp/entry.html | head

# Static page: compare hash/size/mtime before and after a generator call.
md5sum /tmp/static.before /tmp/static.after
stat -c '%s %y' /tmp/static.after
```

A generator returning `{"code":0,"data":0}` and an unchanged hash means the endpoint is dead for that page. Do not keep retrying it.

## Bot-maintained fields

When a field says it is maintained by a Telegram bot, verify the bot before promising an edit:

```bash
curl -sS 'https://api.telegram.org/bot<BOT_TOKEN>/getMe'
curl -sS 'https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo'
curl -sS 'https://api.telegram.org/bot<BOT_TOKEN>/getMyCommands'
```

- `getWebhookInfo` with a non-zero `pending_update_count` and `last_error_message: Connection refused` means updates are stuck; a bot-maintained value will not change until the webhook is fixed.
- An empty `getMyCommands` means the bot has no command menu; do not assume a hidden `/setlink` command.
- If the bot cannot update the field, report it as bot-maintained and move on; do not fabricate a change.
