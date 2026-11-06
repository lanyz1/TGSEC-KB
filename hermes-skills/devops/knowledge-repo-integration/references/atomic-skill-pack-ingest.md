# 整包落地实录: 122 技能逆向包 (rev-skills, 2026-09-17)

## 来料特征(判「整包」的信号)

- 仓库: `dslsdzc/rev-skills` — Apache-2.0 / CC-BY-4.0, 61★, ~2MB, 当天仍在更新。
- 结构三层: 入口 `re-analyze` → 12 个大类网关 → 109 个原子技能; 共 **122 份 `SKILL.md`**。
- 元数据: 语言标 JS(npm 包壳), 但真正的资产是 markdown 技能库 + `references/`。
- 判定: 自洽多层路由体系 → **整包落地**, 不散进既有域、不与本地同名路由包堆叠。

## 廉价探测

```bash
curl -fsSL https://api.github.com/repos/<owner>/<repo>   # 存在性/描述/语言/★/size/更新时间/许可证
git clone --depth 1 https://github.com/<owner>/<repo> /root/TGSEC-Qtzuu/_probe_<name>/<repo>
find <clone> -name SKILL.md | wc -l                       # 技能数, 不是 md 总数
```

结构盘点别只数文件: 找出「入口技能 / 网关集 / 原子集」的相对关系(入口 README 或 triage 文档里通常写死了路由顺序)。

## 覆盖差异(与本地同类资产比)

- 本地近亲可能是**另一个仓**: 本地 `/root/reverse-skill` = 50 个粗粒度技能目录, 与来料技能名重叠 **1/122**。别因为名字像就当重复。
- 判据用**技能目录名精确比对**(basename 集合求交/差), 关键词匹配在几百份 md 的本地语料上误命中到没法用。
- 输出「本地明显缺失」清单(实测: 内核/RTOS/hypervisor/TEE/JavaCard/eBPF/UEFI/车载/工控/游戏机/Flutter/WASM/DRM/反作弊/内存转储/流量捕获/隐写/崩溃分诊 等 30+ 面本地 0 覆盖)。

## 投毒核查(整包也要跑, 别省)

| 项 | 实测结果 |
|---|---|
| `package.json` 的 `postinstall`/`preinstall`/`prepare` | 全无 |
| JS 混淆 / `curl|bash` / 挖矿 / 回连 | 0 命中 |
| 全部外连 URL 逐个判 | 唯一: `bin/wxsource.mjs` → 看雪论坛取素材, 放行 |
| shell 脚本 | 只有 1 个 `probe.sh`(`uname`/`free`/`command -v` 环境探测), 通读干净 |
| 异常文件 | `ccgen.nim` 内容只有 `404: Not Found` = 提交事故, 不是代码 |

结论写进融合报告, 与真增量清单一并给用户。**先评估后动手**(用户硬性: 「先告诉我 让我做决定」)——评估阶段就报「吸/不吸/吸哪些」, 等一声令下再克隆融合。

## 融合脚本要点(`fuse_<pack>.py`)

1. 遍历来源技能目录 → 整目录 `shutil.copy2` 到 `<pack>/<skill>/`(保持 `references/` 相对路径)。
2. `parse_fm()` 必须吃块标量: `key: value` 与 `key: >`/`|` 两种形态; 只认前者的版本会让上百行简介变空。
3. 生成 `<pack>/README.md`: 来源/许可证/技能数/文件数/参考数 + 「入口 + 网关」表 + 原子技能全表 + 增量面 + 投毒甄别结论 + 署名。
4. 域 `README.md` 追加 `<!-- fused:<src> <date> -->` 块(幂等: 先查 `'<pack>' not in text`)。
5. Hermes 伞形技能追加「快查表」(需求 → 打开哪个 `SKILL.md`), 同样幂等。
6. 落报告 `reports/.../DIGEST-<NAME>-CN.md`。

## 验证(必须实测数字)

```bash
find <pack> -name 'SKILL.md' | wc -l          # == 来料技能数
find <pack> -type f ! -name 'SKILL.md' | wc -l
ls <pack>/<入口技能>/references/ | wc -l      # 参考文件没丢
du -sh <pack>
```

## 收尾

- `rm -rf` 暂存克隆(实测 6.5M); 元数据挪 `_ingest_<name>_<date>/`(脚本 + JSON + 日志, 124K)。
- 索引脚本、结果 JSON 全部留档, 便于二次 diff。
- 落点: `domains/<域>/<name>-pack/`, 与本地同类路由包**并存不合并**。
