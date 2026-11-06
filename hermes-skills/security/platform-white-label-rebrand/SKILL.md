---
name: platform-white-label-rebrand
description: Use when 把平台二开成自有品牌：换名/配色/图标/净化/验回归。
---

# 平台换皮二开（white-label rebrand）

把别人给的平台（开源换皮包 / 买来的源码 / 单二进制+静态前端）改成自有品牌并交付。
**默认动作：先备份原树 → 再改 → 最后用「基线 vs 现版」差分证明零回归。**

## 0. 先决条件（别跳）
1. 备份原树：`tar -czf _pristine_backup/<proj>_pristine.tar.gz --exclude='*.exe' --exclude='data' --exclude='log' <proj>`
   —— 这是后面所有差分验证的**唯一真基线**，必须最先做。
2. 摸清品牌串分布：`grep -ril "<旧品牌>" . | grep -v data/log/.git`，按目录归类（源码/前端/文档/插件/资源）。
3. 查是否内嵌：`grep -rn "go:embed" --include="*.go" .`。
   - 无 embed ⇒ 改前端/模板/图标/文案**不用重编译**，刷新即可；
   - 有 embed ⇒ 每次改前端都要重编（先确认，否则白验收）。

## 1. 换名（文本 + 文件/目录名）
- 规则写成**长→短排序的单遍替换表**（`A+B`、`A`、`slug`、`slug`去连字符…），一次交错匹配，
  **绝不能链式 replace**：`#60a5fa→#A78BFA` 被后续规则二次命中的话会变成第三个颜色（真踩过）。
- 文件/目录名同样单遍映射，先收集后重命名，避免边改边踩。
- **排除清单**：`.git`、`data/`、`log/`、`*.exe`、`*.jar`、`*.db`、图片、以及用户要求原样保留的目录。
- ★**扩展名白名单必须写全**：漏 `.java`/`.cjs` 会造成「目录改名了但文件内容没改」，类名/断言与源码脱节，
  编译器或测试才炸。做完必须 `grep -ril 旧品牌 .` 复验，空才算过。
- Go 项目别忘了 `go.mod: module <新名>`，全树 import 路径要一致。

## 2. 换配色
- 先统计 CSS 全部颜色（次数+色值），分三类：
  ① 品牌强调色（按钮/链接/焦点环/选中态）→ 换新品牌色；
  ② 中性灰（slate/gray：`#64748b/#e2e8f0/#f8fafc`）→ **绝不动**；
  ③ 暗色主题背景（`#020617/#0b1324`）→ **绝不动**。
- 判断「是不是品牌色」用**显式清单**，不要「色相区间+饱和度阈值」自动旋转：
  阈值会把暗色背景和浅灰一起染紫（真踩过）。
- 一次覆盖 `#hex` 与 `rgba(r, g, b, a)` 两种写法，保留 alpha。
- 亮/暗两套各验：`getComputedStyle(document.documentElement).getPropertyValue('--accent-color')`
  + 主按钮 `backgroundImage`（确认渐变起止色已是新色）。

## 3. 换图标/logo
- 生成多尺寸（1024/256/64/36 + `.ico`），**≥128 用完整装饰、≤64 用简化高对比**（小尺寸糊掉是常见事故）。
- 覆盖点先找全：`favicon.ico`、`images/logo.png`、`images/logo_small.png`、`web/static/logo.png`、
  模板 `<img>`、插件/扩展自带图标、`apple-touch-icon`。
- 前端直读磁盘 ⇒ 覆盖同名文件即可；出多版给用户挑（A/B/C + preview 拼图）。

## 4. 插件/扩展（最易忽略的面）
- Chrome 扩展：`manifest.json` 的 `name`/`short_name`/`description`、面板标题、目录名。
- ★**Burp/JAR 类插件**：`unzip -l` 看类名——常见「源码改了、jar 还是上游旧构建」。
  无 JDK/Maven 时做**字节级改名**：
  1) 解析 class 常量池（tag 1=UTF8 带 2 字节长度；5/6=Long/Double 占两槽；其余按 tag 定长）；
  2) 命中旧品牌的 UTF8 与字符串字面量**同步改写长度字段**；
  3) 条目名同步重命名（`burp/OldName.class`→`burp/NewName.class`）；
  4) 自检：重新解析全部 class 常量池 + 校验每条 `this_class` 名与条目路径一致（一致 ⇒ JVM 能加载）。
  最后 `Main-Class`/`META-INF/maven/<旧坐标>` 也别漏；交付说明要讲清「类体仍是上游构建、要完全同步请 `mvn package`」。

## 5. 配置净化
- 清空上游作者留的 API key / base_url / bot token / webhook / 搜索 key，关掉其机器人开关。
- 监听地址 `0.0.0.0` → `127.0.0.1`（换皮包常自带 `exec` ⇒ 面板暴露=拿 shell）。
- 原配置另存 `<cfg>.orig_bak` 供回滚；新配置零长串凭据（`grep -E "[A-Za-z0-9_-]{32,}"` 应为空）。

## 6. 自定义扩展位
按平台既有约定加模板（多数是「文件即注册、无中心索引、重启生效」）：
`roles/*.yaml`（name/description/user_prompt）、`agents/*.md`（front-matter）、`skills/<n>/SKILL.md`、`tools/*.yaml`。
写清 front-matter 必填字段，否则加载器静默忽略。

## 7. 收尾验证（缺一不可）
1. **残留**：`grep -ril 旧品牌 .`（排除保留目录/binary/备份）⇒ 空；保留的上游署名（LICENSE、`skills/<上游>/SKILL.md`）
   是合规要求，单独列出并说明。
2. **二进制**：`grep -c 新名 <exe>` 有值、`grep -c 旧名 <exe>` = 0。
3. **服务**：`curl -o /dev/null -w '%{http_code}'` = 200；`netstat` 确认监听 = 本机。
4. **视觉**：登录页 + 仪表盘（暗/亮各一张）+ `getComputedStyle` 取值佐证，别只看文字。
5. ★**测试差分**（最有说服力）：原封包跑一遍自带测试记通过/失败数，再跑现版对比。
   - 数字必须一致；现版多失败就逐个看是不是「测试写死了旧品牌/旧配色」（如断言 `rgba(96,165,250,0.18)`）
     ⇒ 把断言对齐到新值，直到与基线一致。
   - 基线本来就失败的用例，明确报告为「上游自带问题」，不冒充成果。
6. 交付文档：目录地图、编译/启动命令、改品牌三种途径、扩展位写法、备份回滚、升级上游的办法。

## Pitfalls（真踩过）
- 链式替换把颜色改飞；单遍映射才安全。
- 扩展名白名单漏 `.java`/`.cjs` ⇒ 改名后类名/断言与源码脱节。
- 没先确认前端是直读还是 embed ⇒ 误判要不要重编。
- 自带测试会用正则断言 CSS 色值和 `window.xxx` 全局名 ⇒ 换皮后必然失败，属预期，要同步对齐。
- 随包 jar 常是上游旧构建 ⇒ 只改文件名不够，按第 4 节处理并如实说明。
- 无人值守长任务：每步落盘脚本（scratch）+ 打印可核对数字，结论必须有证据。
