# `.git` 暴露但 `git clone` 失败 → 逐 blob SHA 还原源码

> 触发：`/.git/HEAD`、`/.git/config` 可读（`.git` 目录全暴露），
> 但 `git clone http://target/.git` 报错；或跳板机**无外网 / 无 pip / 无 git**，装不上 `git-dumper`。
> 实测案例：fm 服务端源码 **65/65 文件全部还原成功**。

## 为什么 clone 会失败

- `.git/objects` 里的 **pack 文件**（`pack-*.pack`）体积大，常被 WAF/限速/超时打断；
- 跳板机没外网，`git-dumper`（Python 包）装不上；
- 部分对象被清理，`git fsck` 报 `missing blob`。

## 关键认知：**`.git/index` 才是完整清单**

- `HEAD` → refs → 一个 tree，**只反映该次提交**，且是嵌套树，手工展开烦。
- **`.git/index`（二进制）直接列出工作区全部文件的 blob SHA + 路径** ⇒ 一次拿全，不用递归树。

## 步骤

1. 取元信息（都是纯 GET，天然只读）：
   ```
   /.git/HEAD              → ref: refs/heads/master
   /.git/refs/heads/master → 40 位 commit
   /.git/index             → ★ 清单（二进制，可能几百 KB）
   /.git/logs/HEAD         → 顺带拿全部历史 commit（找"删除前的版本"靠它）
   ```
2. 解析 `index`：`DIRC` 魔数 → 头 12B → 32B 表头/条 → 每条含 20B **binary SHA**。
   用 Python 抓这 20 字节，输出 40 位 hex。**跳过扩展段**（`TREE`/`REUC` 等）即可。
3. 逐个取对象并解压：
   ```
   /.git/objects/<sha[:2]>/<sha[2:]>   → zlib 流
   Python: zlib.decompress(body) → b"blob <len>\x00<内容>"
   ```
4. 落盘为原路径（index 里有路径字节串），得到**明文目录树**。

## 坑

- **单对象 404 是正常的**（对象在 pack 里没被单独暴露）⇒ 记录缺失项，别中断；本例 65/65 无缺失。
- 历史版本常常才是金子：**旧版 Action 里可能留有当前版已删的调试/上传/注入代码**（本例 `LoginAction.class190227a.php` 这类按日期命名的历史件）。
- **`App/Conf/config.php`、`db.php` 之类通常在 `.gitignore` 里** ⇒ **源码到手 ≠ 拿到 DB 凭据**，别误判「源码已得=数据库直连」。
- 全套操作**零写入**，符合「不留影响」底线。

## 同一台机器上的孪生手法（交付包实测）

- **web 根放明文日志**：`repeat_log.txt`（310 KB，1,050 条含身份证/手机号）零鉴权直读
  ⇒ 拿到源码后**先按源码里的 `file_put_contents`/`log` 路径去 web 根试读**。
- **分窗导出绕上限**：`POST /user/userset/user_list` + `isexcel=1`，按 `hiredate` 切 17 个时间窗，各导一次 ⇒ 绕「单次导出上限」的标准做法，比调 page 更稳。
