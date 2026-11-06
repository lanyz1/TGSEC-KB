## 3. 业务归属校验陷阱(最难发现也最值钱 = PII 明文出口)

接口校验 `uid参数 == resource.owner`(如 uid==teacher_uid)**却不校验 token 归属** → uid 参数改成任意 owner uid 即拉其名下全部资源(学员/订单/审核列表可含**完整手机号+微信号明文**,展示接口打码但数据层明文)。

发现路径:页面渲染明文 PII(phone/wechat)的"导师/审核/学员/订单列表"管理页 → 反向定位数据接口 → 自己当 owner 验证基线 → 伪造 owner uid 拉全量。

