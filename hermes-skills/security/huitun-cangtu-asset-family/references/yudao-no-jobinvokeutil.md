# 关键区分：yudao（ruoyi-vue-pro）没有 JobInvokeUtil —— EL RCE 不存在

RuoYi 系的 EL 定时任务链**只适用于 RuoYi 原版**。打 **芋道 yudao / ruoyi-vue-pro**（YunaiV）前先判定目标用的是哪套调度：

| | RuoYi 原版 | yudao（ruoyi-vue-pro） |
|---|---|---|
| 调用工具类 | `JobInvokeUtil` | **无此类** |
| handlerParam 解析 | `getMethodParams()` → `substringBetweenLast("(",")")`，参数须带引号且**不能含括号** | 不解析方法，字符串整段透传 |
| handler 取值 | 任意 `类名.方法名`（可反射任意类 ⇒ EL 可行） | `applicationContext.getBean(handlerName, JobHandler.class)` ⇒ **必须是实现 `JobHandler` 接口的 Spring bean**，调 `execute(String)` |
| EL RCE | 可行 | **不可行**：`javax.el.ELProcessor.eval` 触发必抛 `NoSuchBeanDefinitionException` |

## 判定方法
- 目标源码里搜 `JobInvokeUtil`：搜不到就是 yudao 系；
- 或看 job 触发后的表现：yudao 是「bean not found」，不是参数解析异常；
- 参照实现：`yudao-framework/yudao-spring-boot-starter-job/.../quartz/core/handler/JobHandlerInvoker.java`。

## 实测教训（2026-09，某 yudao 生产部署）
建 `handlerName=javax.el.ELProcessor.eval` 的 job 返回 `code:0`（仅入库），触发后目标标记文件从未写出。
曾先后误判为「job 没被执行」「handlerParam 裸 EL 未加引号 / 含括号破坏解析」，并围绕列宽上限（~255）与引号反复改载荷 —— **真实根因是 NoSuchBean，整条 EL 路线从头就不成立**。

## 正解方向
1. yudao 上打 job 面 ＝ 找应用自带的、可滥用的 `JobHandler` bean（看 `execute(String)` 的参数能否拼出可控行为）；
2. 否则放弃 job 面，转文件/配置类原语（yudao `/infra/file-config` 的 `basePath`、`/infra/file/upload`、`/infra/codegen` 等）；
3. **判定前不要先做长度/转义假设** —— 先确认框架家族，再设计载荷。
