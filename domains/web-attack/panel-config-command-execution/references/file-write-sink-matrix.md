# File-write sink matrix (Chinese Java admin panels)

Use this before building a chain that needs an exact filename (for example a scheduler's `sh -b <name>` first operand). Verify each row against the live target; naming rules differ by build.

| Sink | Auth | Filename control | Content control | Observed behavior / verdict |
|---|---|---|---|---|
| APK upload (`/api/image/upload`, APK content type) | admin | no — `apk/<yyyyMMddHHmmss>.apk` | full file | Stored under the APK root, mode 0644, only when that content type is routed to the local APK root. Usable as `sh <path>` (read-only needed), not as a direct executable. |
| Image upload | admin | no — `upload/<date>/<uuid>.webp` | full bytes | Served from MinIO/CDN; not in the app cwd. The same endpoint accepted a ZIP renamed `.webp` and returned 200, but the bytes were still object storage, not a local packer input. No use for a cwd filename. |
| Video upload | admin | no — `upload/mp4/<date>/<uuid>.mp4` | full bytes | May create a zero-size record / async path; not a cwd file. |
| H5 preload injector (`H5_PAGE_PATH` + `H5_PRELOAD_ENABLED`) | admin | path fixed to `index.html` / `index-hd.html` or a directory | encrypted page ciphertext (hundreds of KB) | Runs repeatedly on a schedule; writes existing page files. The content is encrypted HTML/JS, not a shell script. |
| Landing injector (`LANDING_PAGE_PATH` + `LANDING_DOWNLOAD_DOMAIN`) | admin | `index.html` or a directory only | `window.__STATIC_DOWNLOAD__ = "<domain>";` | A non-index path returns success with `data:0` and no write. Only useful when the destination is an HTML page. |
| Channel JSON (`CHANNEL_JSON_PATH` + `jsonName`) | admin | `{jsonName}.json` | JS array of channel links | Writer may be inactive when the path is empty; the `.json` suffix is fixed. |
| `client/gen_html?cid=` | none/admin | unknown | page render | Returned success without writing in tests; `cid` path traversal did not create a file. |
| APK protect output (`/data/tp/apk-protect-output/`) | read via channel endpoint | server-generated | APK | Read-only; 302 to the channel APK. Not a write. |
| Walle / channel packer | admin | output name from config | copies/injects APK | Operates on the zip in memory; zip-slip entries are not extracted. `package_channel` needs `/data/tp/apk/walle-cli-all.jar`, often absent. |
| Webclip pregen | admin | generated `.mobileconfig` | template + domain | Requires `/data/tp/ios/JPM.mobileconfig`; absent means it fails before signing. |
| Report export | admin | generated `.xlsx` | report data | Server-side workbook generation; no shell. |
| ZIP-slip via any unpacker | — | entry name | entry bytes | Only lands if the unpacker writes entries to the filesystem with unvalidated `../`. Confirm by writing to a web-served path and reading it back. |

## Path-setting join and packer presence

- `BASE_APK`-style settings are joined to a fixed upload root. Read the joined path from `APK母包不存在: /data/tp/upload/...`; a leading `/../../../../` escapes the root.
- The packer binary can be absent (`Cannot run program ... error=2`). Verify it before relying on a zip-slip entry; without the binary there is no extraction/execution point.

## Decision rule

If the target filename is fixed and no row gives exact-name control, stop building the chain and report the missing piece. Do not spend hours trying to rename UUID/timestamp outputs from the app layer.
