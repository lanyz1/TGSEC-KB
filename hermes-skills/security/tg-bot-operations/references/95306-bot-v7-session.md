# 95306 Bot v7 会话沉淀(2026-08-29)

## 企业名归一化(dwhz 简称 → 官方全称)

**根因**:实时采集企业名来自 `user/info` 的 `dwhz` 字段(企业注册 95306 时自填,可简称如"河南凡欧"/"嘉楠兴"),供应商主数据(369,710 家,官方企业库)是工商全称。

**实现**:
```python
# merger 侧(数据落盘层,O(1) 缓存)
_NAME_MAP = None
def _norm_ent_name(n):
    global _NAME_MAP
    if _NAME_MAP is None:
        _NAME_MAP = {_norm_key(fn[:-5]): fn[:-5] for fn in os.listdir(SUP_DIR) if fn.endswith(".json")}
    return _NAME_MAP.get(_norm_key(n), n)  # 只做精确核心名匹配

# bot 侧(展示层,含包含匹配兜底)
def norm_ent_name(name):
    # 精确匹配核心名 → 失败后包含匹配(key in fk or fk in key, len>=2)
```

**同账号合并 + ?修复**:`acct_name[账号] = 最长名`;`?` 单位用账号补全;同账号 pack_map 记录合并(包件按 packId 去重,保留最新时间)。

**全量整理脚本模式**(pool_clean.py,13K 项目 4 秒):
1. 构建 `{核心名: 全称}` 映射(369K 供应商文件名)
2. 遍历 /data_pool/*/pack_map.json:改名统计/账号合并/?修复 → 写回
3. 重建 /data_pool/企业档案/(遍历全部 pack_map 聚合 + 旧档案合并,记录保留 20 条)
4. index 一致性:index 项目数 vs 36 字符文件夹数

## 数据池分类管线(classify_all)

merger 每轮合并后调用,写 /data_pool/分类/:
- `按路局.json`:bureau_of 正则 `([\u4e00-\u9fa5]{2,8}局)` 兜底公司名
- `按物资.json`:关键词优先序列表(废钢轨在废钢轨物资前;含 废电子电器 在 废电子 前)
- `按状态.json`:live 读 `{pid}/bid_status.json` 的"状态",历史用 status 码(14=已结束/22=流标)
- `按时间.json`:bidStarttime 前 10 位,今日/明日/未来7天/本月/历史
- 每类条目 {pid,name,code,bid,packs,ents,live},按 bid 倒序,每类截 500
- bot 回调链:`cat`(总览)→ `cat:<dim>`(子菜单带数量)→ `catopen:<dim>:<key>:<page>`(8/页)

**踩坑**:merger.py 顶部没有 `import re`,文件后部加的函数用 re → `NameError: name 're' is not defined`(bot 同样踩过,顶部补 `import re`)。

## 补采包件(collect_one.py --pid 模式)

- 公告查找:**先 notTitle=项目名前20字**(读 /tmp/targets/<pid>/项目信息.json 的 projName)→ 翻 3 页匹配 projId
- 找到公告 → readNoticeInfo → 正则解析包件 + 同步存公告全文.json
- bot:"🔄 补采包件"按钮(repack:<pid>,异步线程)+ 管理员 /repackall(repack_missing 找缺包件 live 项目,串行每个 ~15s,上限 30 个)
- 实测:29 个缺包件项目全部补采成功;补采后 merger 下一轮自动拉回主服

## 其他本会话修复

- 竞价提醒:sub_checker 里 `0 < delta <= 15*60` 且未提醒过(prev.get("reminded15"))→ 推"竞价即将开始"
- 深链:`t.me/pixshujubot?start=proj_<36位pid>`,handle_text 解析 `/start proj_xxx`
- 真 xlsx 零依赖:zipfile 手写 [Content_Types].xml/_rels/workbook.xml/worksheets/sheet1.xml(inlineStr 单元格)
- 每日备份 daemon:backup_checker 每 30min 检查 04:00,打包 index/health/汇总 + live 项目文件夹 → /backup/,保留 7 天
- 企业档案数量:整理后 7,739 家(原 7,399 + 实时新增 340)

## 用户偏好(本次确认)

- 更新公告:每次功能更新推详细变更(🆕 新增/🔧 优化/🐛 修复 + 📊 状态),**只推本次内容**,不重复历史
- bot 重启静默:不推"已上线"(只日志)
- 功能说明文档交付:桌面 .md(章节式,含命令速查表/FAQ)
