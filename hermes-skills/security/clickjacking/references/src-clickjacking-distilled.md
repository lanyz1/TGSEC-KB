# SRC 实战报告提炼 — clickjacking

> 来源：蚂蚁SRC榜一Clown的 1 份实战报告
> 提取时间：2026-09-14

## 典型案例摘要（1 份）

### 安全checklist

安全 checklist   权限系统  ( 注册 / 注册 / 二次验证 / 密码重置 )   任何地方都使用  HTTPS. 使用  Bcrypt  存储密码哈希  ( 没有使用盐的必要  - Bcrypt  干的就是这个事 ). 登出 之后销毁会话  ID .   密码重置后销毁所有活跃的会话 .   OAuth2 验证必须包含  state  参数 . 登陆成功之后不能直接重定向到开放的路径（需要校验，否则容易存在钓鱼攻击） . 当解析用户注册 / 登陆的输入时，过滤  javascript:// 、  data:// 以及其他  CRLF 字符 . 使用  secure/httpOn

## 实战 Payload 集（1 条去重）

### XSS

```
javascript://
```

