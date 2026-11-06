# 离线夹具:拆分后绑定、补采链路自测与断言纪律

适用:给 `D:\95306c`(手搓重写版)加「单项目粒度动作」这类新功能后,写/改**零网络零落盘**的离线夹具;
以及任何「夹具只有部分模块被 mock 到」的场合。

## 1. 拆分后名字解析:补丁打在谁身上

`master_deploy.py`(宿主)+ `master_deploy_parts*.py`(拆分段)是**各自独立的模块 globals**。
段里的函数按自己的 globals 解析自由名 ⇒ 宿主上打的补丁对段无效。

```python
def gen(mod, cut, src_lines):
    # ★必须打在拆分段模块上:classify/classify_p2/cron_lines 分住 parts*.py,
    # 只改 mod.cron_lines ⇒ 段照读真机现况,夹具静默失真
    for nm, m in list(sys.modules.items()):
        if m is not None and nm.startswith("master_deploy") and hasattr(m, "cron_lines"):
            m.cron_lines = lambda: list(src_lines)
```

**失效症状(认这几种就是补丁没生效,不是代码有 bug)**:

| 症状 | 含义 |
|---|---|
| 夹具「块外老行/模板行」计数 = 0,来源全是「上一版受管块」 | 读到了真机现况(而非夹具) |
| 本机(无 `crontab`)直接 `FileNotFoundError/WinError 2` | 夹具的 `cron_lines` 没被替换 |
| 断言「生成结果 == 线上现况 + 新行」意外通过 | 两边读的是同一个真机源 ⇒ 该断言无鉴别力 |

**加固**:夹具对**自己的前提**断言一次(夹具应产出 N 行模板 / 来源集合 == 预期集合),补丁失效即响。

## 2. 动态加载工装模块

```python
spec = importlib.util.spec_from_file_location("v6_master_deploy_t", path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m          # ★必须先挂:模块末尾 _v6parts._bind(sys.modules[__name__])
spec.loader.exec_module(m)          #   取不到就 KeyError,整跑挂掉
```

## 3. 三层夹具骨架(单项目补采链:bot → 主控 → 采集机)

| 层 | 真什么 | 假什么 | 该断什么 |
|---|---|---|---|
| A 采集侧 | 真 App/真 `details` 分支 | 假传输层(记录调用,不出网) | 不 force ⇒ **零请求 + 坏产物原样留着**(= 真机「点了没反应」的机理);force ⇒ 既绕「已有清单」又绕退避,坏数据被真覆盖;CLI 退出码/统计键 |
| B 主控侧 | 真消费者 + 真配置读取 + 真点名轮换 | 假 ssh | 远程命令行**逐字**对账;首台失败自动换台;队列消费 + `done/<id>.json` + 请求归档 + 计数;过期请求**零 ssh**;`max_per_run` 生效;`--dry` 零 ssh 零落机 |
| C bot 侧 | 真菜单 + 真命令层 | 假发送器(四路全换记录器) | 别名已拆(不是死键,最长前缀命中);`apply_enable=0` ⇒ 只读回执且**零写动作**;`=1` ⇒ 真下发;按钮 data == handler 同源;非法 id 拒绝;请求文件**原子写、无 `.tmp` 残留**、窗口内重复点 = busy、能读回上次结果 |

- **零污染闸**收尾必跑:断言 `$PREFIX` 外的路径(`/opt`、`/data_pool`)未被创建/写入 —— 夹具可以往临时目录写,不能碰真位置。
- 权威字段以**真源**为准:调试「夹具绿、真数据空」时优先怀疑夹具给了真源没有的字段(见 §菜单/文案样式对齐的 staged 真数据探针)。

## 4. 断言纪律(桩化的 log 最容易骗自己)

1. **按谓词挑命令,不按序号**:`calls[0]` 往往不是你要的那条(ctx 推送 `cat > …` 常在最前),用
   `next(c["cmd"] for c in fake.calls if c["cmd"].startswith("cd "))`。
2. **累加型容器断言前清空**:桩里 `files`/`calls` 若跨轮累积(字典不自动清),上一轮数据会被算进本轮。
3. **队列型夹具每轮清自己的输入目录**(如请求 `req_dir`),否则「本轮零动作」断言必假失败。
4. **断言要有鉴别力**:正反各跑一次(新代码过、换回改动前副本必失败);只测「老入口点了有反应」抓不到「按钮没人渲染」这类缺失。

## 5. 跑法

```bash
# 本机(无 Linux 工具依赖的夹具)
cd /d/95306c && python tools/offline_repack.py

# 需要树内模块导入的夹具
PYTHONPATH="D:/95306c;D:/95306c/deploy" python tools/test_deploy_crontab_offline.py

# 依赖 crontab -l 的夹具 ⇒ 只能上主控(只读)
#   夹具 + `deploy/` 相关文件 → /tmp/<dir>,再 python3 <夹具>(cwd=/tmp/<dir>)
```

收尾门禁(任一不过不许上机):五套离线桩全绿 + `compileall -W always` warning 0 + `struct_check` 棘轮无新增 + `bind_audit` 裸名 0 + pyflakes 按注入类白名单精确计数对账。
