# 云数据库备份桶（DBS）离线脱库 —— Parquet 直读

来源：2026-09 灰豚/央选族（阿里云 DBS 表级备份桶 `dbs-backup-*`）。
适用：任何把**数据库表级导出**丢进对象存储的备份（阿里云 DBS、自建 mysqldump→OSS、S3 上的 parquet 湖）。

## 1. 怎么认出来

- 桶名：`dbs-backup-<阿里云账号ID>`（数字段 = 主体账号，可直接用于归属核实）
- 对象键全貌（5 段，**`datamove` 不在桶根下**）：
  ```
  <rand>/<full|incr>/<快照ID>/datamove/<库名>/<表名>/<分片号>
  ```
  `datamove/` 段就是「逐表导出」的库表快照；问同一个快照 ID 下的对象即一次备份快照全集。
- **★ 桶根全量列举纪律（本文件最重要的一条）**：
  ```python
  # 对，桶根全量列举后按 / 切段聚合
  tabs = {}
  for o in oss2.ObjectIterator(bk, prefix="", max_keys=1000):
      p = o.key.split("/")
      if len(p) >= 6 and p[3] == "datamove":
          tabs.setdefault((p[4], p[5]), []).append((o.key, o.size))
  ```
  **不要用 `prefix="datamove/"` 或任何想当然的短前缀去筛** —— 该前缀在桶根下匹配不到对象，
  结果是**静默少给几十上百张表**：同一个桶，短前缀口径只拿到 24 表 / 8.5 MB，
  桶根全量口径是 **130 表 / 3,599 对象 / 7.7 GB**。
  漏表的代价是「全库」结论直接错，且不会被任何报错提醒。
- **分片 ≠ 完整**：大表切成上千片（`<表>/0`、`/1` … `/1437`），按表聚合必须**求和**，别只取 `/0`。
- **0 字节对象 = 该表在该快照为空**（不是下载失败）：给空 CSV 并标注，别当缺件重试。
- 同族兄弟桶：`*-sql-dump`、`*-order-filie`（拼写错别字也照抄）、`*-bak`、`*-export`、`*-archiving`
  （后者的常见顶层前缀：`ob_data/` 订单库、`all_bak/` 历史归档、`sls_log/` 日志服务归档、`pc-*/` PolarDB 备份）。

## 2. 一次列举就能回答「全库能不能拿」

全量列举后立刻算出并写进交付：

| 指标 | 算法 | 用途 |
|---|---|---|
| 表数 / 对象数 / 总字节 | 按 `(库,表)` 聚合 | 回答"能拿到多少"，规模数字只用清单口径 |
| 每表分片数 | `len(keys)` | 识出订单/日志类大表（上千片） |
| 空表清单 | `size == 0` | 提前排除，报告里如实标注，不假装有数据 |
| **快照日期** | 对象 `LastModified` + 库内 `max(add_time/last_time)` | **新鲜度**，见 §6 |

## 3. 直接读，不要连库

Parquet 是**自描述列存**：`pyarrow.parquet.read_table(p).to_pylist()` 即可，无数据库、无凭证、无线上流量。

- **丢掉 DBS 内部列**：每行都有 `_##alibaba_dbs_parquet_id##_`（分片内主键/行号），导 CSV 前必须剔除，否则污染表头。
- **★ 本机解析优先**：目标侧跳板机常年装不上 pyarrow/依赖（PEP668、无外网、pip 超时）——
  把表 SFTP 拉回本机解析**更快更稳**；跳板机只负责取 STS 签名 + `get_object_to_file`。
- **只拉需要的表**：先 `head_object(k).content_length` 过滤，>100 MB 的按需再拉。
- 拿到表先打 `t.num_rows` + `t.column_names` 再决定下探哪张 —— 列名就是"该表有什么机密"的地图。
- 时间戳列多是 **10 位秒级字符串/整数**（`add_time` 类），换算 +8 小时才是平台本地时。

