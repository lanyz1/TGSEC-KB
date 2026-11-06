# 换树/换版时「老代码兜底分支」丢失 ⇒ 静默空值

## 症状
列表页日期列**整列空白**（`📅 | 🏢0家`）：不报错、不抛异常、日志干净，只有上真数据才暴露。

## 根因
新树 `bot/pool.py::proj_pub_day()` 只保留两条取值（`pubtime 表` / `info["publishTime"]`），
而老正本 `pix_bot_server.py:1019` 还有第三条兜底：
`re.search(r"0020(\d{6})", projCode)` ⇒ `%y%m%d` → `%Y-%m-%d`。
真池里 `/data_pool/publish_time.json` **根本不存在**（pubtime 恒空）⇒ 两条全落空 ⇒ 静默返空。

## 铁律
1. **换树/重写取值链时，老代码的每个 `or` / fallback 分支都要逐条搬**，不许按"看着够用"收口。
2. **上产前必须在「未割接的新树」上跑实渲染探针**（`tools/_probe_style.py` 指向新 `lib/v6rel_*` 目录；远端 sed 换 TREE 后跑）：先验后切，才能在上线前抓到这类静默空值。
3. 补值时**顺带接权威源**：`/data_pool/plat_enroll_map.json` 每项带 `公告日`（实测 612/612 全有，按 projCode 命中 409 项）。优先级：
   ① pubtime 表 → ② 平台权威「公告日」 → ③ `info.publishTime` → ④ `projCode` 里 `0020(\d{6})` 反推（可覆盖 12,507 项）。
4. **一次读盘、逐项复用**：`plat_enroll_map.json` 437KB，`page_out` 里 `pe` 只读一次再传参
   （`proj_pub_day(pid, info, pub, pe)` / `proj_plat_ent_count(pid, info, pe)`），别逐项重读。
5. 补不齐的项**安全返空、绝不编数据**，并如实报残留比例（本例 2/16 空白，与老正本同一口径）。

## 单测
`tools/_probe_pubday.py` —— 7 档：四源优先级 + 平台公告日优先于码推 + 列表切片 `[5:16]` ⇒ `MM-DD`。

## 验收口径（本例）
修复后实渲染列表：`📅08-18 / 08-19 / 08-20 / 08-25 / 08-31`（老格式 `MM-DD`）；
`当前 → v6rel_20261005ae`，线上 `menus.py`/`pool.py` sha 与本地**逐位一致**。
