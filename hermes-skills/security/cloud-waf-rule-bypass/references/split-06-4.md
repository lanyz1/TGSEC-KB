## 4. 绕过成立后立刻回头重打旧拦截面

拿到 Host 绕过不等于拿到东西。**马上重跑之前被拦的全部面**:

- actuator:`env` / `heapdump` / `info`(`info` 常漏 git commit,可直接定版与年代)
- Druid 控制台:`druid/index.html` 取在线会话 = 直接接管
- **注入**:查询串与 JSON body 里 `SLEEP`/`UNION` 被 403 掉的载荷 —— 只留一个绕过结论、
  不重跑注入 = 没拿到任何东西

### 4.1 重跑之后立刻判「值不值得继续」——别把绕过度当成面已开

绕过解锁的是**面**,不是**成果**。重跑完用一两发请求判死三条最常见的空面,
判完立刻换面,不要逐个端点再试一遍:

- **`/actuator` 只回 `health`/`info`**(读 `_links` 一眼可知)⇒ **Spring Cloud `env`+`refresh` RCE 链已死**。
  `env`/`refresh`/`beans`/`configprops`/`mappings`/`heapdump`/`jolokia` 全部 **404 = 显式禁用**,
  与「被 WAF 挡」是两回事(被挡是 403 拦截页)。这条判定只值一发请求。
- **应用对未知路径回固定常量默认体**(实测形如 `{"result":{},"isBizErr":false,"errMsg":"成功","errCode":"0"}`,58 字节)
  ⇒ **状态码不携带任何存在性信息**,枚举的 oracle 只能是**响应体逐字节比对**(`b.strip() == DEFAULT`),
  谁是常量体谁就是「不存在」。同一形态还会**遮蔽接口表**:Springfox 确实在(`/swagger-ui.html` 200、
  `/swagger-resources` 回 `location:/v2/api-docs`),但 `/v2/api-docs` 被 `/**` catch-all 吃掉 ——
  实测 27 种路径变体(尾斜杠、`;`、`..;/`、`%2f`、`%00`、`//`、`/./`、大小写、`?`、`#`、`jsessionid`)
  **全部回同一常量体** ⇒ 接口表拿不到就是拿不到,停,别再加变体。
- **命名不等于框架**:`*Action` 后缀 + `.jsp` 视图 **不是 Struts2 的证据** —— Spring MVC 控制器同样可以这么命名、
  同样能映射 `.do`/`.action`。唯一判据是实打:S2-045/046 的 Content-Type OGNL 载荷 + OOB 回连,
  **无回连即判非 Struts2**,不要拿「命名推断」写结论或据此排计划(会白烧一整条路线)。