## 4. 表名分类地图（用户点名的业务三类）

使用者常按业务面点名取数（"商户客户 / 达人主播 / 协议合作 全量给我"），按此归类直接取：

| 业务面 | 表 | 最值钱的列 |
|---|---|---|
| **商户客户** | `merchant_info` `merchant_cate` `merchant_right` `merchant_enroll_log` `merchant_trade_info` `shop_info` `shop_rule` `brand_info` `brand_dy` `mcn_info` `institute_info` `channel_info` `trade_info` `open_info` `selection_*` | `merchant_mobile` / `contact_mobile` / `wechat` / `merchant_passwd`(md5) |
| **达人主播** | `anchor_info` `anchor_info_backup` `anchor_day` `talent_info` `talent_cate` `talent_cate_industry` `talent_tag` `talent_right` `open_anchor_relation` `open_dy_anchor_relation` `open_authentication` `twitter_info` `promoters` `video_info` `live_info` `live_product` `tag_info` | `contact_mobile` / `contact_name` / **`access_token` / `refresh_token`**(第三方授权凭证) |
| **协议合作** | `protocol_info` `protocol_option` `protocol_log` `protocol_proof` `protocol_material` `protocol_live_info` `agreement_info` `sample_order` `sample_order_product` `cost_sample_product` `tender_info` `tender_cate` `invitation_info` | `merchant_id × talent_id × order_sn` **关系边**（比裸号码值钱）+ `sample_order` 37 列寄样全链 |
| **订单/资金**（常被要求追加） | `order_dy` `order_ks` `dy_order_history` `order_product_*` `product_*` `sku_*` `commission_*` `pay_info` `gmv_*` `refund_*` `transfer_account` | 金额、分账、结算 |
| 后台/审计 | `admin_user` `admin_role` `admin_node` `admin_operate_log` `admin_user_role` | `user_name` / `salt` / `password` / `login_ip` / `token` |

- 实测锚点（该族快照量级）：总 55 表 / **1,200,615 行**，最大表 `anchor_day` 55 万行、`talent_tag` 28.6 万行、`orientation_plan` 14.5 万行、`protocol_info` 2.1 万行。
- 快照里的空表是**真为空**（本轮 6 张：`brand_dy` `institute_info` `mcn_info` `merchant_enroll_log` `protocol_data` `tender_survey`），别把空表当成"没拉下来"。
- `contact_mobile` 可能**全空**而 `contact_num` 全为 `0` —— 别急着结论"没有联系方式"，
  把同一业务域**所有**表拉下来横向比对（本轮 `anchor_info` 全空，真值在 `talent_info` / `merchant_info`）。
- **跨表去重 + 交叉命中数**要一起报：交叉命中（同一号码出现在 ≥2 张表）是**号码有效性的自证**。
- `*_backup` / `*_his` / `*_log` 是旧快照，与现表有差集 → 历史数据补全的另一半。

## 5. 口令字段结构速判（决定爆不爆）

| 形态 | 判据 | 处理 |
|---|---|---|
| 有独立 `salt` 列 | 多半是 `md5(salt . md5(pwd) . salt)`（PHP `genPassword` 家族） | 按公式重算，靶向小表即可 |
| 32 位十六进制、**无** salt 列 | **无盐 md5** | 直接与候选表比 md5 值，一条 `e10adc3949ba59abbe56e057f20f883e`(=`md5("123456")`) 采样即可秒判 |
| `$2y$` / `$argon2` | 慢哈希 | 记录形态，别浪费算力（除非业务要求） |

- 靶向几十条候选词（公司名/品牌拼音/常见弱口令）在本地毫秒级跑完 —— **不属批量爆破**，随时可停；
  命中率实测：无盐 md5 商户 7.2%、达人 14.0%（`123456` 占绝大多数）；加盐后台 4/13。

## 6. 归档存储类 = 解冻门（先查再计划，别撞上去）

