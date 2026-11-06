## ⚠️ pack_map schema 契约(写前必读)

任何通道写 pack_map.json 必须用 collector 兼容 schema,否则 bot 读不到(曾致 79 家补漏数据消失):
```json
{"enterprises": {"<账号key>": {"账号": "x", "用户": "", "单位": "全称", "ST": "", "时间": "YYYY-MM-DD HH:MM:SS",
  "来源": "collector|backfill8|01三态+映射链", "包件": [{"packId": "uuid", "packCode": "004", "packName": "",
  "保证金": 0, "报价模式": "单价", "物资条数": "1", "审核状态": "未审批|通过|拒绝", "审核码": "00"}]}}}
```
- bot 读 `ev.get("包件")`(list)+ `pk.get("审核状态")`;审核统计/企业明细/18列CSV 全依赖它
- key 用账号(历史导入 key=单位名 → merger 归一);同单位多账号展示层 merge_ents_by_unit 合并
- 审核状态字段 = getBuyPackageList 的 bidderCheckStatusName(00=未审批);data 直接是 list 不是 {result}

