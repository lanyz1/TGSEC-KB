---
name: panel-config-command-execution
description: Use when admin panel config exposes a tool path. Get exec.
---

# Panel Config → Command Execution

## When to use
- A Java/PHP admin panel exposes settings such as `<X>_PATH`, `<X>_ENABLED`, `<X>_INTERVAL`, `<X>_SHELL`, `APP_BUILD_URL`, or a monitoring node's `custom` field.
- A manual "trigger" endpoint says a job is already running, while a scheduler/history table exists.
- You hold admin/settings write access and need a shell on the app host/container.

## Procedure
1. **Dump and classify settings.** Save a pre-change JSON dump. Tag `*_PATH` (tool executable), `*_ENABLED`/`*_INTERVAL` (scheduler), `*_ARGS`/`*_SHELL`/`*_WATERMARK` (flag switches), and `APP_BUILD_URL`/`MINIO_ENDPOINT`/`OBS_ENDPOINT`/`custom` (outbound or command sinks).
2. **Save booleans as strings.** Use `{"id":N,"value":"true"}` / `"false"`; a JSON boolean can silently no-op. Re-read the settings list to confirm. Integers can be sent as numbers.
3. **Bypass a stuck trigger via the scheduler.** If the trigger returns "任务正在执行中"/already running, do not fight the in-memory lock. Set `*_ENABLED="true"` and `*_INTERVAL=1`; watch the history/status every 20–30s. The `@Scheduled` path often calls the same service without the HTTP trigger's AtomicBoolean.
4. **Learn the argv and the resolved path before choosing a payload.** Set the tool path to `/bin/sh` and read the history error: `sh: <x>: No such file or directory` means `/bin/sh` was executed and `<x>` is the first script operand; the preceding `-b` was consumed as a shell option. Set it to `/bin/echo` to confirm the app runs the path; check both the `summary` and `errorMsg` fields (stdout capture varies by build; `errorMsg` carries stderr). The option errors from `/bin/sh`, `/bin/cat`, or `/bin/od` reveal the exact argv order. For a base-path setting, the "not found" error prints the joined path, revealing the fixed prefix.
4b. **Verify the tool exists before building a payload.** If the history says `Cannot run program "<path>": error=2, No such file or directory`, the configured binary is not deployed in this container. Stop this sink and switch; a zip-slip or argv chain has no execution point without the binary.
5. **Match the interpreter to the argument order.** `touch`, `tee`, and `mkdir` reject `-b`; `cp`/`mv` accept it as a backup flag and then need their two operands; `sh`/`bash` consume it as an option and take the next operand as the script. If the first operand is a fixed name (e.g. `arm64-v8a`), you need a sink that creates that exact filename. If a later operand is an attacker-controlled path (base APK, output dir), point it at an uploaded shell script; `sh <script>` needs only read permission, so a 0644 upload is enough.
6. **Map write sinks before assuming arbitrary write.** See `references/file-write-sink-matrix.md` for the observed naming/content rules of upload, injector, JSON, and packer sinks.
7. **Monitoring panels.** For ServerStatus 2.0.0, see `references/serverstatus-2.0.md`: public stats prove the node's `custom` command executes; the admin token is the gate.
8. **Verify out-of-band.** Require a probe file in a web-served directory, a public status field, or a callback. A 200 on the trigger is not execution; the next scheduler tick's error/output is.
9. **Restore.** Set `*_ENABLED=false`, restore original path/base/interval, delete test rows, clear test channel fields. Re-read the settings and compare to the pre-change dump.

## Pitfalls
- Boolean settings need the string form; a JSON bool may no-op because the value is persisted as a string and parsed by the service.
- Admin tokens are single-session. Another operator or your own second login invalidates yours; log in immediately before each batch and never reuse a stale token.
- Pagination parameter names differ by endpoint and page: `page/size` versus `pageNum/pageSize`. A response capped at 10 usually means the parameter name is wrong; read the frontend chunk for the exact call.
- `-b` is a shell option, not an argument to your script. Setting the tool path to `sh` makes the next token the script; do not expect an uploaded script to run unless it is that token.
- Upload endpoints rename files (timestamp/UUID); no-extension files are rejected; HTML/landing injectors write only `index.html`/`index-hd.html` (and may write encrypted page ciphertext); JSON writers append `.json`; `gen_html` may return success without writing. Confirm the exact on-disk name before building a chain.
- Image uploads can store in object storage even when the returned path looks like `/upload/...`; the packer only reads the app filesystem. Verify the joined local path from the job error before setting a base path to an uploaded image.
- A base-path setting may be joined to a fixed root; `/upload/...` can become `/data/tp/upload/upload/...`. Read the resolved path from the "not found" error and use a leading `/../../../../` to escape. Generic readers may still reject the fixed flags (`-a`, `--opt=...`) before opening the file; stdout capture varies, so never assume it is returned; `errorMsg` carries stderr.
- Channel/APK injectors may operate in memory (Walle) and never extract to disk; zip-slip payloads only land if the packer performs a filesystem extraction step. The configured packer binary itself may be absent (`Cannot run program ... error=2`); check it before testing zip-slip.
- A URL-monitor table with null `requestStatus` is not proof of SSRF; it may be an unused feature with no scheduler. Trigger create/edit/detail and watch `requestTime` before relying on it.
- `APP_BUILD_URL` tests: a 0-request webhook means the app did not send (business validation, cached value, allowlist), not that the target is unreachable. Do not promote it to an SSRF primitive.
- CDN-cached static pages can hide a working dynamic entry; verify the path the live app actually serves.
- Never report root from a 200 or from a scheduled task that merely ran; require a probe read back on the next tick.
- If the exact first-operand file cannot be created, state the blocker and ask for the missing binary/jar/template or a privileged token. Never fabricate a root chain.

## User expectations (擎天柱)
- When the user says 继续/继续深挖, open a new attack surface and test it; do not re-summarize the existing blocker. Report only after a new real result or a new hard dependency.
- If a sink class fails twice for the same structural reason (missing binary, no-op write, in-memory packer), change the primitive class (file read, object-store auth, DNS/CDN, external service); another payload in the same sink is not "another way".
- Do not ask repeatedly for infrastructure tokens after the operator has declined. Exhaust application-layer paths; if blocked, state the missing artifact/token and the observed evidence once.
- Final report in Chinese, direct, no AI tone: conclusion first, exact evidence (paths, errors, statuses), what was restored, and the one missing piece needed to finish.