```python
h = bk.head_object(key)
h.headers.get("x-oss-storage-class")   # Standard / IA / Archive / ColdArchive
```

- `Archive`/`ColdArchive` 的对象 **GET 会回 `InvalidObjectState`** —— 不是权限问题、不是键写错；
  必须先 `RestoreObject` **解冻**（取回后按容量计费、不可逆、有最小计费时长）⇒ **属于需要用户明确点头的动作，不要默默发起**。
- 同一账号内逐桶/逐前缀查，**存储类常混着放**：实测 `dbs-backup-*` 是 Standard（可直读），
  同族 `*-order-filie/<实例>/ *.sql.gz`（94 个 / 11.9 GB）是 **Archive**（拦在解冻门上）。
- 报告里把"可直读"与"需解冻（未执行）"分成两栏写，别合成一句"已具备访问"。

## 7. 回本机管线与交付形状（用户说"拉到本地 X 盘"时照这个做）

1. **目标侧只下载**：跳板机取 STS → `get_object_to_file` 到 `/root/<工作区>/<分类>/<表>/<分片>`，逐个报成功/失败数。
2. **SFTP 拉回本机**：按**目标文件 size 匹配**做断点续传（size 相同即跳过），
   小体量（几十 MB）常十几秒完成；耗时用**时间预算 + 打印剩余**，别一次调用里硬等。
3. **本机解码**：`pyarrow` 逐分片读 → 去内部列 → 写 `utf-8-sig` CSV（Excel 直开不乱码）。
   多分片的表命名 `<表>_part<n>.csv`，单分片 `  `<表>.csv`。
4. **附属交付**（每次都要，别只丢一堆 CSV）：
   - `db_full_索引.csv`：分类 / 表名 / 行数 / 列数 / 原始字节 / 分片数
   - `db_full_说明.md`：**来源桶 + 完整对象键前缀 + 快照 ID + 备份上传日 + 库内最新业务时间 + 行数合计 + 空表清单 + 敏感字段提示**
5. 路径按用户当次指定（"拉到本地 d 盘" ⇒ `D:\渗透\<目标>_recon\` 下 raw + csv 两份），报告副本另落交付目录。

## 8. 判据纪律

- **备份桶是旁路**：业务接口修好了也没用 —— 报告里必须**单独列一条 P0**
  「备份桶独立账号 + KMS 加密 + 生命周期回收」，否则修复建议等于没写。
- **快照 ≠ 实时**：交付里必须写清截止日期。实测该族备份上传 2023-07-31、库内最新业务时间 2023-07-30，
  比当前晚三年 ⇒ 回答"能不能拿下全部数据"时给**「快照全量 + 增量缺口」**两句，增量另走 `*-sql-dump` 归档或后台导出接口。
- **「到今天的最新数据」只有一条路：现网应用层**（后台列表页/导出接口、免鉴权业务接口）。
  备份桶再怎么挖都是快照 —— **两条通道要在交付里分行写出各自的「数据时间」**：
  备份侧用 `LastModified` + 库内 `max(time)`；现网侧用页面自带日期自证（统计页最新统计日 / 列表页最新记录 / 管理员最后动作时间）。
  用户追问「没有最新的吗」时，答案不是「备份里没有」，而是**切到现网通道去打**（打法见
  `lowcode-admin-data-exfil/references/live-admin-list-and-export-harvesting.md`）。
- **"已收敛"必须逐入口复测**：本轮实测同一平台，业务侧老入口 5 天内已 401/500，
  而**零鉴权 STS 入口一字未改、仍可领凭据** → 一次复测就能证明"对方只堵了公开过的洞"。
- 备份桶里的表常含**全量第三方授权 token**（`access_token`/`refresh_token`）：
  这是"数据面之外的第二份凭据库"，影响面要单列。
- 交付：CSV 一律 `utf-8-sig`（Excel 直开不乱码），表头用中文业务列名，附一份 `unique_*.json` 去重底表。
