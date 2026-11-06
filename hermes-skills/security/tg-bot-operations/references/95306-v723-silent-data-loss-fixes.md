# v7.23 静默丢数据修复实录(bot 侧,2026-08-30)

## 1. 搜索拆词(用户实测痛点:"沈阳82"/"武汉局69次" 搜不到)
纯子串匹配 `k in name` 对"路局名+次数"组合输入全部 0 命中——名称是"沈阳铁道工业集团有限公司2026年第82次废钢轨物资处置项目",不含连续子串"沈阳82"。
修复:拆词 AND 匹配
```python
tokens = [t for t in re.findall(r'[\u4e00-\u9fa5]+|\d+', k) if t]
if not tokens: tokens = [k]
hay = f"{name}{code}{pid}".lower()
if all(t in hay for t in tokens):  # 命中
```
效果:"沈阳82"→3 命中(live 优先);"武汉局69次"→3 命中(之前 0)。
注意:数字 token 可能误命中 projCode 里的数字(如"西安69"命中 64 次项目,因 code 含 69)——可接受,排序后 live 优先。

## 2. 搜索排序反转(live 排到最后)
`hits.sort(key=lambda x: (0 if live else 1, bidStarttime), reverse=True)` — reverse=True 把 0 组(live)放最后!
正确:key 里 live 给大值 `(1 if live else 0, bidStarttime)`,reverse=True → live 组先、组内时间倒序。

## 3. sub_checker 读错路径(竞价状态推送从未触发)
`json.load(open(os.path.join(POOL, "bid_status.json")))` — bid_status.json 在项目目录 `POOL/<pid>/bid_status.json`,根目录文件不存在 → bs 永远空 → 竞价开始/结束推送永不触发。
修复:os.path.join(POOL, pid, "bid_status.json")。**教训:推送/状态类代码的路径要用与写入端完全一致的拼接,写完 grep 一遍所有读文件路径。**

## 4. 审核首推抑制
`if old_st and st and st != old_st:` — 旧状态空(首次出现审核结果)不推 → 审核通过静默。
修复:`if st and st != old_st:` — 空→有 也推(首次审核结果值得推);有→空 不推(避免误报)。

## 5. 包件清单去重字段优先
merger 按 packCode 去重先到先得 → 缺字段版本(某台采集机解析失败)覆盖全字段版本。修复:按字段完整度择优(保证金/时间非空者胜出),相同则保留先到。

## 交叉引用
- 采集侧 10 项检查清单:auditlog-ticket-harvesting/references/95306-session15-st-dead-tickets-collector-fixes.md
- daemon/systemd 根治:remote-daemon-ops/references/systemd-daemon-root-fix.md
